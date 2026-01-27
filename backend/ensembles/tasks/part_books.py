from celery import shared_task

from divisi.tasks import format_arrangement_version
from divisi.tasks.export import (
    export_mscz_to_mp3,
    export_all_parts_with_tracking,
)
from ensembles.models import Ensemble, PartAsset, PartBook, PartBookEntry, PartName
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
    
    ensemble = Ensemble.objects.get(id=ensemble_id)
    revision = ensemble.latest_part_book_revision +1

    part_name_ids = PartName.objects.filter(ensemble_id=ensemble_id).values_list("id", flat=True)
    for part_name_id in part_name_ids:
        generate_part_book(ensemble_id, part_name_id, revision)

    ensemble.latest_part_book_revision = revision
    ensemble.save(update_fields=["latest_part_book_revision"])

    return {"status": "success", "ensemble_id": ensemble_id}


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

    ensemble = Ensemble.objects.get(id)

    #first, generate all part book entries for that part name
    #TODO: This should set parent and the revision values
    parent = ensemble.part_books.order_by("-finalized_at")[0]
    part_book = PartBook.objects.create(ensemble_id=ensemble_id, part_name_id=part_name_id, revision=revision, parent=parent)
    ensemble.generate_part_book_entries(part_book=part_book)

    #Then, render the part book
    part_book.render()

    return {"status": "success", "file_key": part_book.pdf_file_key}

