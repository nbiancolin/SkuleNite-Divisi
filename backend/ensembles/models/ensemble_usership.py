from django.db import models

from ensembles.models import Ensemble

from logging import getLogger
logger = getLogger("app")

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