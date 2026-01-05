from django.db import models
from django.utils.text import slugify
from django.core.files.storage import default_storage

import os
import secrets
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
    owner = models.ForeignKey(
        'auth.User',
        related_name='owned_ensembles',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    invite_token = models.CharField(max_length=64, unique=True, null=True, blank=True)

    @property
    def num_arrangements(self):
        return Arrangement.objects.filter(ensemble__id=self.pk).count()

    def generate_invite_token(self):
        """Generate a secure random token for inviting users"""
        token = secrets.token_urlsafe(32)  # 32 bytes = 43 characters in URL-safe base64
        # Ensure uniqueness
        while Ensemble.objects.filter(invite_token=token).exists():
            token = secrets.token_urlsafe(32)
        self.invite_token = token
        self.save(update_fields=['invite_token'])
        return token

    def get_or_create_invite_token(self):
        """Get existing invite token or create a new one"""
        if not self.invite_token:
            self.generate_invite_token()
        return self.invite_token

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Ensemble, self.name, instance=self)
        super().save(*args, **kwargs)

class EnsembleUsership(models.Model):
    """Model to track which users have access to which ensembles"""

    user = models.ForeignKey(
        'auth.User',
        related_name='ensemble_userships',
        on_delete=models.CASCADE
    )
    ensemble = models.ForeignKey(
        Ensemble,
        related_name='userships',
        on_delete=models.CASCADE
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    class Role(models.TextChoices):
        MEMBER = "M", "member"
        ADMIN = "A", "admin"

    role = models.CharField(max_length=1, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        unique_together = ('user', 'ensemble')
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.user.username} - {self.ensemble.name}"


class Arrangement(models.Model):
    ensemble = models.ForeignKey(
        Ensemble, related_name="arrangements", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    composer = models.CharField(max_length=255, blank=True, null=True)
    act_number = models.IntegerField(blank=True, null=True)
    piece_number = models.IntegerField(default=1, blank=True, null=True)

    mvt_no = models.CharField(max_length=4, blank=True)

    style = models.CharField(choices=STYLE_CHOICES)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Arrangement, self.title, instance=self)

        if not self.style:
            self.style = self.ensemble.default_style

        if self.pk is None:
            super().save(*args, **kwargs)
            if self.mvt_no is None:
                self.mvt_no = self.pk
                super().save(update_fields=["mvt_no"])
        else:
            if self.mvt_no is None:
                self.mvt_no = self.pk
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


class ArrangementVersion(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, related_name="versions", on_delete=models.CASCADE
    )

    file_name = models.CharField()
    version_label = models.CharField(max_length=10, default="0.0.0")  # 1.0.0 or 1.2.3
    timestamp = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=False)
    
    #TODO[SC-241]: Convert these fields to a state field
    is_processing = models.BooleanField(default=True)
    error_on_export = models.BooleanField(default=False)

    class AudioStatus(models.TextChoices):
        NONE = "N", "none"
        PROCESSING = "P", "processing"
        COMPLETE = "C", "complete"
        ERROR = "E", "error"


    audio_state = models.CharField(max_length=1, choices=AudioStatus.choices, default=AudioStatus.NONE)

    num_measures_per_line_score = models.IntegerField()
    num_measures_per_line_part = models.IntegerField()
    num_lines_per_page = models.IntegerField()

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
    def audio_file_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext}.mp3"

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

    @property
    def audio_file_url(self) -> str:
        return default_storage.url(self.audio_file_key)

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
            self.score_parts_pdf_key,
        ]
        
        # Also delete all part PDFs
        for part in self.parts.all():
            if part.file_key not in keys_to_delete:
                keys_to_delete.append(part.file_key)
        
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
        return f"{self.arrangement.__str__()} (v{self.version_label})"

    class Meta:
        ordering = ["-timestamp"]


class Part(models.Model):
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

class ExportFailureLog(models.Model):
    arrangement_version = models.ForeignKey(ArrangementVersion, related_name="failure_log", on_delete=models.CASCADE)
    #Auto-populated with info from 
    error_msg = models.CharField()

    #info that I may want to add
    comments = models.CharField()

    @property
    def arrangement_version__str__(self):
        return self.arrangement_version.__str__()

#TODO: Remove
class Diff(models.Model):
    from_version = models.ForeignKey(
        ArrangementVersion, on_delete=models.CASCADE, related_name="diff_as_source"
    )
    to_version = models.ForeignKey(
        ArrangementVersion, on_delete=models.CASCADE, related_name="diff_as_target"
    )

    file_name = models.CharField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    error_msg = models.CharField(blank=True, null=True)

    @property
    def from_version__str__(self):
        return self.from_version.__str__()

    @property
    def to_version__str__(self):
        return self.to_version.__str__()

    @property
    def file_key(self) -> str:
        return f"ensemble-diffs/{self.from_version.ensemble_slug}/{self.from_version.arrangement_slug}/{self.from_version.version_label}-{self.to_version.version_label}/{self.file_name}"

    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.file_key)

    class Meta:
        unique_together = ("from_version", "to_version")

    def __str__(self):
        return f"Diff {self.from_version} → {self.to_version}"

    def delete(self, **kwargs):
        # Delete files when diff is deleted
        keys_to_delete = [self.file_key]
        logger.warning("Deleting Diff")

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


def _part_upload_key(instance, filename):
    """Generate storage key for part files"""
    ensemble_slug = instance.version.arrangement.ensemble.slug
    arrangement_slug = instance.version.arrangement.slug
    version = instance.version.version_label
    return f"ensembles/{ensemble_slug}/arrangements/{arrangement_slug}/versions/{version}/parts/{filename}"

#holdover from an old migration, can't delete this without squashing migrations
_part_upload_path = _part_upload_key

