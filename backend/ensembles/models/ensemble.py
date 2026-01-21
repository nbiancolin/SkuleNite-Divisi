from django.db import models
import secrets
from logging import getLogger
from ensembles.models.constants import STYLE_CHOICES
from ensembles.lib.slug import generate_unique_slug

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ensembles.models.arrangement import Arrangement
    from ensembles.models.part import PartName


logger = getLogger("app")



class Ensemble(models.Model):
    
    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager
        arrangements: RelatedManager["Arrangement"]
        part_names: RelatedManager["PartName"]

    name = models.CharField(max_length=30)
    slug = models.SlugField(unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    default_style = models.CharField(max_length=10, choices=STYLE_CHOICES)
    
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
        return self.arrangements.count()

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