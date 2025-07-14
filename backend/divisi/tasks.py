from celery import shared_task
import subprocess
import os

from .part_formatter.processing import mscz_main

@shared_task
def part_formatter_mscz(file_path: str) -> str:
    mscz_main(file_path)
    return file_path[:-5] + "_processed.mscz"


@shared_task
def export_mscz_to_pdf(file_path):
    """
    export parts to "done" location where users can download their files aain
    """
    output_path = file_path[:-5] +".pdf"

    try:
        subprocess.run([
            "mscore4",  
            file_path,
            "-o", output_path
        ], check=True)
        return {"status": "success", "output": output_path}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}
