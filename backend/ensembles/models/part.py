from django.db import models
from django.core.files.storage import default_storage

from ensembles.models.arrangement_version import ArrangementVersion

from logging import getLogger

logger = getLogger("app")


class PartAsset(models.Model):
    """Model to track individual part PDFs for an ArrangementVersion"""
    arrangement_version = models.ForeignKey(
        ArrangementVersion, related_name="parts", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)  # Part name (e.g., "Violin", "Cello")
    file_key = models.CharField(max_length=500)  # Storage key for the PDF file
    is_score = models.BooleanField(default=False)  # True if this is the full score PDF
    
    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.file_key)
    
    def __str__(self):
        part_type = "Score" if self.is_score else "Part"
        return f"{part_type}: {self.name} ({self.arrangement_version})"
    
    class Meta:
        ordering = ["-is_score", "name"]  # Score first (True before False), then parts alphabetically