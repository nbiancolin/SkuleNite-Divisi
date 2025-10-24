from celery import shared_task
import tempfile

import os
import shutil

from django.core.files import File
from django.core.files.storage import default_storage

from musescore_part_formatter import format_mscz, FormattingParams
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
) -> dict:
    session = UploadSession.objects.get(id=uuid)

    kwargs: FormattingParams = {
        "selected_style": style,
        "versionNum": version_num if version_num is not None else "1.0.0"
    }

    if show_title is not None:
        kwargs["movementTitle"] = show_title
    if show_number is not None:
        kwargs["workNumber"] = show_number

    kwargs["arranger"] = arranger if arranger is not None else "COMPOSER"
    if composer is not None:
        kwargs["composer"] = composer  # fixed key name

    if num_measure_per_line is not None:
        kwargs["num_measure_per_line"] = num_measure_per_line

    tmp_in_path = tmp_out_path = None
    try:
        # create temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mscz") as tmp_in:
            tmp_in_path = tmp_in.name
            # download mscz from storage into tmp_in
            with default_storage.open(session.mscz_file_key, "rb") as stored_in:
                shutil.copyfileobj(stored_in, tmp_in)
                tmp_in.flush()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            tmp_out_path = tmp_out.name

        # call the formatter which expects input/output paths
        format_result = format_mscz(tmp_in_path, tmp_out_path, **kwargs)

        # If your format_mscz returns structured result, check for errors
        if isinstance(format_result, dict) and format_result.get("status") == "error":
            return format_result

        # upload generated file back to storage at session.output_file_key
        with open(tmp_out_path, "rb") as out_f:
            django_file = File(out_f)
            default_storage.save(session.output_file_key, django_file)

        # mark session completed and return public URL
        session.completed = True
        session.save(update_fields=["completed"])

        return {"status": "success", "output": default_storage.url(session.output_file_key)}
    finally:
        # cleanup temp files if created
        if tmp_in_path and os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)
        if tmp_out_path and os.path.exists(tmp_out_path):
            os.remove(tmp_out_path)


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
