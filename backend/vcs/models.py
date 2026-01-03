from django.db import models

class ScoreRepository(models.Model):
    arrangement = models.OneToOneField("ensembles.Arrangement", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class ScoreVersion(models.Model):
    score = models.ForeignKey(ScoreRepository, on_delete=models.CASCADE)
    git_commit = models.CharField(max_length=40)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True
    )

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )

    canonical_hash = models.CharField(max_length=64)

