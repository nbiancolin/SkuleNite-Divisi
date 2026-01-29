from io import BytesIO
from pathlib import Path
from datetime import datetime
from django.db import models
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError

from ensembles.models.arrangement_version import ArrangementVersion
from ensembles.lib.slug import generate_unique_slug
from ensembles.lib.pdf import TocEntry
from ensembles.lib.pdf import (
    generate_full_part_book,
    generate_cover_page,
    generate_tacet_page,
    PartBookInfo,
)

from typing import TYPE_CHECKING

from logging import getLogger

logger = getLogger("app")


class PartAsset(models.Model):
    """Model to track individual part PDFs for an ArrangementVersion"""

    arrangement_version = models.ForeignKey(
        ArrangementVersion, related_name="parts", on_delete=models.CASCADE
    )
    # TODO: Backfill/delete any part assets that dont have a NameObj associated, and remove this null=True
    part_name = models.ForeignKey("PartName", on_delete=models.PROTECT, null=True)
    file_key = models.CharField(max_length=500)  # Storage key for the PDF file
    is_score = models.BooleanField(default=False)  # True if this is the full score PDF

    def save(self, **kwargs) -> None:
        if self.part_name is None:
            raise NotImplementedError("Cannot create a PartAsset without a NameObj")
        return super().save(**kwargs)

    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.file_key)

    @property
    def name(self):
        return self.part_name.display_name if self.part_name else "No NameObj Record"

    def __str__(self):
        part_type = "Score" if self.is_score else "Part"
        return f"{part_type}: {self.name} ({self.arrangement_version})"

    class Meta:
        ordering = [
            "-is_score"
        ]  # Score first (True before False), then parts alphabetically

        constraints = [
            models.UniqueConstraint(
                fields=["arrangement_version", "part_name"],
                name="uniq_partasset_version_partname",
            ),
        ]
    

class PartName(models.Model):
    id: int

    ensemble_id: int
    ensemble = models.ForeignKey(
        "ensembles.Ensemble", related_name="part_names", on_delete=models.CASCADE
    )

    display_name = models.CharField(max_length=64)
    # SLUG should be unique per ensemble -- not for all part names
    slug = models.SlugField()

    def save(self, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                PartName,
                self.display_name,
                instance=self,
                queryset=PartName.objects.filter(ensemble_id=self.ensemble_id),
            )
        super().save(**kwargs)

    def __str__(self):
        return f"{self.display_name} ({self.ensemble.name})"

    def _merge_objs(self, second: "PartName"):
        """Merge `second` into `self`. Deletes `second` afterwards"""
        second_part_asset_ids = PartAsset.objects.filter(part_name=second).values_list(
            "id", flat=True
        )
        PartAsset.objects.filter(id__in=second_part_asset_ids).update(
            part_name_id=self.id
        )
        second.delete()

    @staticmethod
    def normalize_display_name(value: str) -> str:
        # Normalize for stable matching (case/whitespace-insensitive).
        return " ".join((value or "").strip().lower().split())

    @classmethod
    def resolve_for_arrangement(
        cls, ensemble, arrangement, raw_display_name: str
    ) -> "PartName":
        """
        Resolve an incoming/raw part label to a canonical PartName for this arrangement.

        This first checks persisted aliases (created when users merge/rename parts),
        scoped per arrangement so re-uploading arrangement A uses A's alias.
        Then falls back to a case-insensitive match on PartName.display_name, and
        finally creates a new PartName if nothing matches.
        """
        from ensembles.models.part_name_alias import PartNameAlias

        normalized = cls.normalize_display_name(raw_display_name)

        if arrangement is not None:
            alias = (
                PartNameAlias.objects.select_related("canonical_part_name")
                .filter(
                    ensemble=ensemble,
                    arrangement=arrangement,
                    alias_normalized=normalized,
                )
                .first()
            )
            if alias is not None:
                return alias.canonical_part_name

        existing = (
            cls.objects.filter(ensemble=ensemble, display_name__iexact=raw_display_name)
            .order_by("id")
            .first()
        )
        if existing is not None:
            return existing

        return cls.objects.create(ensemble=ensemble, display_name=raw_display_name)

    @classmethod
    def merge_part_names(
        cls, first: "PartName", second: "PartName", new_displayname: str = ""
    ) -> "PartName":
        if (
            PartAsset.objects.filter(part_name=second).count()
            > PartAsset.objects.filter(part_name=first).count()
        ):
            target = second
            merge_from = first
            if not new_displayname:
                new_displayname = first.display_name
        else:
            target = first
            merge_from = second

        # Before merging, ensure we will not end up with multiple PartAsset
        # objects for the same ArrangementVersion under the final part name.
        existing_versions = set(
            PartAsset.objects.filter(part_name=target).values_list(
                "arrangement_version_id", flat=True
            )
        )
        incoming_versions = set(
            PartAsset.objects.filter(part_name=merge_from).values_list(
                "arrangement_version_id", flat=True
            )
        )
        if existing_versions.intersection(incoming_versions):
            raise ValidationError(
                "Cannot merge part names: multiple parts exist for the same "
                "arrangement version under the merged name."
            )

        # Persist the merge intent as aliases per arrangement so re-uploading
        # arrangement A uses A's alias (e.g. "Flute I" -> Flute) and B uses B's.
        from ensembles.models.part_name_alias import PartNameAlias

        previous_target_name = target.display_name
        previous_merge_from_name = merge_from.display_name
        ensemble_id = target.ensemble_id

        # Arrangements that had a part under the name we're merging away:
        # when we re-upload that arrangement, we want "merge_from" label -> target.
        arrangements_with_merge_from = set(
            PartAsset.objects.filter(part_name=merge_from)
            .values_list("arrangement_version__arrangement_id", flat=True)
        )
        arrangements_with_merge_from.discard(None)

        with transaction.atomic():
            # Re-point any existing aliases that targeted the "merge_from" PartName.
            PartNameAlias.objects.filter(
                ensemble_id=ensemble_id, canonical_part_name=merge_from
            ).update(canonical_part_name=target)

            # Create/ensure an alias (merge_from name -> target) per arrangement
            # that had that part, so re-uploading that arrangement uses the alias.
            for arr_id in arrangements_with_merge_from:
                PartNameAlias.objects.update_or_create(
                    ensemble_id=ensemble_id,
                    arrangement_id=arr_id,
                    alias_normalized=PartNameAlias.normalize(previous_merge_from_name),
                    defaults={
                        "alias": previous_merge_from_name,
                        "canonical_part_name": target,
                    },
                )

            # If we are renaming the canonical display name, keep the old canonical name
            # as an alias too for arrangements that had the target part.
            if new_displayname and PartNameAlias.normalize(previous_target_name) != PartNameAlias.normalize(new_displayname):
                arrangements_with_target = set(
                    PartAsset.objects.filter(part_name=target)
                    .values_list("arrangement_version__arrangement_id", flat=True)
                )
                arrangements_with_target.discard(None)
                for arr_id in arrangements_with_target:
                    PartNameAlias.objects.update_or_create(
                        ensemble_id=ensemble_id,
                        arrangement_id=arr_id,
                        alias_normalized=PartNameAlias.normalize(previous_target_name),
                        defaults={
                            "alias": previous_target_name,
                            "canonical_part_name": target,
                        },
                    )

            # Merge actual PartAsset references and delete the redundant PartName.
            target._merge_objs(merge_from)

            if new_displayname:
                target.display_name = new_displayname
                target.save(update_fields=["display_name"])

        return target


