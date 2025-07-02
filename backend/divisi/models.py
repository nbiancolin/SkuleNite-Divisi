from django.db import models


class Ensemble(models.Model):
    title = models.CharField(max_length=120)

    def __str__(self):
        return self.title


class Arrangement(models.Model):
    ensemble = models.ForeignKey(Ensemble, related_name='arrangements', on_delete=models.CASCADE)
    title=models.CharField(max_length=255)
    subtitle=models.CharField(max_length=255)
    

    def __str__(self):
        return f"{self.title} (v{self.version})"

class ArrangementVersion(models.Model):
    arrangement = models.ForeignKey(Arrangement, related_name='versions', on_delete=models.CASCADE)
    version=models.CharField(max_length=5) #1.0.0 or v1.2.3
    timestamp = models.DateTimeField(auto_now_add=True)


def _part_upload_path(instance, filename):
    ensemble = instance.version.arrangement.ensemble.title
    arrangement = instance.version.arrangement.title
    version = instance.version.version_label
    return f"{ensemble}/{arrangement}/{version}/"


class Part(models.Model):
    arrangement = models.ForeignKey(Arrangement, related_name='parts', on_delete=models.CASCADE)
    part_name = models.CharField(max_length=120)
    filename = models.FileField(upload_to=_part_upload_path) #TODO: Have this be a dynamic location, store parts in {ensemble}/{arrangement}/{version}/{partname}.pdf
    

    def __str__(self):
        return f"{self.title} - {self.part_name} (v{self.arrangement.version})"


class ScoreOrder(models.Model):
    ensemble = models.OneToOneField(Ensemble, related_name='score_order', on_delete=models.CASCADE)

    def __str__(self):
        return f"Score Order for {self.ensemble.title}"


class ScoreOrderEntry(models.Model):
    score_order = models.ForeignKey(ScoreOrder, related_name='entries', on_delete=models.CASCADE)
    part_title = models.CharField(max_length=120)
    score_order_id = models.PositiveIntegerField()

    class Meta:
        unique_together = ('score_order', 'score_order_id')
        ordering = ['score_order_id']

    def __str__(self):
        return f"{self.score_order_id:02d} - {self.part_title}"