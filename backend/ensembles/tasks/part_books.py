from celery import shared_task

from divisi.tasks import format_arrangement_version
from divisi.tasks.export import (
    export_mscz_to_mp3,
    export_all_parts_with_tracking,
)
from ensembles.models import ArrangementVersion, ExportFailureLog
from logging import getLogger
from django.core.files.storage import default_storage
import os

logger = getLogger("part_book_tasks")


@shared_task
def generate_books_for_ensemble():
    pass