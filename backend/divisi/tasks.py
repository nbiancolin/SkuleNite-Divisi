from celery import shared_task
import subprocess
import tempfile

import os

from django.core.files.storage import default_storage

from divisi.part_formatter.processing import mscz_main
from divisi.part_formatter.export import export_mscz_to_pdf_score
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
        "input_key": session.mscz_file_key,
        "output_key": session.output_file_key,
        "style_name": style,
        "versionNum": version_num if version_num is not None else "1.0.0" #TODO[SC-83]: Move to settings.py
    }

    if arranger is not None:
        kwargs["arranger"] = arranger
    else:
        kwargs["arranger"] = "COMPOSER"
    if composer is not None:
        kwargs["compopser"] = composer

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
    Export MSCZ to PDF, store it back into storage, and return the URL.
    """
    session = UploadSession.objects.get(id=uuid)

    # Build output key (replace .mscz with .pdf)
    output_key = session.output_file_key.rsplit(".", 1)[0] + ".pdf"

    # Create temp files for input and output
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mscz") as tmp_in, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:

        tmp_in_path = tmp_in.name
        tmp_out_path = tmp_out.name

        # Download from storage into tmp_in
        with default_storage.open(session.output_file_key, "rb") as f:
            tmp_in.write(f.read())
            tmp_in.flush()

        # Run musescore on temp files
        res = export_mscz_to_pdf_score(tmp_in_path, tmp_out_path)
        if res["status"] == "error":
            return res

        # Upload generated PDF to storage
        with open(tmp_out_path, "rb") as pdf_file:
            default_storage.save(output_key, pdf_file)

    # Clean up temp files
    os.remove(tmp_in_path)
    os.remove(tmp_out_path)

    return {"status": "success", "output": default_storage.url(output_key)}
