import os
import shutil
import tempfile
from logging import getLogger

from celery import shared_task
from django.core.files import File
from django.core.files.storage import default_storage
from mscz_formatter.mscz.format import format_mscz

from divisi.lib.musescore_headless import export_all_mpos
from divisi.models import UploadSession
from ensembles.formatting_steps_constants import (
    FORMATTING_STEP_KEYS,
    LINE_BREAK_STEP_KEYS,
    merge_formatting_step_defaults,
)
from ensembles.models import ArrangementVersion

LOGGER = getLogger("divisi_processing")

_LAYOUT_INFER_KEYS: tuple[str, ...] = LINE_BREAK_STEP_KEYS + (
    "apply_line_break_balancing",
    "apply_scrub_existing_line_breaks",
)


def _v2_formatting_params(formatting_params: dict) -> dict:
    """Map stored / API params onto part-formatter-v2 ``FormattingParams``."""
    params: dict = {
        "selected_style": formatting_params.get("selected_style") or "broadway",
        "staff_spacing_strategy": formatting_params.get("staff_spacing_strategy"),
        "staff_spacing_value": formatting_params.get("staff_spacing_value"),
        "optimize_for_page_turns": formatting_params.get(
            "optimize_for_page_turns", True
        ),
    }

    if "apply_mss_style" in formatting_params:
        params["apply_mss_style"] = bool(formatting_params["apply_mss_style"])

    if "apply_part_layout" in formatting_params:
        params["apply_part_layout"] = bool(formatting_params["apply_part_layout"])
    elif any(k in formatting_params for k in _LAYOUT_INFER_KEYS):
        params["apply_part_layout"] = any(
            formatting_params.get(k) for k in _LAYOUT_INFER_KEYS
        )

    return params


def _format_mscz_file(
    input_key: str, output_key: str, formatting_params: dict
) -> dict[str, str]:
    """Internal fn to format a mscz file. Reads in the file from the key, and writes it back"""

    tmp_in_path = tmp_out_path = None
    mpos_dir = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mscz") as tmp_in:
            tmp_in_path = tmp_in.name
            with default_storage.open(input_key, "rb") as stored_in:
                shutil.copyfileobj(stored_in, tmp_in)
                tmp_in.flush()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mscz") as tmp_out:
            tmp_out_path = tmp_out.name

        v2_params = _v2_formatting_params(formatting_params)
        apply_part_layout = v2_params.get("apply_part_layout", True)

        part_mpos: dict[str, str] = {}
        if apply_part_layout:
            mpos_dir = tempfile.mkdtemp(prefix="part_mpos_")
            part_mpos = export_all_mpos(
                tmp_in_path,
                mpos_dir,
                include_score=False,
            )
            if not part_mpos:
                return {
                    "status": "error",
                    "details": (
                        "No parts found to format. Open all parts in MuseScore "
                        "before uploading."
                    ),
                }
            LOGGER.info("Exported %d part .mpos file(s)", len(part_mpos))

        success = format_mscz(tmp_in_path, tmp_out_path, part_mpos, v2_params)

        if success is False:
            LOGGER.error("Error from mscz_formatter (part-formatter-v2)")
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
        if tmp_in_path and os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)
        if tmp_out_path and os.path.exists(tmp_out_path):
            os.remove(tmp_out_path)
        if mpos_dir and os.path.isdir(mpos_dir):
            shutil.rmtree(mpos_dir, ignore_errors=True)


@shared_task
def format_upload_session(session_id: int, **kwargs) -> dict[str, str]:
    """Takes in divisi.UploadSession obj id, and formats it"""

    session = UploadSession.objects.get(id=session_id)

    input_key = session.mscz_file_key
    output_key = session.output_file_key

    params: dict = {
        "selected_style": kwargs.get("selected_style"),
        "show_title": kwargs.get("show_title"),
        "show_number": kwargs.get("show_number"),
        "version_num": kwargs.get("version_num", "1.0.0"),
        "num_measures_per_line_score": kwargs.get("num_measures_per_line_score"),
        "num_measures_per_line_part": kwargs.get("num_measures_per_line_part"),
        "num_lines_per_page": kwargs.get("num_lines_per_page"),
        "staff_spacing_strategy": kwargs.get("staff_spacing_strategy"),
        "staff_spacing_value": kwargs.get("staff_spacing_value"),
        "optimize_for_page_turns": kwargs.get("optimize_for_page_turns", True),
    }

    return _format_mscz_file(input_key, output_key, params)


def _arrangement_version_format_params(
    version: ArrangementVersion,
    *,
    formatting_steps_override: dict[str, bool] | None = None,
) -> dict:
    params: dict = {
        "selected_style": version.arrangement.style,
        "show_title": version.ensemble_name,
        "show_number": version.arrangement.mvt_no,
        "work_title": version.arrangement.title,
        "version_num": f"v{version.version_label}",
        "num_measures_per_line_score": version.num_measures_per_line_score,
        "num_measures_per_line_part": version.num_measures_per_line_part,
        "num_lines_per_page": version.num_lines_per_page,
        "staff_spacing_strategy": version.staff_spacing_strategy,
        "staff_spacing_value": (
            str(version.staff_spacing_value)
            if version.staff_spacing_value is not None
            else None
        ),
        "optimize_for_page_turns": True,
    }

    if formatting_steps_override is not None:
        params.update(formatting_steps_override)
    else:
        stored = version.formatting_steps or {}
        if isinstance(stored, dict):
            for key in FORMATTING_STEP_KEYS:
                if key in stored:
                    params[key] = stored[key]

    merge_formatting_step_defaults(params)
    return params


@shared_task
def format_arrangement_version(
    version_id: int,
    *,
    formatting_steps_override: dict[str, bool] | None = None,
) -> dict[str, str]:
    version = ArrangementVersion.objects.get(id=version_id)
    params = _arrangement_version_format_params(
        version, formatting_steps_override=formatting_steps_override
    )
    return _format_mscz_file(version.mscz_file_key, version.output_file_key, params)
