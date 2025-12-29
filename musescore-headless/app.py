"""
FastAPI App to interface with the musescore docker container
"""
import asyncio
import subprocess
import tempfile
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


@app.get("/health")
def health():
    return {"status": "ok"}
