from django.contrib import admin, messages

from .models import Ensemble, Arrangement, ArrangementVersion, Diff
from .tasks import export_arrangement_version, prep_and_export_mscz, compute_diff

from django.http import HttpRequest


class EnsembleAdmin(admin.ModelAdmin):
    list_display = ("name",)


class ArrangementAdmin(admin.ModelAdmin):
    list_display = ("title", "ensemble", "latest_version")


class ArrangementVersionAdmin(admin.ModelAdmin):
    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

    list_display = ("version_label", "arrangement_title", "ensemble_name", "timestamp")

    actions = (
        "re_export_version",
        "re_process_version",
        "manually_compute_diff",
        "manually_export_musicxml",
    )

    @admin.action(description="Re-trigger export of version")
    def re_export_version(self, request, queryset):
        if len(queryset) > 5:
            messages.warning(
                request,
                "Please don't do this to more than 5 versions at a time. Cloud computing is expensive :sob:",
            )
            return
        for version in queryset:
            export_arrangement_version.delay(version.pk)
            messages.success(
                request,
                f'Successfully retriggered export for "{version.arrangement.title}" v{version.version_label}',
            )

    @admin.action(description="Re-trigger format and export of version")
    def re_process_version(self, request, queryset):
        if len(queryset) > 5:
            messages.warning(
                request,
                "Please don't do this to more than 5 versions at a time. Cloud computing is expensive :sob:",
            )
            return
        for version in queryset:
            prep_and_export_mscz.delay(version.pk)
            messages.success(
                request,
                f'Successfully retriggered format and export for "{version.arrangement.title}" v{version.version_label}',
            )

    @admin.action(description="Manually Export MusicXML file")
    def manually_export_musicxml(self, request, queryset):
        for v in queryset:
            export_arrangement_version(v.id, action="mxl")
        messages.success(request, f"Queued {queryset.count()} versions for MXL export")

    @admin.action(description="Manually compute diff of two scores")
    def manually_compute_diff(self, request, queryset):
        if len(queryset) != 2:
            messages.warning(
                request, "Can only compute diff of two scores. no more, no less."
            )
            return

        queryset = queryset.order_by("timestamp")

        from_version = ArrangementVersion.objects.get(id=queryset[0].id)
        to_version = ArrangementVersion.objects.get(id=queryset[1].id)
        if from_version.arrangement != to_version.arrangement:
            messages.warning(request, "Must select 2 versions of the same arrangement")
            return

        d, created = Diff.objects.get_or_create(
            from_version=from_version,
            to_version=to_version,
            file_name="comp-diff.pdf",
        )

        if d.status == "in_progress":
            messages.error(request, "This diff is already in the export process. Wait for it to finish, then try again")
            return

        if not created:
            messages.warning(request, "Diff already existed, re-computing")
            d.status = "pending"
            d.save()

        res = compute_diff(d.id)
        messages.success(request, f"Res: {res}")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class DiffAdmin(admin.ModelAdmin):
    list_display = ("from_version__str__", "to_version__str__", "status", "timestamp")

    actions = "recompute_diff"

    @admin.action(description="Manually re-compute diff")
    def recompute_diff(self, request, queryset):
        if queryset.count() != 1:
            messages.warning(request, "Please only trigger one diff to be recomputed!")
            return

        diff = queryset[0]
        diff.status = "pending"
        diff.save()

        compute_diff.delay(diff.id)
        messages.success(request, "Triggered diff to be re-exported")
        return

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Diff, DiffAdmin)
