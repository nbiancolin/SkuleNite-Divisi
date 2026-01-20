from typing import Iterable
from django.db import models
from django.core.files.storage import default_storage

from ensembles.models.arrangement_version import ArrangementVersion
from ensembles.lib.slug import generate_unique_slug

from typing import TYPE_CHECKING

from logging import getLogger

logger = getLogger("app")


class PartAsset(models.Model):
    """Model to track individual part PDFs for an ArrangementVersion"""
    arrangement_version = models.ForeignKey(
        ArrangementVersion, related_name="parts", on_delete=models.CASCADE
    )
    #TODO: Backfill/delete any part assets that dont have a NameObj associated
    name_obj = models.ForeignKey("PartName", on_delete=models.PROTECT, null=True)
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

    id: int

    ensemble = models.ForeignKey("ensembles.Ensemble", related_name="part_names", on_delete=models.CASCADE)

    display_name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)

    def save(self):
        if not self.slug:
            self.slug = generate_unique_slug(PartName, self.display_name, instance=self)

    def __str__(self):
        return f"{self.display_name} ({self.ensemble.name})"
    
    def _merge_objs(self, second: "PartName"):
        """Merge `second` into `self`. Deletes `second` afterwards"""
        second_part_asset_ids = PartAsset.objects.filter(name_obj=second).values_list("id", flat=True)
        PartAsset.objects.filter(id__in=second_part_asset_ids).update(name_obj_id=self.id)
        second.delete()

    @classmethod
    def merge_part_names(cls, first: "PartName", second: "PartName", new_displayname: str = "") -> "PartName":
        if PartAsset.objects.filter(name_obj=second).count() > PartAsset.objects.filter(name_obj=first).count():
            target = second
            merge_from = first
            if not new_displayname:
                new_displayname = first.display_name
        else:
            target = first
            merge_from = second


        target._merge_objs(merge_from)
        if new_displayname:
            target.display_name = new_displayname
            target.save(update_fields=["displayname"])
        
        return target

    
        

class PartBook(models.Model):

    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager
        entries: RelatedManager["PartBookEntry"]

    ensemble = models.ForeignKey("ensembles.Ensemble", related_name="part_books", on_delete=models.CASCADE)
    part_name = models.ForeignKey(PartName, related_name="part_books", on_delete=models.CASCADE)

    revision = models.PositiveIntegerField()

    # parent #TODO

    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    # Constraint that ensemble, partName and revision are all unique to eachother
    class Meta:
        unique_together = ("ensemble", "part_name", "revision")



class PartBookEntry(models.Model):
    part_book = models.ForeignKey(PartBook, related_name="entries", on_delete=models.CASCADE)
    
    arrangement = models.ForeignKey("ensembles.Arrangement", on_delete=models.CASCADE)
    arrangement_version = models.ForeignKey("ensembles.ArrangementVersion", on_delete=models.CASCADE)

    #When building a part book, compute this value from the Arrangement's mvt_no. This determines the order in the book
    position = models.PositiveIntegerField()
