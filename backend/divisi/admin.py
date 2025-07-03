from django.contrib import admin

from .models import Ensemble, Arrangement, ArrangementVersion, Part, ScoreOrder, ScoreOrderEntry


# Register your models here.

class EnsembleAdmin(admin.ModelAdmin):
    list_display = ("title", "score_order")

class ArrangementAdmin(admin.ModelAdmin):
    list_display = ("ensemble", "title")

class ArrangementVersionAdmin(admin.ModelAdmin):
    list_display = ("arrangement", "version", "timestamp")

class PartAdmin(admin.ModelAdmin):
    list_display = ("arrangement", "part_name", "filename")

class ScoreOrderAdmin(admin.ModelAdmin):
    list_display = ("ensemble",)

class ScoreOrderEntryAdmin(admin.ModelAdmin):
    list_display = ("score_order", "part_title", "score_order_list_id")


admin.site.register(Ensemble, EnsembleAdmin)
admin.site.register(Arrangement, ArrangementAdmin)
admin.site.register(ArrangementVersion, ArrangementVersionAdmin)
admin.site.register(Part, PartAdmin)
admin.site.register(ScoreOrder, ScoreOrderAdmin)
admin.site.register(ScoreOrderEntry, ScoreOrderEntryAdmin)

