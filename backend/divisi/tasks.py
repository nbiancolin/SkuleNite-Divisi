from celery import shared_task
import subprocess
import os

from django.conf import settings

from divisi.part_formatter.processing import mscz_main
from divisi.models import UploadSession


@shared_task
def part_formatter_mscz(
    uuid: int,
    style: str,
    show_title: str | None,
    show_number: str | None,
    num_measure_per_line: int | None,
    version_num: int | None,
    composer: str | None,
    arranger: str | None,
) -> None:
    session = UploadSession.objects.get(id=uuid)

    kwargs = {
        "input_path": session.mscz_file_path,
        "output_path": session.output_file_path,
        "style_name": style,
        "versionNum": version_num if version_num is not None else "1.0.0" #TODO[SC-83]: Move to settings.py
    }

    if arranger is not None:
        kwargs["arranger"] = arranger
    if composer is not None:
        kwargs["compopser"] = composer
        if arranger is None:
            kwargs["arranger"] = composer

    if show_title is not None:
        kwargs["movementTitle"] = show_title
    if show_number is not None:
        kwargs["workNumber"] = show_number
    if num_measure_per_line is not None:
        kwargs["num_measure_per_line"] = num_measure_per_line

    mscz_main(**kwargs)


@shared_task
def export_mscz_to_pdf(uuid: int):
    """
    export parts to "done" location where users can download their files aain
    """
    session = UploadSession.objects.get(id=uuid)
    output_path = session.output_file_path[:-5] + ".pdf"

    try:
        subprocess.run(
            ["mscore4", session.output_file_path, "-o", output_path], check=True
        )
        return {"status": "success", "output": output_path}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}
