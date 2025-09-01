from django.db import models
from django.utils.text import slugify
from django.core.files.storage import default_storage

import os
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
    act_number = models.IntegerField(blank=True, null=True)
    piece_number = models.IntegerField(
        default=1, blank=True, null=True
    )  

    style = models.CharField(choices=STYLE_CHOICES) 

    # TODO: Make this a little cleaner, might not be optimal
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Arrangement, self.title, instance=self)
        
        if not self.style:
            self.style = self.ensemble.default_style

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

    file_name = models.CharField()
    version_label = models.CharField(max_length=10, default="0.0.0")  # 1.0.0 or 1.2.3
    timestamp = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=False)
    is_processing = models.BooleanField(default=True)
    error_on_export = models.BooleanField(default=False)

    num_measures_per_line_score = models.IntegerField()
    num_measures_per_line_part = models.IntegerField()

    @property
    def mscz_file_key(self) -> str:
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/raw/{self.file_name}"

    @property
    def output_file_key(self) -> str:
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{self.file_name}"

    @property
    def score_pdf_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext}.pdf"

    @property
    def mxl_file_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext}.musicxml"

    @property
    def score_parts_pdf_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext} - Score+Parts.pdf"

    @property
    def mscz_file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.mscz_file_key)

    @property
    def output_file_url(self) -> str:
        return default_storage.url(self.output_file_key)

    @property
    def score_pdf_url(self) -> str:
        return default_storage.url(self.score_pdf_key)

    @property
    def score_parts_pdf_url(self) -> str:
        return default_storage.url(self.score_parts_pdf_key)

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

    def delete(self, **kwargs):
        # Delete files when version is deleted
        keys_to_delete = [
            self.mscz_file_key, 
            self.output_file_key, 
            self.score_pdf_key, 
            self.score_parts_pdf_key
        ]
        logger.warning("Deleting ArrangementVersion")

        for key in keys_to_delete:
            try:
                if default_storage.exists(key):
                    default_storage.delete(key)
                    logger.info(f"Deleted file: {key}")
                else:
                    logger.warning(f"File does not exist, skipping: {key}")
            except Exception as e:
                logger.error(f"Failed to delete {key}: {e}")

        super().delete(**kwargs)

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

class Diff(models.Model):
    from_version = models.ForeignKey(
        ArrangementVersion,
        on_delete=models.CASCADE,
        related_name="diff_as_source"
    )
    to_version = models.ForeignKey(
        ArrangementVersion,
        on_delete=models.CASCADE,
        related_name="diff_as_target"
    )

    file_name = models.CharField()
    timestamp = models.DateTimeField(auto_now_add=True)
    generated = models.BooleanField(default=False)

    @property
    def file_key(self) -> str:
        return f"ensemble-diffs/{self.from_version.ensemble_slug}/{self.from_version.arrangement_slug}/{self.from_version.version_label}-{self.to_version.version_label}/{self.file_name}"

    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.file_key)
    
    def compute_diff(self):
        pass

    class Meta:
        unique_together = ("from_version", "to_version")

    def __str__(self):
        return f"Diff {self.from_version} → {self.to_version}"




def _part_upload_key(instance, filename):
    """Generate storage key for part files"""
    ensemble_slug = instance.version.arrangement.ensemble.slug
    arrangement_slug = instance.version.arrangement.slug
    version = instance.version.version_label
    return f"ensembles/{ensemble_slug}/arrangements/{arrangement_slug}/versions/{version}/parts/{filename}"

_part_upload_path = _part_upload_key

class Part(models.Model):
    version = models.ForeignKey(
        ArrangementVersion, related_name="parts", on_delete=models.CASCADE
    )
    part_name = models.CharField(max_length=120)
    file = models.FileField(upload_to=_part_upload_key)

    @property
    def file_key(self) -> str:
        """Get the storage key for this part's file"""
        if self.file:
            return self.file.name
        return ""

    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        if self.file:
            return default_storage.url(self.file.name)
        return ""

    def delete(self, **kwargs):
        # Delete the file when part is deleted
        if self.file:
            try:
                if default_storage.exists(self.file.name):
                    default_storage.delete(self.file.name)
                    logger.info(f"Deleted part file: {self.file.name}")
            except Exception as e:
                logger.error(f"Failed to delete part file {self.file.name}: {e}")
        
        super().delete(**kwargs)

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
