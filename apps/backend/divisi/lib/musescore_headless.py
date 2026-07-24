import io
import zipfile
from pathlib import Path

import requests
from django.conf import settings


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


def export_all_mpos(
    input_path: str,
    output_dir: str,
    *,
    include_score: bool = False,
    timeout: int = 600,
) -> dict[str, str]:
    """
    Export .mpos files for a .mscz via musescore-headless ``/export-all-mpos``.

    Writes each ``{key}.mpos`` into ``output_dir`` and returns a map of
    target key → absolute path (same shape as part-formatter-v2's generate helper).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(input_path, "rb") as f:
        r = requests.post(
            f"http://{_get_host()}:1234/export-all-mpos",
            files={"file": f},
            data={"include_score": "true" if include_score else "false"},
            timeout=timeout,
        )

    r.raise_for_status()

    results: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(r.content), "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".mpos"):
                continue
            key = Path(name).stem
            dest = out / f"{key}.mpos"
            dest.write_bytes(zf.read(name))
            results[key] = str(dest.resolve())

    if not results:
        raise RuntimeError("musescore-headless returned no .mpos files")

    return results
