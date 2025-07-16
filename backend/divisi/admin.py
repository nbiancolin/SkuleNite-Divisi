from django.contrib import admin
from django.http import HttpRequest

from .models import UploadSession

class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("file_name", "created_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj = None) -> bool:
        return False


admin.site.register(UploadSession, UploadSessionAdmin)