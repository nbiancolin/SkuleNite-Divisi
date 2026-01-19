from django.contrib import admin, messages

from .models import ExportFailureLog, Ensemble, Arrangement, ArrangementVersion, Diff, EnsembleUsership, PartAsset, PartName
from .tasks import export_arrangement_version, prep_and_export_mscz

from django.http import HttpRequest


class PartNameInline(admin.TabularInline):
    model = PartName
    extra = 0
    fields = ('display_name',) 

class EnsembleAdmin(admin.ModelAdmin):
    list_display = ("name", "num_arrangements", "owner")
    inlines = [PartNameInline]

    def part_names_list(self, obj):
        return ", ".join(obj.part_names.values_list('name', flat=True))
    part_names_list.short_description = 'Parts'


class ArrangementAdmin(admin.ModelAdmin):
    list_display = ("title", "ensemble", "latest_version")


class ArrangementVersionAdmin(admin.ModelAdmin):
    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

    list_display = ("version_label", "arrangement_title", "ensemble_name", "timestamp", "audio_state")

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
            messages.warning(
                request, "Can only export audio of one score at a time."
            )
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
    

class DiffAdmin(admin.ModelAdmin):
    list_display = ("from_version__str__", "to_version__str__", "status", "timestamp")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


class EnsembleUsershipAdmin(admin.ModelAdmin):
    list_display = ("user", "ensemble", "date_joined")
    list_filter = ("ensemble", "date_joined")
    search_fields = ("user__username", "user__email", "ensemble__name")


#TODO: Rename
class PartAdmin(admin.ModelAdmin):
    list_display = ("name", "arrangement_version", "is_score", "file_key")
    list_filter = ("is_score", "arrangement_version")
    search_fields = ("name", "arrangement_version__arrangement__title")
    readonly_fields = ("file_key", "file_url")


admin.site.register(ExportFailureLog, ExportFailureLogAdmin)
admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Diff, DiffAdmin)
admin.site.register(EnsembleUsership, EnsembleUsershipAdmin)
admin.site.register(PartAsset, PartAdmin)
