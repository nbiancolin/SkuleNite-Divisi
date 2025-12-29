from celery import shared_task

from divisi.tasks import format_arrangement_version
from divisi.tasks.export import (
    export_score_and_parts_ms4_storage,
    export_mscz_to_mp3,
)
from .models import ArrangementVersion, ExportFailureLog
from logging import getLogger
from django.core.files.storage import default_storage
import os

logger = getLogger("export_tasks")

#TODO[SC-XXX]: Move Musescore export tasks to a common "lib" location (divisi/lib/musescore_api.py or smth)

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

        case "mp3":
            try:
                input_key = version.mscz_file_key
                if not default_storage.exists(input_key):
                    logger.error(f"No input file found for version {version_id}")
                    version.audio_state = ArrangementVersion.AudioStatus.ERROR
                    version.save(update_fields=["audio_state"])

                    ExportFailureLog.objects.create(arrangement_version=version, error_msg=f"No input file found for version {version_id}")
                    return {
                        "status": "error",
                        "details": "No input file found when exporting MP3",
                    }

                output_key = version.audio_file_key
                if default_storage.exists(output_key):
                    logger.info(f"[EXPORT] - mp3 file already exists for version id {version_id}, returning.")
                    return {}

                version.audio_state = ArrangementVersion.AudioStatus.PROCESSING
                version.save(update_fields=["audio_state"])
                res = export_mscz_to_mp3(input_key, output_key)

                if res["status"] != "error":
                    version.audio_state = ArrangementVersion.AudioStatus.COMPLETE
                    version.save(update_fields=["audio_state"])
                    print("Status was Success")
                else:
                    version.audio_state = ArrangementVersion.AudioStatus.ERROR
                    version.save(update_fields=["audio_state"])
                    print("Status was not success")
                    ExportFailureLog.objects.create(arrangement_version=version, error_msg=res["details"])
                
                return res
                

            except Exception as e:
                logger.error(
                    f"Unexpected error exporting version {version_id}: {str(e)}"
                )
                version.audio_state = ArrangementVersion.AudioStatus.ERROR
                version.save(update_fields=["audio_state"])

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
