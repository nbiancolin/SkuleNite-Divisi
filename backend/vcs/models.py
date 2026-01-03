from django.db import models

class ScoreRepository(models.Model):
    """ This model is where the git things live. So as to not point everything to arrangement versons """
    arrangement = models.OneToOneField("ensembles.Arrangement", on_delete=models.CASCADE)


class ScoreVersion(models.Model):
    """ Django Model that models git commits """
    score = models.ForeignKey(to=ScoreRepository, on_delete=models.PROTECT) #should delete all versions before deleting repo
    commit_hash = models.CharField(max_length=64, unique=True)

    created_by = models.ForeignKey(to="auth.User", null=True, on_delete=models.SET_NULL) 
    created_at = models.DateTimeField(auto_now_add=True)

    message = models.CharField(max_length=100)



class ScoreDownload(models.Model):
    """
    Tracks what version of a score a user downloaded
    This is used when merging changes, which versio is considered the "Base" version in the 3 way merge strategy
    """

    user = models.ForeignKey(to="auth.User", on_delete=models.CASCADE)
    score = models.ForeignKey(to=ScoreRepository, on_delete=models.CASCADE)

    version = models.ForeignKey(to=ScoreVersion, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="user_and_score_must_be_unique",
                fields=["user", "score"]
            )
        ]
