from typing import Iterable
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
    #TODO: Backfill/delete any part assets that dont have a NameObj associated
    name_obj = models.ForeignKey("PartName", on_delete=models.CASCADE, null=True)
    # name = models.CharField(max_length=255)  # Part name (e.g., "Violin", "Cello")
    file_key = models.CharField(max_length=500)  # Storage key for the PDF file
    is_score = models.BooleanField(default=False)  # True if this is the full score PDF

    def save(self, **kwargs) -> None:
        if self.name_obj is None:
            raise NotImplementedError("Cannot create a PartAsset without a NameObj")
        return super().save(**kwargs)
    
    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.file_key)
    
    @property
    def name(self):
        return self.name_obj.display_name if self.name_obj else "No NameObj Record"
    
    def __str__(self):
        part_type = "Score" if self.is_score else "Part"
        return f"{part_type}: {self.name} ({self.arrangement_version})"
    
    class Meta:
        ordering = ["-is_score"]  # Score first (True before False), then parts alphabetically



class PartName(models.Model):

    ensemble = models.ForeignKey("ensembles.Ensemble", related_name="part_names", on_delete=models.CASCADE)

    display_name = models.CharField(max_length=64)
    # slug #TODO

    def __str__(self):
        return f"{self.display_name} ({self.ensemble.name})"
    

    @classmethod
    def merge_part_names(cls, part1: "PartName", part2: "PartName", new_display_name: str):
        #TODO: this
        pass

class PartBook(models.Model):
    ensemble = models.ForeignKey("ensembles.Ensemble", related_name="part_books", on_delete=models.CASCADE)
    part_name = models.ForeignKey(PartName, related_name="part_books", on_delete=models.CASCADE)

    revision = models.PositiveIntegerField()

    # parent #TODO

    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    # class Meta:
    # Constraint that ensemble, partName and revision are all unique to eachother



class PartBookEntry(models.Model):
    part_book = models.ForeignKey(PartBook, related_name="entries", on_delete=models.CASCADE)
    
    arrangement = models.ForeignKey("ensembles.Arrangement", on_delete=models.CASCADE)
    arrangement_version = models.ForeignKey("ensembles.ArrangementVersion", on_delete=models.CASCADE)

    #When building a part book, compute this value from the Arrangement's mvt_no. This determines the order in the book
    position = models.PositiveIntegerField()
