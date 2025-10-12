from django.contrib import admin

# Register your models here.
from .models import SiteWarning

class SiteWarningAdmin(admin.ModelAdmin):
    pass

admin.site.register(SiteWarning, SiteWarningAdmin)