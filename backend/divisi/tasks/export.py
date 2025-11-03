import tempfile
import os
import re
from celery import shared_task
import subprocess
import json, base64, subprocess

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from divisi.models import UploadSession


from logging import getLogger

LOGGER = getLogger("divisi_export")

def _export_mscz_to_pdf_score(input_file_path: str, output_path: str):
    """Uses Musescore to render the provided musescore file and output a pdf of the score"""
    assert output_path.endswith(".pdf"), (
        "ERR: export_mscz_to_pdf_score was called with a non-pdf output file"
    )
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        subprocess.run(["musescore", input_file_path, "-o", output_path], check=True)
        return {"status": "success", "output": output_path}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}


def export_mscz_to_musicxml(input_key, output_key):
    """
    Export a MusicXML file from MuseScore and save it to Django storage.

    Args:
        input_key (str): storage key for the input .mscz file
        output_key (str): storage key to save the resulting .musicxml
    """
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

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
            temp_output = os.path.join(temp_dir, "output.musicxml")

            # Run MuseScore
            subprocess.run(
                ["musescore", temp_input, "-o", temp_output],
                check=True,
                capture_output=True,
                env=env,
            )

            # Save to storage
            with open(temp_output, "rb") as f:
                default_storage.save(output_key, ContentFile(f.read()))

            return {"status": "success", "output": output_key}
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            LOGGER.error("MuseScore export failed: %s", stderr)
            return {"status": "error", "details": stderr}
        except Exception as e:
            LOGGER.exception("MusicXML export error")
            return {"status": "error", "details": str(e)}


def export_score_and_parts_ms4_storage_scoreparts(
    input_key,
    output_prefix,
):
    """
    Export with MuseScore's --score-parts-pdf flag and save resulting PDFs to Django storage.

    Args:
        input_key (str): storage key for the input .mscz file
        output_prefix (str): storage path prefix to save outputs (should end with '/')

    Returns:
        dict: {"status": "success"|"error", "written": [saved_keys], "details": "..."}
    """
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    def _extract_json_from_text(text):
        """Find the first complete JSON object in text by balancing braces."""
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in MuseScore output")
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        raise ValueError("Incomplete JSON object in MuseScore output")

    b64_alph_re = re.compile(r"^[A-Za-z0-9+/=\s]+$")

    def _decode_pdf_from_b64(s):
        """Robustly decode potential single- or double-base64-encoded PDF payload.
        Returns bytes or None on failure."""
        if not s:
            return None
        # Remove whitespace/newlines
        candidate = "".join(s.split())
        try:
            first = base64.b64decode(candidate)
        except Exception as e:
            LOGGER.warning("base64 decode (first) failed: %s", e)
            return None

        # If we already have a PDF
        if first.startswith(b"%PDF"):
            return first

        # If 'first' contains an inner PDF somewhere, extract it
        idx = first.find(b"%PDF")
        if idx != -1:
            return first[idx:]

        # If first is ASCII-looking and itself base64, try decode again (workaround for double-encoding bug)
        try:
            first_str = first.decode("ascii", errors="ignore").strip()
            clean = "".join(first_str.split())
            if b64_alph_re.match(clean):
                second = base64.b64decode(clean)
                if second.startswith(b"%PDF"):
                    return second
                # if second contains PDF inside, extract it
                idx2 = second.find(b"%PDF")
                if idx2 != -1:
                    return second[idx2:]
        except Exception:
            pass

        # Last resort: return first (even if not perfect)
        return first

    with tempfile.TemporaryDirectory() as temp_dir:
        # download input
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

        # run MuseScore with --score-parts-pdf
        try:
            proc = subprocess.run(
                ["musescore", "--score-parts-pdf", temp_input],
                check=True,
                capture_output=True,
                env=env,
                timeout=300,
            )
            stdout_bytes = proc.stdout or b""
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            json_text = _extract_json_from_text(stdout_text)
            data = json.loads(json_text)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            LOGGER.error("MuseScore CLI failed: %s", stderr)
            return {"status": "error", "details": stderr}
        except Exception as e:
            LOGGER.exception("Failed to run MuseScore --score-parts-pdf or parse JSON")
            return {"status": "error", "details": f"MuseScore/JSON error: {e}"}

        # now decode and save PDFs
        written = []
        stem = os.path.splitext(os.path.basename(input_key))[0]

        # 1) score-only (conductor) -> common key: "scoreBin"
        if "scoreBin" in data:
            pdf_bytes = _decode_pdf_from_b64(data["scoreBin"])
            if pdf_bytes:
                key = f"{output_prefix}{stem}.pdf"
                try:
                    default_storage.save(key, ContentFile(pdf_bytes))
                    written.append(key)
                    LOGGER.info("Saved score-only: %s", key)
                except Exception as e:
                    LOGGER.exception("Failed to save score-only PDF")

        # 2) combined score + parts: check a few possible keys (handle double-encoding bug)
        for combined_key in ("scoreFullBin", "fullScoreBin", "fullScore", "scoreFull"):
            if combined_key in data:
                pdf_bytes = _decode_pdf_from_b64(data[combined_key])
                if pdf_bytes:
                    combined_key_name = f"{output_prefix}{stem} - Score+Parts.pdf"
                    try:
                        default_storage.save(combined_key_name, ContentFile(pdf_bytes))
                        written.append(combined_key_name)
                        LOGGER.info("Saved combined score+parts: %s", combined_key_name)
                    except Exception:
                        LOGGER.exception("Failed to save combined PDF")
                break

        # 3) individual parts: either under "parts" or "partsBin"
        parts_list = []
        if "parts" in data and isinstance(data["parts"], list):
            parts_list = data["parts"]
        elif "partsBin" in data and isinstance(data["partsBin"], list):
            parts_list = data["partsBin"]

        for part in parts_list:
            try:
                if isinstance(part, dict):
                    name = (
                        part.get("name")
                        or part.get("partName")
                        or part.get("part")
                        or "Part"
                    )
                    b64 = (
                        part.get("bin")
                        or part.get("pdf")
                        or part.get("pdfBin")
                        or part.get("partsBin")
                    )
                elif isinstance(part, (list, tuple)) and len(part) >= 2:
                    name = part[0]
                    b64 = part[1]
                else:
                    LOGGER.warning("Unrecognized part format, skipping: %r", part)
                    continue

                pdf_bytes = _decode_pdf_from_b64(b64)
                if not pdf_bytes:
                    LOGGER.warning("No PDF bytes decoded for part %s", name)
                    continue

                safe_name = (
                    "".join(c for c in str(name) if c not in r'\/:*?"<>|').strip()
                    or "Part"
                )
                key = f"{output_prefix}{stem} - {safe_name}.pdf"
                default_storage.save(key, ContentFile(pdf_bytes))
                written.append(key)
                LOGGER.info("Saved part: %s", key)
            except Exception:
                LOGGER.exception("Failed to save a part")

        if not written:
            return {
                "status": "error",
                "details": "MuseScore ran but no PDFs were produced or decoded.",
            }

        return {"status": "success", "written": written}


def export_score_and_parts_ms4_storage(input_key, output_prefix):
    return export_score_and_parts_ms4_storage_scoreparts(input_key, output_prefix)





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
