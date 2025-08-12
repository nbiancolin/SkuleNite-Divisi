from django.contrib import admin, messages
from django.http import HttpRequest

import datetime

from .models import UploadSession

class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("file_name", "created_at")

    actions = ["remove_older_scores",]

    # Override to allow for delete method to actualy clean up old stuff
    # There is a performance impact, but its ncessary to save space
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

    @admin.action(description="Delete Scores >=2 days old")
    def remove_older_scores(self, request, queryset):
        two_days_ago = datetime.datetime.now() - datetime.timedelta(days=2)
        old_scores = queryset.filter(created_at__lt=two_days_ago)
        num_scores = old_scores.count()
        old_scores.delete()

        self.message_user(request, f"Successfully deleted {num_scores} scores", messages.SUCCESS)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj = None) -> bool:
        return False


admin.site.register(UploadSession, UploadSessionAdmin)