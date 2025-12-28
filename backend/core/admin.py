from django.contrib import admin, messages

# Register your models here.
from .models import SiteWarning

class SiteWarningAdmin(admin.ModelAdmin):
    list_display = ("text", "is_visible")

    actions = ("display_warnings", "hide_warnings")

    @admin.action(description="Turn On Warnings")
    def display_warnings(self, request, queryset):
        for warning in queryset:
            warning.is_visible = True
            warning.save(update_fields=["is_visible"])
        
        messages.success(request, f"Successfully displayed {queryset.count()} warnings")
    
    @admin.action(description="Turn Off Warnings")
    def hide_warnings(self, request, queryset):
        for warning in queryset:
            warning.is_visible = False
            warning.save(update_fields=["is_visible"])
        
        messages.success(request, f"Successfully hid {queryset.count()} warnings")

admin.site.register(SiteWarning, SiteWarningAdmin)

#unregister unneeded socialaccount models
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
admin.site.unregister(SocialApp)
admin.site.unregister(SocialAccount)
admin.site.unregister(SocialToken)
from allauth.account.models import EmailAddress
admin.site.unregister(EmailAddress)