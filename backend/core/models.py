from django.db import models

# Create your models here.


class SiteWarning(models.Model):
    text = models.CharField()

    is_visible = models.BooleanField(default=False)
