from django.db import models
from django.conf import settings


class UserScoreCommit(models.Model):
    """
    This model tracks the version of the score the user downloaded. 

    In a 3 way merge, this would be the base  
    
    """

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE
    )

    arrrangement = models.ForeignKey(
        "ensembles.Arrangement",
        on_delete=models.CASCADE
    )

    commit = models.ForeignKey(
        "ensembles.Commit",
        on_delete=models.CASCADE,
    )


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "arrangement"], name="user_and_arrangement_must_be_unique")
        ]