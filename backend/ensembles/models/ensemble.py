from django.db import models
from django.apps import apps
import secrets
from logging import getLogger
from ensembles.models.constants import STYLE_CHOICES
from ensembles.lib.slug import generate_unique_slug

from django.db.models.expressions import RawSQL

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


    part_books_generating = models.BooleanField(default=False)
    latest_part_book_revision = models.IntegerField(default=1)
    
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


    #TODO: Allow for passing in custom revisions of arrangements here
    def generate_part_book_entries(self, part_book):
        """Given a part book, generate part book entries for all the arrangements in this ensemble."""

        PartBookEntry = apps.get_model("ensembles.PartBookEntry")
        PartAsset = apps.get_model("ensembles.PartAsset")

        arrangements = (
            self.arrangements
            .annotate(
                first_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^([0-9]+)'))[1] AS INTEGER)",
                    []
                ),
                second_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^[0-9]+(?:-|m)([0-9]+)'))[1] AS INTEGER)",
                    []
                ),
            )
            .order_by("first_num", "second_num", "mvt_no")
        )

        position = 0
        for arrangement in arrangements:
            if arrangement.latest_version is None:
                continue
            part_asset = PartAsset.objects.filter(
                arrangement_version=arrangement.latest_version,
                part_name=part_book.part_name,
                is_score=False,
            ).first()
            # Create entry with or without part_asset; when None, render will generate a tacet page
            PartBookEntry.objects.create(
                part_book=part_book,
                arrangement=arrangement,
                arrangement_version=arrangement.latest_version,
                part_asset=part_asset,
                position=position,
            )
            position += 1


    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Ensemble, self.name, instance=self)
        super().save(*args, **kwargs)