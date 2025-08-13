from django.db import models
from django.utils.text import slugify
from django.conf import settings

import uuid
import os
import shutil
from logging import getLogger

logger = getLogger("app")

STYLE_CHOICES = [("jazz", "Jazz"), ("broadway", "Broadway"), ("classical", "Classical")]


def generate_unique_slug(model_class, value, instance=None):
    """
    Generates a unique slug for a model instance.
    """
    base_slug = slugify(value)
    slug = base_slug
    counter = 1

    # Exclude current instance if updating
    queryset = model_class.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


class Ensemble(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    default_style = models.CharField(choices=STYLE_CHOICES)

    @property
    def num_arrangements(self):
        return Arrangement.objects.filter(ensemble__id=self.pk).count()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Ensemble, self.name, instance=self)
        super().save(*args, **kwargs)


class Arrangement(models.Model):
    ensemble = models.ForeignKey(
        Ensemble, related_name="arrangements", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    composer = models.CharField(max_length=255, blank=True, null=True)
    act_number = models.IntegerField(default=1, blank=True, null=True)
    piece_number = models.IntegerField(
        default=1, blank=True, null=True
    )  # NOTE: This field is auto-populated on save... should never actually be blank

    default_style = models.CharField(choices=STYLE_CHOICES) #TODO: This should be called "style" not default_style

    # TODO: Make this a little cleaner, might not be optimal
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Arrangement, self.title, instance=self)

        if self.pk is None:
            super().save(*args, **kwargs)
            if self.piece_number is None:
                self.piece_number = self.pk
                super().save(update_fields=["piece_number"])
        else:
            if self.piece_number is None:
                self.piece_number = self.pk
            super().save(*args, **kwargs)

    def get_mvtno(self):
        if self.act_number is not None:
            return f"{self.act_number}-{self.piece_number}"
        return f"{self.piece_number}"

    @property
    def mvt_no(self):
        return self.get_mvtno()

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
        return f"{self.mvt_no}: {self.title} (v{self.latest_version_num})"

    class Meta:
        ordering = ["act_number", "piece_number"]


class ArrangementVersion(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, related_name="versions", on_delete=models.CASCADE
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    file_name = models.CharField()
    version_label = models.CharField(max_length=10, default="0.0.0")  # 1.0.0 or 1.2.3
    timestamp = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=False)

    def _bump_version_label(self, version_type, old_version_label):
        major, minor, patch = map(int, old_version_label.split("."))
        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"{major}.{minor}.{patch}"


    def save(self, *args, **kwargs):
        version_type = kwargs.pop("version_type", None)

        if version_type:
            # This is a new version, and caller wants to bump the version
            latest = ArrangementVersion.objects.filter(
                arrangement=self.arrangement, is_latest=True
            ).first()

            old_label = latest.version_label if latest else "0.0.0"
            self.version_label = self._bump_version_label(version_type, old_label)

            # Mark all other versions as not latest
            ArrangementVersion.objects.filter(arrangement=self.arrangement).update(
                is_latest=False
            )

            self.is_latest = True

        super().save(*args, **kwargs)

        #create directories
        os.makedirs(self.mscz_file_location, exist_ok=True)
        os.makedirs(self.output_file_location, exist_ok=True)

    def delete(self, **kwargs):
        #delete files when session is deleted
        paths_to_delete = [self.mscz_file_location, self.output_file_location]
        logger.warning("Deleting ArrangementVersion")

        for rel_path in paths_to_delete:
            abs_path = os.path.abspath(rel_path) 

            if os.path.exists(abs_path):
                try:
                    shutil.rmtree(abs_path)
                    logger.info(f"Deleted folder: {abs_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {abs_path}: {e}")
            else:
                logger.warning(f"Path does not exist, skipping: {abs_path}")

        super().delete(**kwargs)

    @property
    def mscz_file_location(self) -> str:
        return f"{settings.MEDIA_ROOT}/_ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.uuid}/raw/"

    @property
    def mscz_file_path(self) -> str:
        return self.mscz_file_location + f"{self.file_name}"

    @property
    def output_file_location(self) -> str:
        return f"{settings.MEDIA_ROOT}/_ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.uuid}/processed/"

    @property
    def output_file_path(self) -> str:
        return self.output_file_location + f"{self.file_name}"
    
    @property
    def score_pdf_path(self) -> str:
        return self.output_file_path[:-4] + "pdf"

    @property
    def score_parts_pdf_path(self) -> str:
        return self.output_file_path[:-5] + "-Score+Parts.pdf"

    @property
    def arrangement_title(self):
        return self.arrangement.title
    
    @property
    def arrangement_slug(self):
        return self.arrangement.slug
    
    @property
    def ensemble_name(self):
        return self.arrangement.ensemble_name
    
    @property
    def ensemble_slug(self):
        return self.arrangement.ensemble_slug

    def __str__(self):
        return f"{self.arrangement.__str__} (v{self.version_label})"

    class Meta:
        ordering = ["-timestamp"]


def _part_upload_path(instance, filename):
    ensemble = instance.version.arrangement.ensemble.name.replace(" ", "_")
    arrangement = instance.version.arrangement.title.replace(" ", "_")
    version = instance.version.version_label
    return f"blob/PDF/{ensemble}/{arrangement}/{version}/{filename}"  # TODO: Move this to use media/static root


class Part(models.Model):
    version = models.ForeignKey(
        ArrangementVersion, related_name="parts", on_delete=models.CASCADE
    )
    part_name = models.CharField(max_length=120)
    file = models.FileField(upload_to=_part_upload_path)

    def __str__(self):
        return f"{self.version.arrangement.title} - {self.part_name} (v{self.version.version_label})"


class EnsembleSetlistEntry(models.Model):
    ensemble = models.ForeignKey(
        Ensemble, related_name="setlist_entries", on_delete=models.CASCADE
    )
    arrangement = models.ForeignKey(Arrangement, on_delete=models.CASCADE)
    order_index = models.PositiveIntegerField()

    class Meta:
        unique_together = ("ensemble", "order_index")
        ordering = ["order_index"]

    def __str__(self):
        return f"{self.order_index:02d} - {self.arrangement.title}"
