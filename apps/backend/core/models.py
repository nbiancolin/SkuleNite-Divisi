from django.db import models

# Create your models here.


class SiteWarning(models.Model):
    text = models.CharField(max_length=256)

    is_visible = models.BooleanField(default=False)
