from django.contrib import admin, messages

from .models import Ensemble, Arrangement, ArrangementVersion, Diff, Part
from .tasks import export_arrangement_version, prep_and_export_mscz, compute_diff

from django.http import HttpRequest
from django.db.utils import IntegrityError


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

    actions = ("re_export_version", "re_process_version", "manually_compute_diff")

    @admin.action(description="Re-trigger export of version")
    def re_export_version(self, request, queryset):
        if len(queryset) > 5:
            messages.warning(request, "Please don't do this to more than 5 versions at a time. Cloud computing is expensive :sob:")
            return
        for version in queryset:
            export_arrangement_version.delay(version.pk)
            messages.success(request, f"Successfully retriggered export for \"{version.arrangement.title}\" v{version.version_label}")

    @admin.action(description="Re-trigger format and export of version")
    def re_process_version(self, request, queryset):
        if len(queryset) > 5:
            messages.warning(request, "Please don't do this to more than 5 versions at a time. Cloud computing is expensive :sob:")
            return
        for version in queryset:
            prep_and_export_mscz.delay(version.pk)
            messages.success(request, f"Successfully retriggered format and export for \"{version.arrangement.title}\" v{version.version_label}")

    #TODO: Add admin action to manually create and compute a diff
    @admin.action(description="Manually compute diff of two scores")
    def manually_compute_diff(self, request, queryset):
        if len(queryset) != 2:
            messages.warning(request, "Can only compute diff of two scores. no more, no less.")
            return

        queryset = queryset.order_by("timestamp")

        from_version = ArrangementVersion.objects.get(id=queryset[0].id)
        to_version = ArrangementVersion.objects.get(id=queryset[1].id)
        if from_version.arrangement != to_version.arrangement:
            messages.warning(request, "Must select 2 versions of the same arrangement")
            return
        
        try:
            d = Diff.objects.create(from_version=from_version, to_version=to_version, file_name="comp-diff.pdf")
        except IntegrityError:
            messages.warning(request, "A Diff for these versions already exists! delete it first")
            return

        res = compute_diff(d.id)
        messages.success(request, f"Res: {res}")


    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj = None) -> bool:
        return False


class DiffAdmin(admin.ModelAdmin):

    list_display = ("from_version__str__", "to_version__str__", "status", "timestamp")
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

class PartAdmin(admin.ModelAdmin):
    list_display = ("version", "part_name", "file")


# TODO: do this
# class EnsembleSetListEntryAdmin(admin.ModelAdmin):
#     list_display = ("ensemble", "arrangement", "order_index")


admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Diff, DiffAdmin)
admin.site.register(Part, PartAdmin)
