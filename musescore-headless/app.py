"""
FastAPI App to interface with the musescore docker container
"""
import asyncio
import subprocess
import tempfile
import zipfile
import io
import json
import base64
import re
import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, Form, HTTPException, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Exactly ONE job at a time
render_lock = asyncio.Semaphore(1)


@app.post("/render")
async def render(
    file: UploadFile,
    out_format: str = Form("pdf"),
):
    if out_format not in {"pdf", "mp3", "musicxml"}:
        raise HTTPException(400, "Unsupported out_format")

    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / file.filename
            dst = tmp / f"output.{out_format}"

            src.write_bytes(await file.read())

            try:
                subprocess.run(
                    ["musescore", src, "-o", dst],
                    check=True,
                    timeout=60,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except subprocess.TimeoutExpired:
                raise HTTPException(504, "MuseScore timed out")
            except subprocess.CalledProcessError as e:
                raise HTTPException(
                    500,
                    e.stderr.decode(errors="ignore"),
                )

            content = dst.read_bytes()
            media_types = {
                "pdf": "application/pdf",
                "png": "image/png",
                "midi": "audio/midi",
                "musicxml": "application/xml",
            }
            return Response(
                content=content,
                media_type=media_types.get(out_format, "application/octet-stream"),
                headers={"Content-Disposition": f'attachment; filename="{dst.name}"'},
            )


def _extract_json_from_text(text: str) -> str:
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


def _decode_pdf_from_b64(s: str) -> bytes | None:
    """Robustly decode potential single- or double-base64-encoded PDF payload.
    Returns bytes or None on failure."""
    if not s:
        return None
    # Remove whitespace/newlines
    candidate = "".join(s.split())
    try:
        first = base64.b64decode(candidate)
    except Exception:
        return None

    # If we already have a PDF
    if first.startswith(b"%PDF"):
        return first

    # If 'first' contains an inner PDF somewhere, extract it
    idx = first.find(b"%PDF")
    if idx != -1:
        return first[idx:]

    # If first is ASCII-looking and itself base64, try decode again (workaround for double-encoding bug)
    b64_alph_re = re.compile(r"^[A-Za-z0-9+/=\s]+$")
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


@app.post("/render-all-parts-pdf")
async def render_all_parts_pdf(file: UploadFile):
    """
    Renders the score and all parts as individual PDF files and returns them as a zip archive.
    The zip will contain:
    - The full score as a PDF (from scoreBin)
    - Each part as a separate PDF file (from partsBin)
    """
    logger.info(f"Starting render-all-parts-pdf for file: {file.filename}")
    
    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / file.filename
            src_stem = src.stem  # filename without extension
            
            # Write uploaded file to temp directory
            file_content = await file.read()
            logger.info(f"Received file of size: {len(file_content)} bytes")
            src.write_bytes(file_content)
            
            try:
                # Use --score-parts-pdf to get JSON output with all PDFs via stdout
                logger.info(f"Running MuseScore --score-parts-pdf on: {src}")
                proc = subprocess.run(
                    ["musescore", "--score-parts-pdf", src],
                    check=True,
                    capture_output=True,
                    timeout=300,
                )
                stdout_bytes = proc.stdout
                stdout_text = stdout_bytes.decode("utf-8", errors="replace")
                logger.info(f"MuseScore stdout length: {len(stdout_bytes)} bytes")
                logger.info(f"MuseScore stderr length: {len(proc.stderr)} bytes")
                
                if proc.stderr:
                    logger.info(f"MuseScore stderr (first 500 chars): {proc.stderr.decode('utf-8', errors='replace')[:500]}")
                
            except subprocess.TimeoutExpired:
                logger.error("MuseScore timed out")
                raise HTTPException(504, "MuseScore timed out")
            except subprocess.CalledProcessError as e:
                stderr_msg = e.stderr.decode(errors="ignore") if e.stderr else "Unknown error"
                logger.error(f"MuseScore error: {stderr_msg}")
                raise HTTPException(500, f"MuseScore error: {stderr_msg}")
            
            if not stdout_bytes:
                logger.error("No output produced from MuseScore")
                raise HTTPException(500, "No output produced from MuseScore")
            
            # Extract and parse JSON from stdout
            try:
                json_text = _extract_json_from_text(stdout_text)
                logger.info(f"Extracted JSON length: {len(json_text)} chars")
                data = json.loads(json_text)
                logger.info(f"Parsed JSON keys: {list(data.keys())}")
            except (ValueError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"JSON text that failed: {json_text[:2000] if 'json_text' in locals() else 'N/A'}")
                raise HTTPException(500, f"Failed to parse MuseScore JSON output: {e}")
            
            # Collect PDFs to add to zip
            pdf_files = []
            
            # 1) Add the full score PDF (scoreBin)
            if "scoreBin" in data:
                logger.info("Found scoreBin in data")
                score_b64 = data["scoreBin"]
                logger.info(f"scoreBin type: {type(score_b64)}, length: {len(str(score_b64)) if score_b64 else 0}")
                pdf_bytes = _decode_pdf_from_b64(score_b64)
                if pdf_bytes:
                    logger.info(f"Decoded score PDF: {len(pdf_bytes)} bytes")
                    pdf_files.append(("Score.pdf", pdf_bytes))
                else:
                    logger.warning("Failed to decode scoreBin")
            else:
                logger.warning("scoreBin not found in data")
            
            # 2) Add individual parts (partsBin)
            logger.info("Looking for partsBin in data...")
            parts_list = data.get("partsBin", [])
            parts_names = data.get("parts", [])
            logger.info(f"partsBin type: {type(parts_list)}, length: {len(parts_list) if isinstance(parts_list, list) else 'N/A'}")
            logger.info(f"parts (names) type: {type(parts_names)}, length: {len(parts_names) if isinstance(parts_names, list) else 'N/A'}")
            
            if not isinstance(parts_list, list):
                logger.warning(f"partsBin is not a list, it's a {type(parts_list)}. Converting...")
                # Handle case where partsBin might be a single object or different structure
                parts_list = [parts_list] if parts_list else []
            
            if not isinstance(parts_names, list):
                parts_names = []
            
            # MuseScore returns partsBin as a list of base64 strings, and parts as a list of names
            # They should be in the same order, so we zip them together
            logger.info("Processing %d parts", len(parts_list))
            
            for idx, b64 in enumerate(parts_list):
                # Get the corresponding part name, or use a default
                if idx < len(parts_names):
                    name = parts_names[idx]
                else:
                    name = f"Part {idx + 1}"
                
                logger.info(f"Processing part {idx + 1}/{len(parts_list)}: name={name}, b64 type={type(b64)}, b64 length={len(str(b64)) if b64 else 0}")
                
                try:
                    if not b64:
                        logger.warning(f"Part {idx} ({name}) has no base64 data, skipping")
                        continue
                    
                    if not isinstance(b64, str):
                        logger.warning(f"Part {idx} ({name}) base64 is not a string (type: {type(b64)}), skipping")
                        continue
                    
                    pdf_bytes = _decode_pdf_from_b64(b64)
                    if not pdf_bytes:
                        logger.warning(f"Failed to decode PDF for part {idx} ({name})")
                        continue
                    
                    logger.info(f"Successfully decoded PDF for part {idx} ({name}): {len(pdf_bytes)} bytes")
                    
                    # Sanitize part name for filename
                    safe_name = (
                        "".join(c for c in str(name) if c not in r'\/:*?"<>|').strip()
                        or f"Part {idx + 1}"
                    )
                    pdf_files.append((f"{safe_name}.pdf", pdf_bytes))
                    logger.info(f"Added part to zip: {safe_name}.pdf")
                except Exception as e:
                    logger.exception(f"Exception processing part {idx} ({name}): {e}")
                    # Skip parts that fail to decode
                    continue
            
            logger.info(f"Total PDF files to add to zip: {len(pdf_files)}")
            logger.info(f"PDF file names: {[name for name, _ in pdf_files]}")
            
            if not pdf_files:
                logger.error("No PDF files were generated or decoded")
                raise HTTPException(500, "No PDF files were generated or decoded")
            
            # Create a zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for name, pdf_bytes in pdf_files:
                    zip_file.writestr(name, pdf_bytes)
                    logger.info(f"Added {name} ({len(pdf_bytes)} bytes) to zip")
            
            zip_buffer.seek(0)
            zip_size = len(zip_buffer.getvalue())
            logger.info(f"Created zip file: {zip_size} bytes total")
            
            # Return the zip file
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{src_stem}_score_and_parts.zip"'
                },
            )


@app.get("/health")
def health():
    return {"status": "ok"}
