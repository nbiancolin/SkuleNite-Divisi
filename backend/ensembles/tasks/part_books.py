from celery import shared_task

from divisi.tasks import format_arrangement_version
from divisi.tasks.export import (
    export_mscz_to_mp3,
    export_all_parts_with_tracking,
)
from ensembles.models import Ensemble, PartAsset, PartBook, PartBookEntry
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
    

    #TODO: Do these after the other part logic is set up



    pass


@shared_task
def generate_part_book(ensemble_id: int, part_name_id: int, custom_versions: dict[int, int] = {}):
    """
    Generate a part book for a specific part in an ensemble
    
    :param ensemble_id: Id of the ensemble to use
    :type ensemble_id: int
    :param part_name_id: Id of the part name object to use
    :type part_name_id: int
    :param custom_versions: dict[arrangement_id, arrangement_version_id]. If you want to use a custom version for any arrangements, pass it in here
    :type custom_versions: dict[int, int]
    """
    pass