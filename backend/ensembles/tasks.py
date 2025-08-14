from celery import shared_task

from divisi.part_formatter.processing import mscz_main
from divisi.part_formatter.export import export_mscz_to_pdf_score, export_score_and_parts_ms4
from .models import ArrangementVersion

@shared_task
def format_arrangement_version(version_id: int):
    version = ArrangementVersion.objects.get(id=version_id)
    arr = version.arrangement

    kwargs = {
        "input_path": version.mscz_file_path,
        "output_path": version.output_file_path,
        "style_name": arr.style,
        "versionNum": version.version_label,
    }

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
    #TODO: Add formatting options to uploadArrangementVersion page
    # if num_measure_per_line is not None:
    #     kwargs["num_measure_per_line"] = num_measure_per_line
    mscz_main(**kwargs)  #noqa -- no idea why this error is here but it shouldn't be

@shared_task
def export_arrangement_version(version_id: int, action:str = "score"):
    version = ArrangementVersion.objects.get(id=version_id)
    return export_score_and_parts_ms4(version.output_file_path, version.output_file_location)


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