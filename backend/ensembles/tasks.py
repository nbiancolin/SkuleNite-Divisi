from celery import shared_task

from musescore_part_formatter import FormattingParams, format_mscz

from divisi.part_formatter.export import (
    export_score_and_parts_ms4_storage,
    export_mscz_to_musicxml,
)
from .models import ArrangementVersion, Diff, ExportFailureLog
from logging import getLogger
from django.core.files.storage import default_storage
from django.core.files import File
from django.core.files.base import ContentFile
import os
import shutil
import tempfile
import musicdiff
import traceback

logger = getLogger("export_tasks")

@shared_task
def format_arrangement_version(version_id: int):
    version = ArrangementVersion.objects.get(id=version_id)
    arr = version.arrangement

    kwargs: FormattingParams = {
        "selected_style": arr.style,
        "show_title": arr.ensemble_name,
        "show_number": arr.mvt_no,
        "num_measures_per_line_score": version.num_measures_per_line_score,
        "num_measures_per_line_part": version.num_measures_per_line_part,
        "num_lines_per_page": version.num_lines_per_page,
        "msv4_6_line_break_fix": False  #TODO Remove this
        #TODO: Allow for version num
        # "versionNum": version.version_label
    }

    #TODO: Allow for this
    # kwargs["arranger"] = arr.composer if arr.composer is not None else "COMPOSER"
    # if arr.composer is not None:
    #     kwargs["composer"] = arr.composer  # Look into the payload returned from this


    tmp_in_path = tmp_out_path = None
    try:
        # create temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mscz") as tmp_in:
            tmp_in_path = tmp_in.name
            # download mscz from storage into tmp_in
            with default_storage.open(version.mscz_file_key, "rb") as stored_in:
                shutil.copyfileobj(stored_in, tmp_in)
                tmp_in.flush()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            tmp_out_path = tmp_out.name

        logger.debug("Downloaded input mscz to %s (key=%s)", tmp_in_path, version.mscz_file_key)
        try:
            logger.debug("Calling format_mscz(%s -> %s) with kwargs=%r", tmp_in_path, tmp_out_path, kwargs)
            format_result = format_mscz(tmp_in_path, tmp_out_path, kwargs)
            logger.debug("format_mscz returned: %r", format_result)
        except Exception as fe:
            logger.exception("format_mscz failed")
            raise

        # verify output file was created
        if not tmp_out_path or not os.path.exists(tmp_out_path):
            logger.error("Formatter did not produce output file at %s", tmp_out_path)
            raise RuntimeError("Formatter did not produce output file")

        # upload generated file back to storage at session.output_file_key
        try:
            with open(tmp_out_path, "rb") as out_f:
                from django.core.files.base import ContentFile
                data = out_f.read()
                default_storage.save(version.output_file_key, ContentFile(data))
            logger.info("Saved formatted file to storage key=%s (size=%d)", version.output_file_key, len(data))
            # double-check
            if default_storage.exists(version.output_file_key):
                logger.debug("Verified storage contains %s", version.output_file_key)
            else:
                logger.warning("Storage does not report existence of %s after save", version.output_file_key)
        except Exception as se:
            logger.exception("Failed saving formatted file to storage key=%s", version.output_file_key)
            raise
    finally:
        # cleanup temp files if created
        if tmp_in_path and os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)
        if tmp_out_path and os.path.exists(tmp_out_path):
            os.remove(tmp_out_path)

