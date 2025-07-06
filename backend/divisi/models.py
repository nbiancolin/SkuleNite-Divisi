from django.db import models


class Ensemble(models.Model):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name


class Arrangement(models.Model):
    ensemble = models.ForeignKey(
        Ensemble, related_name="arrangements", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    act_number = models.IntegerField(default=1)
    piece_number = models.IntegerField(default=1)

    def get_mvtno(self):
        return f"{self.act_number}-{self.piece_number}"

    def __str__(self):
        return f"{self.act_number}-{self.piece_number}: {self.title}"

    @property
    def mvt_no(self):
        return self.get_mvtno()

    @property
    def latest(self):
        return self.versions.filter(is_latest=True).first()

    class Meta:
        ordering = ["act_number", "piece_number"]


class ArrangementVersion(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, related_name="versions", on_delete=models.CASCADE
    )
    version_label = models.CharField(max_length=10, default="1.0.0")  # 1.0.0 or v1.2.3
    timestamp = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.arrangement.__str__} (v{self.version_label})"

    class Meta:
        ordering = ["-timestamp"]
        unique_together = ("arrangement", "version_label")


def _part_upload_path(instance, filename):
    ensemble = instance.version.arrangement.ensemble.title.replace(" ", "_")
    arrangement = instance.version.arrangement.title.replace(" ", "_")
    version = instance.version.version_label
    return f"{ensemble}/{arrangement}/{version}/{filename}"


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
