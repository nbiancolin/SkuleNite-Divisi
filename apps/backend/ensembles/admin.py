from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest

from .models import (
    Arrangement,
    ArrangementVersion,
    Commit,
    Diff,
    Ensemble,
    EnsembleUsership,
    ExportFailureLog,
    PartAsset,
    PartBook,
    PartName,
    PartNameAlias
    UserScoreVersion,
)
from .tasks import export_arrangement_version, prep_and_export_mscz


class PdfObjMixin:
    """Mixin for modeladmins with pdfs. Pdfs and files need to be cleaned up"""

    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


class PartNameInline(admin.TabularInline):
    model = PartName
    extra = 0
    fields = ("display_name",)


class EnsembleAdmin(admin.ModelAdmin):
    list_display = ("name", "num_arrangements", "owner")
    inlines = [PartNameInline]

    def part_names_list(self, obj):
        return ", ".join(obj.part_names.values_list("name", flat=True))

    part_names_list.short_description = "Parts"


class ArrangementAdmin(admin.ModelAdmin):
    list_display = ("title", "ensemble", "latest_version")
    list_filter = ("ensemble",)


class ArrangementVersionAdmin(admin.ModelAdmin, PdfObjMixin):
    list_display = (
        "version_label",
        "arrangement_title",
        "ensemble_name",
        "timestamp",
        "audio_state",
    )

    actions = (
        "re_export_version",
        "re_process_version",
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

    @admin.action(description="Re-trigger audio export of version")
    def re_export_audio(self, request, queryset):
        if len(queryset) != 1:
            messages.warning(request, "Can only export audio of one score at a time.")
            return

        export_arrangement_version.delay(queryset[0].pk, action="mp3")
        messages.success(
            request,
            f'Successfully re-triggered audio export for "{queryset[0].arrangement.title}" v{queryset[0].version_label}',
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class ExportFailureLogAdmin(admin.ModelAdmin):
    list_display = ("id", "arrangement_version__str__")

    readonly_fields = ("id", "arrangement_version", "error_msg")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class DiffAdmin(admin.ModelAdmin, PdfObjMixin):
    list_display = ("from_version__str__", "to_version__str__", "status", "timestamp")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class EnsembleUsershipAdmin(admin.ModelAdmin):
    list_display = ("user", "ensemble", "date_joined")
    list_filter = ("ensemble", "date_joined")
    search_fields = ("user__username", "user__email", "ensemble__name")


class PartAssetAdmin(admin.ModelAdmin, PdfObjMixin):
    list_display = ("part_name", "arrangement_version", "is_score", "file_key")
    list_filter = ("is_score", "arrangement_version")
    search_fields = ("part_name", "arrangement_version__arrangement__title")
    readonly_fields = ("file_key", "file_url")


class PartNameAdmin(admin.ModelAdmin):
    list_display = ("display_name", "ensemble")
    list_filter = ("ensemble",)
    search_fields = ("ensemble",)

    @admin.action(description="Merge Part Names")
    def merge_part_names(self, request, queryset):
        if len(queryset) != 2:
            messages.warning(request, "Can only merge 2 part names at a time!")
            return

        try:
            PartName.merge_part_names(*queryset)
        except ValidationError as e:
            messages.error(request, f"Failed to merge part names: {e}")


class PartBookAdmin(admin.ModelAdmin, PdfObjMixin):
    pass

class PartNameAliasAdmin(admin.ModelAdmin):
    list_filter = ("ensemble",)
    

class CommitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "arrangement",
        "file_name",
        "message",
        "parent_commit",
        "is_initial_commit",
        "is_latest_commit",
    )
    list_filter = ("arrangement__ensemble", "arrangement")
    search_fields = (
        "file_name",
        "message",
        "arrangement__title",
        "arrangement__ensemble__name",
    )
    readonly_fields = (
        "mscz_file_key",
        "mscz_file_url",
        "is_initial_commit",
        "is_latest_commit",
    )


class UserScoreVersionEnsembleFilter(admin.SimpleListFilter):
    title = "ensemble"
    parameter_name = "ensemble"

    def lookups(self, request, model_admin):
        return [
            (e.pk, e.name) for e in Ensemble.objects.order_by("name").only("pk", "name")
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(arrangement__ensemble_id=self.value())
        return queryset


class UserScoreVersionArrangementFilter(admin.SimpleListFilter):
    title = "arrangement"
    parameter_name = "arrangement"

    def lookups(self, request, model_admin):
        ensemble_id = request.GET.get(UserScoreVersionEnsembleFilter.parameter_name)
        if not ensemble_id:
            return []
        return [
            (a.pk, a.title)
            for a in Arrangement.objects.filter(ensemble_id=ensemble_id)
            .order_by("title")
            .only("pk", "title")
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(arrangement_id=self.value())
        return queryset


class UserScoreVersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ensemble_name",
        "arrangement",
        "commit_summary",
        "updated_at",
    )
    list_filter = (
        UserScoreVersionEnsembleFilter,
        UserScoreVersionArrangementFilter,
        "updated_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "arrangement__title",
        "arrangement__ensemble__name",
        "commit__message",
    )
    readonly_fields = ("updated_at",)
    raw_id_fields = ("user", "arrangement", "commit")
    list_select_related = ("user", "arrangement__ensemble", "commit")

    @admin.display(description="Ensemble", ordering="arrangement__ensemble__name")
    def ensemble_name(self, obj):
        return obj.arrangement.ensemble.name

    @admin.display(description="Commit")
    def commit_summary(self, obj):
        if obj.commit_id is None:
            return "—"
        message = (obj.commit.message or "").strip()
        if len(message) > 60:
            message = f"{message[:57]}..."
        return f"#{obj.commit_id} {message}" if message else f"#{obj.commit_id}"


admin.site.register(ExportFailureLog, ExportFailureLogAdmin)
admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Diff, DiffAdmin)
admin.site.register(EnsembleUsership, EnsembleUsershipAdmin)
admin.site.register(PartAsset, PartAssetAdmin)
admin.site.register(PartName, PartNameAdmin)
admin.site.register(PartBook, PartBookAdmin)
admin.site.register(PartNameAlias, PartNameAliasAdmin)
admin.site.register(Commit, CommitAdmin)
admin.site.register(UserScoreVersion, UserScoreVersionAdmin)
