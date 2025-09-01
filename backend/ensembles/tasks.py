from celery import shared_task

from divisi.part_formatter.processing import mscz_main
from divisi.part_formatter.export import export_score_and_parts_ms4_storage, export_mscz_to_musicxml
from .models import ArrangementVersion
from logging import getLogger
from django.core.files.storage import default_storage
import os

logger = getLogger("export_tasks")

@shared_task
def format_arrangement_version(version_id: int):
    version = ArrangementVersion.objects.get(id=version_id)
    arr = version.arrangement

    kwargs = {
        "input_key": version.mscz_file_key,
        "output_key": version.output_file_key,
        "style_name": arr.style,
        "versionNum": version.version_label,
        "num_measures_per_line_score": version.num_measures_per_line_score,
        "num_measures_per_line_part": version.num_measures_per_line_part,
    }

    #TODO: Arranger info
    # if arranger is not None:
    #     kwargs["arranger"] = arranger
    # else:
    #     kwargs["arranger"] = "COMPOSER"
    kwargs["arranger"] = "COMPOSER"
    if arr.composer is not None:
        kwargs["compopser"] = arr.composer

    if arr.ensemble_name is not None:
        kwargs["movementTitle"] = arr.ensemble_name
    if arr.mvt_no is not None:
        kwargs["workNumber"] = arr.mvt_no
    mscz_main(**kwargs)  #noqa -- no idea why this error is here but it shouldn't be

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
                    logger.warning(f"Processed file doesn't exist, using raw file: {version.mscz_file_key}")
                    input_key = version.mscz_file_key
                
                if not default_storage.exists(input_key):
                    logger.error(f"No input file found for version {version_id}")
                    version.error_on_export = True
                    version.is_processing = False
                    version.save()
                    return {"status": "error", "details": "No input file found"}
                
                # Generate output prefix based on the version's storage structure
                # Extract the directory part from output_file_key
                output_dir = os.path.dirname(version.output_file_key) + "/"
                
                logger.info(f"Starting export for version {version_id}")
                result = export_score_and_parts_ms4_storage(input_key, output_dir)
                
                if result["status"] == "success":
                    logger.info(f"Successfully exported {len(result['written'])} files for version {version_id}")
                    version.error_on_export = False
                else:
                    logger.error(f"Export failed for version {version_id}: {result.get('details', 'Unknown error')}")
                    version.error_on_export = True
                
                version.is_processing = False
                version.save()
                
                return result
                
            except Exception as e:
                logger.error(f"Unexpected error exporting version {version_id}: {str(e)}")
                version.error_on_export = True
                version.is_processing = False
                version.save()
                return {"status": "error", "details": str(e)}
        case "mxl":
            logger.info("======================================================================================\nExporting MXL file")
            try:
                input_key = version.output_file_key
                if not default_storage.exists(input_key):
                    logger.warning(f"Couldn't Find Processed file for mxl export -- doesn't exist, using raw file: {version.mscz_file_key}")
                    input_key = version.mscz_file_key

                if not default_storage.exists(input_key):
                    logger.error(f"No input file found for version {version_id}")
                    version.error_on_export = True
                    version.is_processing = False
                    version.save()
                    return {"status": "error", "details": "No input file found when exporting MXL"}
                
                output_key = version.mxl_file_key
                return export_mscz_to_musicxml(input_key, output_key)
                
                

            except Exception as e:
                logger.error(f"Unexpected error exporting version {version_id}: {str(e)}")
                version.error_on_export = True
                version.is_processing = False
                version.save()
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