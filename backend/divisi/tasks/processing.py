import tempfile
import os
import shutil

from django.core.files import File
from django.core.files.storage import default_storage

from musescore_part_formatter import format_mscz, FormattingParams

from divisi.models import UploadSession
from ensembles.models import ArrangementVersion

from logging import getLogger

from celery import shared_task

LOGGER = getLogger("divisi_processing")

def _format_mscz_file(input_key: str, output_key: str, formatting_params: FormattingParams) -> dict[str, str]:
    """Internal fn to format a mscz file. Reads in the file from the key, and writes it back"""

    tmp_in_path = tmp_out_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mscz") as tmp_in:
            tmp_in_path = tmp_in.name
            with default_storage.open(input_key, "rb") as stored_in:
                shutil.copyfileobj(stored_in, tmp_in)
                tmp_in.flush()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            tmp_out_path = tmp_out.name

        success = format_mscz(tmp_in_path, tmp_out_path, formatting_params)

        if success is False:
            LOGGER.error("Error from musescore_part_formatter")
            return {"status": "error", "details": "unknown part formatter error"}

        # upload generated file back to storage at session.output_file_key
        with open(tmp_out_path, "rb") as out_f:
            django_file = File(out_f)
            default_storage.save(output_key, django_file)

        LOGGER.info(f"Successfully formatted file: {output_key}")
        return {"status": "success", "output": output_key}
    except Exception as e:
        LOGGER.error(f"Error on formatting file {input_key}, {str(e)}", exc_info=True)
        return {"status": "error", "details": str(e)}
    finally:
        # cleanup temp files if created

        #TODO: Is this ever reached?
        if tmp_in_path and os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)
        if tmp_out_path and os.path.exists(tmp_out_path):
            os.remove(tmp_out_path)


@shared_task
def format_upload_session(session_id: int, **kwargs) -> dict[str, str]:
    """ Takes in divisi.UploadSession obj id, and formats it"""

    session = UploadSession.objects.get(id=session_id)

    input_key = session.mscz_file_key
    output_key = session.output_file_key

    params : FormattingParams = {
        "selected_style": kwargs.get("selected_style"),
        "show_title": kwargs.get("show_title"),
        "show_number": kwargs.get("show_number"),
        "num_measures_per_line_score": kwargs.get("num_measures_per_line_score"),
        "num_measures_per_line_part": kwargs.get("num_measures_per_line_part"),
        "num_lines_per_page": kwargs.get("num_lines_per_page"),
    }

    return _format_mscz_file(input_key, output_key, params)


@shared_task
def format_arrangement_version(version_id: int) -> dict[str, str]:

    version = ArrangementVersion.objects.get(id=version_id)

    input_key = version.mscz_file_key
    output_key = version.output_file_key

    params: FormattingParams = {
        "selected_style": version.arrangement.style,
        "show_title": version.ensemble_name,
        "show_number": version.arrangement.mvt_no,
        "num_measures_per_line_score": version.num_measures_per_line_score,
        "num_measures_per_line_part": version.num_measures_per_line_part,
        "num_lines_per_page": version.num_lines_per_page,
    }

    return _format_mscz_file(input_key, output_key, params)