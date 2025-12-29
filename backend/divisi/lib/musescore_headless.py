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


def render_score_parts(input_path: str) -> bytes:
    """Renders individual parts from a score using MuseScore's --parts option."""
    with open(input_path, "rb") as f:
        r = requests.post(
            f"http://{_get_host()}:1234/render-score-parts",
            files={"file": f},
            timeout=300,
        )

    #Raising an exception here is ok... its caught up above and an error obj is created
    r.raise_for_status() 

    return r.content
