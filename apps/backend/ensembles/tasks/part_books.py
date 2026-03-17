from celery import shared_task

from divisi.tasks import format_arrangement_version
from divisi.tasks.export import (
    export_mscz_to_mp3,
    export_all_parts_with_tracking,
)
from ensembles.models import (
    Ensemble,
    PartAsset,
    PartBook,
    PartBookEntry,
    PartName,
)
from logging import getLogger
from django.core.files.storage import default_storage
import os

logger = getLogger("part_book_tasks")


@shared_task
def generate_books_for_ensemble(ensemble_id: int, custom_versions: dict[int, int] = {}):
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
        PartName.objects.filter(ensemble_id=ensemble_id).values_list("id", flat=True)
    )
    if not part_name_ids:
        ensemble.part_books_generating = False
        ensemble.save(update_fields=["part_books_generating"])
        return {"status": "no action", "detail": "No part names in ensemble"}

    try:
        for part_name_id in part_name_ids:
            generate_part_book(ensemble_id, part_name_id, revision)

        ensemble.latest_part_book_revision = revision
        ensemble.part_books_generating = False
        ensemble.save(update_fields=["part_books_generating", "latest_part_book_revision"])

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
def generate_part_book(ensemble_id: int, part_name_id: int, revision: int, custom_versions: dict[int, int] = {}):
    """
    Generate a part book for a specific part in an ensemble

    :param ensemble_id: Id of the ensemble to use
    :type ensemble_id: int
    :param part_name_id: Id of the part name object to use
    :type part_name_id: int
    :param custom_versions: dict[arrangement_id, arrangement_version_id]. If you want to use a custom version for any arrangements, pass it in here. Currently not supported
    :type custom_versions: dict[int, int]
    """
    ensemble = Ensemble.objects.get(id=ensemble_id)
    part_name = PartName.objects.get(id=part_name_id)

    # First, get parent (previous revision) if any
    parent = None
    if ensemble.part_books.exists():
        parent = ensemble.part_books.order_by("-finalized_at").first()

    part_book = PartBook.objects.create(
        ensemble_id=ensemble_id,
        part_name_id=part_name_id,
        revision=revision,
        parent=parent,
    )

    try:
        ensemble.generate_part_book_entries(part_book=part_book)

        # Then, render the part book
        part_book.render()

        # If all part books for this revision are now finalized, clear the generating flag
        part_name_count = PartName.objects.filter(ensemble_id=ensemble_id).count()
        finalized_count = PartBook.objects.filter(
            ensemble_id=ensemble_id, revision=revision, finalized_at__isnull=False
        ).count()
        if finalized_count >= part_name_count:
            ensemble.part_books_generating = False
            ensemble.save(update_fields=["part_books_generating"])

        return {"status": "success", "file_key": part_book.pdf_file_key}

    except Exception as e:
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

