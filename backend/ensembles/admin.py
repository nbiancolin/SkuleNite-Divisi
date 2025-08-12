from django.contrib import admin

from .models import Ensemble, Arrangement, ArrangementVersion, Part

from django.http import HttpRequest


class EnsembleAdmin(admin.ModelAdmin):
    list_display = ("name",)


class ArrangementAdmin(admin.ModelAdmin):
    list_display = ("ensemble", "title", "latest_version")


class ArrangementVersionAdmin(admin.ModelAdmin):
    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()
    
    list_display = ("version_label", "arrangement_title", "ensemble_name", "timestamp")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj = None) -> bool:
        return False


class PartAdmin(admin.ModelAdmin):
    list_display = ("version", "part_name", "file")


# TODO: do this
# class EnsembleSetListEntryAdmin(admin.ModelAdmin):
#     list_display = ("ensemble", "arrangement", "order_index")


admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Part, PartAdmin)
