from django.contrib import admin

from .models import UploadSession

class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("file_name", "created_at")


admin.site.register(UploadSession, UploadSessionAdmin)