@shared_task
def export_arrangement_version(version_id: int, action: str = "score"):
    """
    Export arrangement version using storage keys.

    Args:
        version_id: ID of the ArrangementVersion to export
        action: Export action type (currently unused but kept for compatibility)
    """
    try:
        version = ArrangementVersion.objects.get(id=version_id)
    except ArrangementVersion.DoesNotExist:
        logger.error(f"ArrangementVersion {version_id} does not exist")
        return {"status": "error", "details": f"Version {version_id} not found"}

    match action:
        case "score":
            try:
                # Use the processed file as input (or raw file if processed doesn't exist)
                input_key = version.output_file_key
                if not default_storage.exists(input_key):
                    logger.warning(
                        f"Processed file doesn't exist, using raw file: {version.mscz_file_key}"
                    )
                    input_key = version.mscz_file_key

                if not default_storage.exists(input_key):
                    logger.error(f"No input file found for version {version_id}")
                    version.error_on_export = True
                    version.is_processing = False
                    version.save()

                    ExportFailureLog.objects.create(arrangement_version=version, error_msg=f"No input file found for version {version_id}")

                    return {"status": "error", "details": "No input file found"}

                # Generate output prefix based on the version's storage structure
                # Extract the directory part from output_file_key
                output_dir = os.path.dirname(version.output_file_key) + "/"

                logger.info(f"Starting export for version {version_id}")
                result = export_score_and_parts_ms4_storage(input_key, output_dir)

                if result["status"] == "success":
                    logger.info(
                        f"Successfully exported {len(result['written'])} files for version {version_id}"
                    )
                    version.error_on_export = False
                else:
                    logger.error(
                        f"Export failed for version {version_id}: {result.get('details', 'Unknown error')}"
                    )
                    version.error_on_export = True
                    ExportFailureLog.objects.create(arrangement_version=version, error_msg=result["details"])

                version.is_processing = False
                version.save()

                return result

            except Exception as e:
                logger.error(
                    f"Unexpected error exporting version {version_id}: {str(e)}"
                )
                version.error_on_export = True
                version.is_processing = False
                version.save()

                ExportFailureLog.objects.create(arrangement_version=version, error_msg=str(e))

                return {"status": "error", "details": str(e)}
        case "mxl":
            try:
                input_key = version.output_file_key
                if not default_storage.exists(input_key):
                    logger.warning(
                        f"Couldn't Find Processed file for mxl export -- doesn't exist, using raw file: {version.mscz_file_key}"
                    )
                    input_key = version.mscz_file_key

                if not default_storage.exists(input_key):
                    logger.error(f"No input file found for version {version_id}")
                    version.error_on_export = True
                    version.is_processing = False
                    version.save()

                    ExportFailureLog.objects.create(arrangement_version=version, error_msg=f"No input file found for version {version_id}")

                    return {
                        "status": "error",
                        "details": "No input file found when exporting MXL",
                    }

                output_key = version.mxl_file_key
                if default_storage.exists(output_key):
                    logger.info(f"[EXPORT] - Mxl file already exists for version id {version_id}, returning.")
                    return {}
                return export_mscz_to_musicxml(input_key, output_key)

            except Exception as e:
                logger.error(
                    f"Unexpected error exporting version {version_id}: {str(e)}"
                )
                version.error_on_export = True
                version.is_processing = False
                version.save()

                ExportFailureLog.objects.create(arrangement_version=version, error_msg=str(e))

                return {"status": "error", "details": str(e)}


@shared_task
def prep_and_export_mscz(version_id):
    format_arrangement_version(version_id)
    res = export_arrangement_version(version_id)
    v = ArrangementVersion.objects.get(id=version_id)
    if not res["status"] == "success":
        v.error_on_export = True
    v.is_processing = False
    v.save(update_fields=["is_processing", "error_on_export"])

    return res


@shared_task
def compute_diff(diff_id: int):
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    
    diff = Diff.objects.get(id=diff_id)
    diff.status = "in_progress"
    diff.save()

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download inputs
            try:
                temp_input_1 = os.path.join(temp_dir, "input1.musicxml")
                with (
                    default_storage.open(diff.from_version.mxl_file_key, "rb") as src,
                    open(temp_input_1, "wb") as dst,
                ):
                    dst.write(src.read())
            except FileNotFoundError:
                export_arrangement_version(diff.from_version.id, action="mxl")
                temp_input_1 = os.path.join(temp_dir, "input1.musicxml")
                with (
                    default_storage.open(diff.from_version.mxl_file_key, "rb") as src,
                    open(temp_input_1, "wb") as dst,
                ):
                    dst.write(src.read())

            try:
                temp_input_2 = os.path.join(temp_dir, "input2.musicxml")
                with (
                    default_storage.open(diff.to_version.mxl_file_key, "rb") as src,
                    open(temp_input_2, "wb") as dst,
                ):
                    dst.write(src.read())
            except FileNotFoundError:
                export_arrangement_version(diff.to_version.id, action="mxl")
                temp_input_2 = os.path.join(temp_dir, "input2.musicxml")
                with (
                    default_storage.open(diff.to_version.mxl_file_key, "rb") as src,
                    open(temp_input_2, "wb") as dst,
                ):
                    dst.write(src.read())

            from music21 import environment

            #TODO: Fix this to use new musescore path
            us = environment.UserSettings()
            us['musicxmlPath'] = '/usr/local/bin/musescore'
            us['musescoreDirectPNGPath'] = '/usr/local/bin/musescore'
                
            # Run MusicDiff
            
            temp_output_1 = os.path.join(temp_dir, "output.pdf")
            temp_output_2 = os.path.join(temp_dir, "output2.pdf")
            musicdiff.diff(temp_input_1, temp_input_2, temp_output_1, temp_output_2, visualize_diffs=True,)

            # Output path in temp

            # Save to storage
            try:
                with open(temp_output_2, "rb") as f:
                    default_storage.save(diff.file_key, ContentFile(f.read()))
            except Exception:
                diff.status = "failed"
                diff.error_msg = "Scores are Identical -- no diff created"
                diff.save()
                return {"status": "error", "details": "Scores are identical, no diff created"}

            diff.status = "completed"
            diff.save()
            return {"status": "success", "output": diff.file_key}
        except Exception as e:
            logger.exception("MusicDiff error")
            diff.status = "failed"
            diff.error_msg = f"MusicDiff error: {traceback.format_exc()}"
            diff.save()
            return {"status": "error", "details": str(e)}
