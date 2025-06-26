from django.db import models
from django.utils import timezone

def score_upload_path(instance, filename):
    return f"{instance.title}/{instance.version}/{filename}"

class Score(models.Model):
    title = models.CharField(max_length=120)
    file = models.FileField(upload_to=score_upload_path)
    version = models.CharField(max_length=6, default='v1.0.0')
    timestamp = models.DateTimeField("date uploaded", default=timezone.now)

    def __str__(self):
        return f"{self.title}-{self.version}"

