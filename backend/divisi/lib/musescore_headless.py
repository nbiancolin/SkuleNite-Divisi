from django.conf import settings
import requests


def _get_host() -> str:
    if settings.DEBUG:
        return "musescore-headless"
    else:
        return "localhost"


def render_mscz(input_path: str, output_path: str, timeout=120):
    """
    Helper function to interface with the headless docker container running MuseScore.
    Renders to the file type of the extension provided from output_path
    """

    output_format = output_path.split(".")[-1]

    with open(input_path, "rb") as f:
        r = requests.post(
            f"http://{_get_host()}:1234/render",
            files={"file": f},
            data={"out_format": output_format},
            timeout=timeout,
        )

    r.raise_for_status()

    with open(output_path, "wb") as out:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                out.write(chunk)


def render_all_parts_pdf(input_path: str) -> bytes:
    """Renders the score and all parts as individual PDFs, returns as zip archive."""
    with open(input_path, "rb") as f:
        r = requests.post(
            f"http://{_get_host()}:1234/render-all-parts-pdf",
            files={"file": f},
            timeout=300,
        )

    r.raise_for_status()
    
    return r.content