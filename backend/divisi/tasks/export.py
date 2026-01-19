import tempfile
import os
from celery import shared_task
import subprocess

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from divisi.models import UploadSession

from divisi.lib import render_mscz, render_all_parts_pdf
from ensembles.models import ArrangementVersion, PartAsset, PartName

import zipfile
import io


from logging import getLogger

LOGGER = getLogger("divisi_export")

def _export_mscz_to_pdf_score(input_file_path: str, output_path: str):
    """Uses Musescore to render the provided musescore file and output a pdf of the score"""
    assert output_path.endswith(".pdf"), (
        "ERR: export_mscz_to_pdf_score was called with a non-pdf output file"
    )
    render_mscz(input_file_path, output_path)
    return {"status": "success", "output": output_path}


def export_mscz_to_mp3(input_key, output_key):
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download input
            temp_input = os.path.join(temp_dir, "input.mscz")
            with (
                default_storage.open(input_key, "rb") as src,
                open(temp_input, "wb") as dst,
            ):
                dst.write(src.read())

            # Output path in temp
            temp_output = os.path.join(temp_dir, "output.mp3")

            # Run MuseScore
            render_mscz(temp_input, temp_output)

            # Save to storage
            with open(temp_output, "rb") as f:
                default_storage.save(output_key, ContentFile(f.read()))

            return {"status": "success", "output": output_key}
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            LOGGER.error("MuseScore export failed: %s", stderr)
            return {"status": "error", "details": stderr}
        except Exception as e:
            LOGGER.exception("Mp3 export error")
            return {"status": "error", "details": str(e)}


def export_all_parts_with_tracking(input_key, output_prefix, arrangement_version_id=None):
    """
    Export score and all parts using the new render-all-parts-pdf endpoint,
    extract individual PDFs from zip, save them, and create Part records.
    
    Args:
        input_key (str): storage key for the input .mscz file
        output_prefix (str): storage path prefix to save outputs (should end with '/')
        arrangement_version_id (int, optional): ID of ArrangementVersion to create Part records for
    
    Returns:
        dict: {"status": "success"|"error", "written": [saved_keys], "parts_created": int, "details": "..."}
    """
    
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download input
        try:
            temp_input = os.path.join(temp_dir, "input.mscz")
            with (
                default_storage.open(input_key, "rb") as src,
                open(temp_input, "wb") as dst,
            ):
                dst.write(src.read())
        except Exception as e:
            LOGGER.exception("Failed to download input file from storage")
            return {"status": "error", "details": f"Download error: {e}"}
        
        # Call the new render-all-parts-pdf endpoint
        try:
            zip_bytes = render_all_parts_pdf(temp_input)
        except Exception as e:
            LOGGER.exception("Failed to call render-all-parts-pdf endpoint")
            return {"status": "error", "details": f"MuseScore API error: {e}"}
        
        # Extract PDFs from zip
        written = []
        parts_created = 0
        stem = os.path.splitext(os.path.basename(input_key))[0]
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zip_file:
                for file_info in zip_file.filelist:
                    if file_info.filename.endswith(".pdf"):
                        # Extract PDF from zip
                        pdf_bytes = zip_file.read(file_info.filename)
                        
                        # Determine if it's the score or a part
                        is_score = file_info.filename.lower() == "score.pdf"
                        #TODO: Here, change part_name to map to a part_name objetct
                        part_name = file_info.filename.replace(".pdf", "")
                        
                        # Generate storage key
                        if is_score:
                            key = f"{output_prefix}{stem}.pdf"
                        else:
                            # Sanitize part name for filename
                            safe_name = "".join(c for c in part_name if c not in r'\/:*?"<>|').strip()
                            key = f"{output_prefix}{stem} - {safe_name}.pdf"
                        
                        # Save PDF to storage
                        default_storage.save(key, ContentFile(pdf_bytes))
                        written.append(key)
                        LOGGER.info("Saved PDF: %s", key)
                        
                        # Create Part record if arrangement_version_id is provided
                        if arrangement_version_id:
                            try:
                                version = ArrangementVersion.objects.get(id=arrangement_version_id)
                                name_obj = PartName.objects.update_or_create(
                                    ensemble=version.ensemble,
                                    display_name=part_name
                                )
                                PartAsset.objects.update_or_create(
                                    arrangement_version=version,
                                    name=name_obj,
                                    defaults={
                                        "file_key": key,
                                        "is_score": is_score,
                                    }
                                )
                                parts_created += 1
                                LOGGER.info("Created Part record: %s for version %d", part_name, arrangement_version_id)
                            except ArrangementVersion.DoesNotExist:
                                LOGGER.warning("ArrangementVersion %d does not exist, skipping Part record", arrangement_version_id)
                            except Exception as e:
                                LOGGER.exception("Failed to create Part record for %s", part_name)
        
        except zipfile.BadZipFile:
            #TODO: Create exportFailureLogs here / INvestigate that if it fails here, an export failure is created
            return {"status": "error", "details": "Invalid zip file received from MuseScore"}
        except Exception as e:
            LOGGER.exception("Failed to extract PDFs from zip")
            return {"status": "error", "details": f"Zip extraction error: {e}"}
        
        if not written:
            return {
                "status": "error",
                "details": "MuseScore ran but no PDFs were extracted from zip.",
            }
        
        return {
            "status": "success",
            "written": written,
            "parts_created": parts_created,
        }



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
        res = _export_mscz_to_pdf_score(tmp_in_path, tmp_out_path)
        if res["status"] == "error":
            return res

        # Upload generated PDF to storage
        with open(tmp_out_path, "rb") as pdf_file:
            default_storage.save(output_key, pdf_file)

    # Clean up temp files
    os.remove(tmp_in_path)
    os.remove(tmp_out_path)

    return {"status": "success", "output": default_storage.url(output_key)}