class PartBook(models.Model):
    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager

        entries: RelatedManager["PartBookEntry"]

    ensemble = models.ForeignKey(
        "ensembles.Ensemble", related_name="part_books", on_delete=models.CASCADE
    )
    part_name = models.ForeignKey(
        PartName, related_name="part_books", on_delete=models.CASCADE
    )

    revision = models.PositiveIntegerField()

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_rendered(self) -> bool:
        return self.finalized_at is not None

    @property
    def name(self) -> str:
        return self.part_name.display_name

    @property
    def file_name(self) -> str:
        # TODO: add # in front here (eg. 01 - Flute (.pdf))
        return f"{self.name}-{self.ensemble.name}_({self.created_at}).pdf"

    @property
    def pdf_file_key(self):
        return f"ensembles/{self.ensemble.slug}/_part-books/{self.part_name.display_name}/{self.revision}/{self.file_name}"

    def render(self):
        """
        Take the part book itself, render its contents to a PDF.
        """

        assert self.entries.count() > 0, "Part book must be built before rendering"

        entries = self.entries.order_by("position")
        export_datetime = datetime.now()
        export_date_str = str(export_datetime)

        book_data = []
        for entry in entries:
            # get TOC entries
            e: TocEntry = {
                "show_number": entry.arrangement.mvt_no,
                "title": entry.arrangement.title,
                "version_label": entry.arrangement_version.version_label,
                "page": -1,  # Dummy value for now
            }

            if entry.part_asset is not None:
                # get file pdf as bytesIO object
                with default_storage.open(entry.part_asset.file_key, "rb") as f:
                    file = BytesIO(f.read())
                book_data.append((e, file))
            else:
                # No part for this arrangement; generate a tacet page
                tacet_pdf = generate_tacet_page(
                    show_title=self.ensemble.name,
                    show_number=entry.arrangement.mvt_no,
                    export_date=export_date_str,
                    song_title=entry.arrangement.title,
                    song_subtitle="",
                    part_name=self.name,
                    selected_style=self.ensemble.default_style,
                )
                book_data.append((e, tacet_pdf))

        cover_pdf = generate_cover_page(
            export_date=str(self.created_at),
            part_name=self.name,
            show_title=self.ensemble.name,
        )

        toc_kwargs: PartBookInfo = {
            "show_title": self.ensemble.name,
            "show_subtitle": "",
            "export_date": str(export_datetime),
            "part_name": self.name,
            "selected_style": self.ensemble.default_style,
        }

        buf = generate_full_part_book(
            cover_pdf=cover_pdf, toc_kwargs=toc_kwargs, content_pdfs=book_data
        )

        # write buf to filesystem (ensure parent dir exists for FileSystemStorage)
        if hasattr(default_storage, "path"):
            parent = Path(default_storage.path(self.pdf_file_key)).parent
            parent.mkdir(parents=True, exist_ok=True)
        with default_storage.open(self.pdf_file_key, "wb") as f:
            f.write(buf.getvalue())

        for _, f in book_data:
            f.close()

        self.finalized_at = export_datetime
        self.save(update_fields=["finalized_at"])

    # Constraint that ensemble, partName and revision are all unique to eachother
    class Meta:
        unique_together = ("ensemble", "part_name", "revision")


class PartBookEntry(models.Model):
    part_book = models.ForeignKey(
        PartBook, related_name="entries", on_delete=models.CASCADE
    )

    arrangement = models.ForeignKey("ensembles.Arrangement", on_delete=models.CASCADE)
    arrangement_version = models.ForeignKey(
        "ensembles.ArrangementVersion", on_delete=models.CASCADE
    )

    part_asset = models.ForeignKey(
        "ensembles.PartAsset", on_delete=models.PROTECT, null=True, blank=True
    )

    # When building a part book, compute this value from the Arrangement's mvt_no. This determines the order in the book
    position = models.PositiveIntegerField()