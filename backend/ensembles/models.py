from django.db import models
from django.utils.text import slugify

STYLE_CHOICES = [
    ("jazz", "Jazz"),
    ("broadway", "Broadway"),
    ("classical", 'Classical')
]

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
    piece_number = models.IntegerField(default=1, blank=True, null=True) #NOTE: This field is auto-populated on save... should never actually be blank

    default_style = models.CharField(choices=STYLE_CHOICES)

    #TODO: Make this a little cleaner, might not be optimal
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
    
    def __str__(self):
        return f"{self.mvt_no}: {self.title} (v{self.latest_version_num})"

    class Meta:
        ordering = ["act_number", "piece_number"]



class ArrangementVersion(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, related_name="versions", on_delete=models.CASCADE
    )
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

        if not self.pk and version_type:
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

    def __str__(self):
        return f"{self.arrangement.__str__} (v{self.version_label})"

    class Meta:
        ordering = ["-timestamp"]
        unique_together = ("arrangement", "version_label")


def _part_upload_path(instance, filename):
    ensemble = instance.version.arrangement.ensemble.name.replace(" ", "_")
    arrangement = instance.version.arrangement.title.replace(" ", "_")
    version = instance.version.version_label
    return f"blob/PDF/{ensemble}/{arrangement}/{version}/{filename}" #TODO: Move this to use media/static root


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
