from django.db import models
from logging import getLogger
from ensembles.models import Ensemble
from ensembles.models.constants import STYLE_CHOICES
from ensembles.lib.slug import generate_unique_slug

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ensembles.models.arrangement_version import ArrangementVersion

logger = getLogger("app")



class Arrangement(models.Model):
    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager
        versions: RelatedManager["ArrangementVersion"]

    ensemble = models.ForeignKey(
        Ensemble, related_name="arrangements", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    composer = models.CharField(max_length=255, blank=True, null=True)
    #TODO[SC-282]: Remove act number and piece number, they are no longer used
    act_number = models.IntegerField(blank=True, null=True)
    piece_number = models.IntegerField(default=1, blank=True, null=True)

    #This field cannot be blank, if its blank the value is filled in with the arrangemnt pk
    mvt_no = models.CharField(max_length=4)

    style = models.CharField(max_length=10, choices=STYLE_CHOICES)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Arrangement, self.title, instance=self)

        if not self.style:
            self.style = self.ensemble.default_style

        creating = self.pk is None
        if creating and self.mvt_no is None:
            raise NotImplementedError("mvt_no is required")
        
        super().save(*args, **kwargs)


    @property
    def latest_version(self):
        return self.versions.filter(is_latest=True).first()

    @property
    def latest_version_num(self):
        latest = self.latest_version
        return latest.version_label if latest else "N/A"

    @property
    def ensemble_name(self):
        return self.ensemble.name

    @property
    def ensemble_slug(self):
        return self.ensemble.slug

    def __str__(self):
        return f"({self.mvt_no}) {self.title}"

    class Meta:
        ordering = ["mvt_no"]