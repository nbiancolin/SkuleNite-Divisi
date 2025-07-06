from django.contrib import admin

from .models import Ensemble, Arrangement, ArrangementVersion, Part


class EnsembleAdmin(admin.ModelAdmin):
    list_display = ("name",)


class ArrangementAdmin(admin.ModelAdmin):
    list_display = ("ensemble", "title")


class ArrangementVersionAdmin(admin.ModelAdmin):
    list_display = ("version_label", "timestamp")


class PartAdmin(admin.ModelAdmin):
    list_display = ("version", "part_name", "file")


# TODO: do this
# class EnsembleSetListEntryAdmin(admin.ModelAdmin):
#     list_display = ("ensemble", "arrangement", "order_index")


admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Part, PartAdmin)
