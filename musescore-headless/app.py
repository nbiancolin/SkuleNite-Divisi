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
from pathlib import Path

from fastapi import FastAPI, UploadFile, Form, HTTPException, Response
from fastapi.responses import PlainTextResponse

app = FastAPI()

# Exactly ONE job at a time
render_lock = asyncio.Semaphore(1)


@app.post("/render-score-parts")
async def render_score_parts(file: UploadFile):
    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / file.filename

            src.write_bytes(await file.read())

            try:
                proc = subprocess.run(
                    ["musescore", "--score-parts-pdf", src],
                    check=True,
                    capture_output=True,
                    timeout=300,
                )
                stdout_bytes = proc.stdout
                stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            
            except subprocess.TimeoutExpired:
                raise HTTPException(504, "MuseScore timed out")
            except subprocess.CalledProcessError as e:
                raise HTTPException(
                    500,
                    e.stderr.decode(errors="ignore"),
                )

            if not stdout_bytes:
                raise HTTPException(500, "No output produced")

            return PlainTextResponse(stdout_text, media_type="text/plain")



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
    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / file.filename
            src_stem = src.stem  # filename without extension
            
            # Write uploaded file to temp directory
            src.write_bytes(await file.read())
            
            try:
                # Use --score-parts-pdf to get JSON output with all PDFs via stdout
                proc = subprocess.run(
                    ["musescore", "--score-parts-pdf", src],
                    check=True,
                    capture_output=True,
                    timeout=300,
                )
                stdout_bytes = proc.stdout
                stdout_text = stdout_bytes.decode("utf-8", errors="replace")
                
            except subprocess.TimeoutExpired:
                raise HTTPException(504, "MuseScore timed out")
            except subprocess.CalledProcessError as e:
                stderr_msg = e.stderr.decode(errors="ignore") if e.stderr else "Unknown error"
                raise HTTPException(500, f"MuseScore error: {stderr_msg}")
            
            if not stdout_bytes:
                raise HTTPException(500, "No output produced from MuseScore")
            
            # Extract and parse JSON from stdout
            try:
                json_text = _extract_json_from_text(stdout_text)
                data = json.loads(json_text)
            except (ValueError, json.JSONDecodeError) as e:
                raise HTTPException(500, f"Failed to parse MuseScore JSON output: {e}")
            
            # Collect PDFs to add to zip
            pdf_files = []
            
            # 1) Add the full score PDF (scoreBin)
            if "scoreBin" in data:
                pdf_bytes = _decode_pdf_from_b64(data["scoreBin"])
                if pdf_bytes:
                    pdf_files.append(("Score.pdf", pdf_bytes))
            
            # 2) Add individual parts (partsBin)
            parts_list = data.get("partsBin", [])
            if not isinstance(parts_list, list):
                # Handle case where partsBin might be a single object or different structure
                parts_list = [parts_list] if parts_list else []
            
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
                        continue
                    
                    pdf_bytes = _decode_pdf_from_b64(b64)
                    if not pdf_bytes:
                        continue
                    
                    # Sanitize part name for filename
                    safe_name = (
                        "".join(c for c in str(name) if c not in r'\/:*?"<>|').strip()
                        or "Part"
                    )
                    pdf_files.append((f"{safe_name}.pdf", pdf_bytes))
                except Exception:
                    # Skip parts that fail to decode
                    continue
            
            if not pdf_files:
                raise HTTPException(500, "No PDF files were generated or decoded")
            
            # Create a zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for name, pdf_bytes in pdf_files:
                    zip_file.writestr(name, pdf_bytes)
            
            zip_buffer.seek(0)
            
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
