from celery import shared_task
import subprocess
import os

from divisi.part_formatter.processing import mscz_main
from divisi.models import UploadSession


@shared_task
def part_formatter_mscz(
    uuid: int, style: str, show_title: str, show_number: str
) -> None:
    session = UploadSession.objects.get(id=uuid)

    mscz_main(
        input_path=session.mscz_file_path,
        output_path=session.output_file_path,
        style_name=style,
        show_title=show_title,
        show_number=show_number,
    )


@shared_task
def export_mscz_to_pdf(uuid: int):
    """
    export parts to "done" location where users can download their files aain
    """
    session = UploadSession.objects.get(id=uuid)
    output_path = session.output_file_path[:-5] + ".pdf"

    try:
        subprocess.run(["mscore4", session.output_file_path, "-o", output_path], check=True)
        return {"status": "success", "output": output_path}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}
