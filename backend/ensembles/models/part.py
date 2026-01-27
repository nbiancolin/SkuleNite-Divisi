from io import BytesIO
from django.db import models
from django.core.files.storage import default_storage

from ensembles.models.arrangement_version import ArrangementVersion
from ensembles.lib.slug import generate_unique_slug

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


class PartName(models.Model):
    id: int

    ensemble = models.ForeignKey(
        "ensembles.Ensemble", related_name="part_names", on_delete=models.CASCADE
    )

    display_name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)

    def save(self, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(PartName, self.display_name, instance=self)
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

        from ensembles.lib.pdf import TocEntry

        book_data = []
        for entry in entries:
            # get TOC entries
            e: TocEntry = {
                "show_number": entry.arrangement.mvt_no,
                "title": entry.arrangement.title,
                "version_label": entry.arrangement_version.version_label,
                "page": -1,  # Dummy value for now
            }

            # get file pdf as bytesIO object
            with default_storage.open(entry.part_asset.file_key, "rb") as f:
                file = BytesIO(f.read())
            book_data.append((e, file))

        from ensembles.lib.pdf import (
            generate_full_part_book,
            generate_cover_page,
            PartBookInfo,
        )

        cover_pdf = generate_cover_page(
            export_date=str(self.created_at),
            part_name=self.name,
            show_title=self.ensemble.name,
        )

        from datetime import datetime

        export_datetime = datetime.now()

        toc_kwargs: PartBookInfo = {
            "show_title": self.ensemble.name,
            "show_subtitle": "",
            "export_date": str(export_datetime),  # TODO: datetime.now
            "part_name": self.name,
            "selected_style": self.ensemble.default_style,
        }

        buf = generate_full_part_book(
            cover_pdf=cover_pdf, toc_kwargs=toc_kwargs, content_pdfs=book_data
        )


        #write buf to filesystem
        with default_storage.open(self.pdf_file_key, "wb") as f:
            f.write(buf)

        for _, f in book_data:
            f.close()

        self.finalized_at = export_datetime
        self.save()

        


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

    part_asset = models.ForeignKey("ensembles.PartAsset", on_delete=models.PROTECT)

    # When building a part book, compute this value from the Arrangement's mvt_no. This determines the order in the book
    position = models.PositiveIntegerField()
