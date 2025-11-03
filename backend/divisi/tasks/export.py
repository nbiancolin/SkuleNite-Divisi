import tempfile
import os

from celery import shared_task

from django.core.files.storage import default_storage


from divisi.models import UploadSession

from logging import getLogger

LOGGER = getLogger("divisi_export")

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
