from logging import getLogger

from celery import shared_task

from ensembles.lib.part_book_layout import resolve_part_book_layout
from ensembles.lib.part_name_matrix import part_names_with_latest_part_assets
from ensembles.models import (
    Ensemble,
    PartBook,
    PartName,
)
from ensembles.models.constants import PART_BOOK_LAYOUT_CHOICES

logger = getLogger("part_book_tasks")


VALID_LAYOUTS = {choice[0] for choice in PART_BOOK_LAYOUT_CHOICES}


@shared_task
def generate_books_for_ensemble(
    ensemble_id: int,
    custom_versions: dict[int, int] = {},
    layout_overrides: dict[int, str] | None = None,
):
    """
    Generate all part books for a given ensemble

    :param ensemble_id: Id of the ensemble to use
    :type ensemble_id: int
    :param custom_versions: dict[arrangement_id, arrangement_version_id]. If you want to use a custom version for any arrangements, pass it in here
    :type custom_versions: dict[int, int]
    """
    try:
        ensemble = Ensemble.objects.get(id=ensemble_id)
    except Ensemble.DoesNotExist:
        return {"status": "error", "detail": f"Ensemble {ensemble_id} not found"}

    if ensemble.part_books_generating is True:
        return {"status": "no action", "detail": "Part books already triggering"}

    ensemble.part_books_generating = True
    ensemble.save(update_fields=["part_books_generating"])
    revision = ensemble.latest_part_book_revision + 1

    part_name_ids = list(
        part_names_with_latest_part_assets(ensemble).values_list("id", flat=True)
    )
    if not part_name_ids:
        ensemble.part_books_generating = False
        ensemble.save(update_fields=["part_books_generating"])
        return {
            "status": "no action",
            "detail": "No part names with uploaded parts in latest arrangement versions",
        }

    layout_overrides = layout_overrides or {}

    try:
        for part_name_id in part_name_ids:
            one_off_layout = layout_overrides.get(part_name_id)
            if one_off_layout is not None and one_off_layout not in VALID_LAYOUTS:
                raise ValueError(f"Invalid layout override: {one_off_layout}")
            generate_part_book(
                ensemble_id,
                part_name_id,
                revision,
                one_off_layout=one_off_layout,
            )

        ensemble.latest_part_book_revision = revision
        ensemble.part_books_generating = False
        ensemble.save(
            update_fields=["part_books_generating", "latest_part_book_revision"]
        )

        return {"status": "success", "ensemble_id": ensemble_id}
    except Exception:
        # If any part book failed, generate_part_book already cleared part_books_generating
        # ensure flag is clear and re-raise
        ensemble.refresh_from_db()
        if ensemble.part_books_generating:
            ensemble.part_books_generating = False
            ensemble.save(update_fields=["part_books_generating"])
        raise


@shared_task
def generate_part_book(
    ensemble_id: int,
    part_name_id: int,
    revision: int,
    custom_versions: dict[int, int] = {},
    one_off_layout: str | None = None,
    solo: bool = False,
):
    """
    Generate a part book for a specific part in an ensemble

    :param ensemble_id: Id of the ensemble to use
    :type ensemble_id: int
    :param part_name_id: Id of the part name object to use
    :type part_name_id: int
    :param custom_versions: dict[arrangement_id, arrangement_version_id]. If you want to use a custom version for any arrangements, pass it in here. Currently not supported
    :type custom_versions: dict[int, int]
    """
    ensemble = Ensemble.objects.select_related().get(id=ensemble_id)
    part_name = PartName.objects.select_related("ensemble").get(id=part_name_id)

    if one_off_layout is not None and one_off_layout not in VALID_LAYOUTS:
        raise ValueError(f"Invalid layout: {one_off_layout}")

    resolved_layout = resolve_part_book_layout(
        part_name, one_off_layout=one_off_layout
    )

    # First, get parent (previous revision) if any
    parent = None
    if ensemble.part_books.exists():
        parent = ensemble.part_books.order_by("-finalized_at").first()

    part_book = PartBook.objects.create(
        ensemble_id=ensemble_id,
        part_name_id=part_name_id,
        revision=revision,
        parent=parent,
        layout=resolved_layout,
    )

    try:
        ensemble.generate_part_book_entries(part_book=part_book)

        # Then, render the part book
        part_book.render()

        # If all part books for this revision are now finalized, clear the generating flag
        if solo:
            ensemble.part_books_generating = False
            ensemble.save(update_fields=["part_books_generating"])
        else:
            part_name_count = part_names_with_latest_part_assets(ensemble).count()
            finalized_count = PartBook.objects.filter(
                ensemble_id=ensemble_id, revision=revision, finalized_at__isnull=False
            ).count()
            if finalized_count >= part_name_count:
                ensemble.part_books_generating = False
                ensemble.save(update_fields=["part_books_generating"])

        return {"status": "success", "file_key": part_book.pdf_file_key}

    except Exception:
        logger.exception(
            "Part book generation failed: ensemble_id=%s part_name=%s revision=%s",
            ensemble_id,
            part_name.display_name,
            revision,
        )
        ensemble.part_books_generating = False
        ensemble.save(update_fields=["part_books_generating"])
        # Remove the part book we created so we don't leave an unfinalized orphan
        part_book.delete()
        raise
