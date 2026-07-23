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
import os
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, UploadFile, Form, HTTPException, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Exactly ONE job at a time
render_lock = asyncio.Semaphore(1)

# Runtime env setup
RUNTIME_DIR = Path("/tmp/runtime-root")
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.chmod(0o700)

MUSESCORE_ENV = {
    **os.environ,
    "QT_QPA_PLATFORM": "offscreen",
    "XDG_RUNTIME_DIR": str(RUNTIME_DIR),
}


@app.on_event("startup")
async def startup_event():
    logger.info("========================================")
    logger.info("MuseScore Container Startup Diagnostics")
    logger.info("========================================")

    logger.info(f"PATH={os.environ.get('PATH')}")
    logger.info(f"DISPLAY={os.environ.get('DISPLAY')}")
    logger.info(f"QT_QPA_PLATFORM={MUSESCORE_ENV.get('QT_QPA_PLATFORM')}")
    logger.info(f"XDG_RUNTIME_DIR={MUSESCORE_ENV.get('XDG_RUNTIME_DIR')}")

    try:
        which_output = subprocess.check_output(
            ["which", "musescore"],
            text=True,
        ).strip()
        logger.info(f"which musescore => {which_output}")
    except Exception:
        logger.exception("Failed to locate musescore binary")

    try:
        version_output = subprocess.check_output(
            ["musescore", "--version"],
            env=MUSESCORE_ENV,
            text=True,
            stderr=subprocess.STDOUT,
        )
        logger.info(f"MuseScore version:\n{version_output}")
    except Exception:
        logger.exception("Failed to get MuseScore version")

    try:
        fc_output = subprocess.check_output(
            ["fc-list"],
            text=True,
            stderr=subprocess.STDOUT,
        )
        logger.info(f"Fontconfig sample:\n{fc_output[:2000]}")
    except Exception:
        logger.exception("Failed to inspect fonts")

    logger.info("Startup diagnostics complete")


def run_musescore(cmd: list[str], timeout: int = 60):
    logger.info("========================================")
    logger.info("Running MuseScore command")
    logger.info("========================================")

    logger.info(f"Command: {' '.join(map(str, cmd))}")
    logger.info(f"Environment:")
    logger.info(f"  QT_QPA_PLATFORM={MUSESCORE_ENV.get('QT_QPA_PLATFORM')}")
    logger.info(f"  XDG_RUNTIME_DIR={MUSESCORE_ENV.get('XDG_RUNTIME_DIR')}")

    start = time.time()

    proc = subprocess.run(
        [str(c) for c in cmd],
        env=MUSESCORE_ENV,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    elapsed = time.time() - start

    logger.info(f"Return code: {proc.returncode}")
    logger.info(f"Elapsed: {elapsed:.2f}s")

    if proc.stdout:
        logger.info("========== STDOUT ==========")
        logger.info(proc.stdout[:10000])

    if proc.stderr:
        logger.error("========== STDERR ==========")
        logger.error(proc.stderr[:10000])

    return proc


@app.post("/render")
async def render(
    file: UploadFile,
    out_format: str = Form("pdf"),
):
    if out_format not in {"pdf", "mp3", "musicxml"}:
        raise HTTPException(400, "Unsupported out_format")

    logger.info("========================================")
    logger.info("Starting /render")
    logger.info("========================================")
    logger.info(f"Filename: {file.filename}")
    logger.info(f"Requested output format: {out_format}")

    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            src = tmp / file.filename
            dst = tmp / f"output.{out_format}"

            file_content = await file.read()

            logger.info(f"Uploaded file size: {len(file_content)} bytes")

            src.write_bytes(file_content)

            logger.info(f"Source file written: {src}")
            logger.info(f"Source exists: {src.exists()}")

            cmd = ["musescore", str(src), "-o", str(dst)]

            try:
                proc = run_musescore(cmd, timeout=60)

            except subprocess.TimeoutExpired:
                logger.exception("MuseScore timed out")
                raise HTTPException(504, "MuseScore timed out")

            logger.info(f"Destination exists: {dst.exists()}")

            if dst.exists():
                logger.info(f"Output size: {dst.stat().st_size} bytes")

            if proc.returncode != 0:
                raise HTTPException(
                    500,
                    f"MuseScore failed.\n\nSTDERR:\n{proc.stderr}",
                )

            if not dst.exists():
                raise HTTPException(
                    500,
                    "MuseScore completed but output file was not created",
                )

            content = dst.read_bytes()

            media_types = {
                "pdf": "application/pdf",
                "png": "image/png",
                "midi": "audio/midi",
                "musicxml": "application/xml",
            }

            logger.info("Render completed successfully")

            return Response(
                content=content,
                media_type=media_types.get(
                    out_format,
                    "application/octet-stream",
                ),
                headers={"Content-Disposition": (f'attachment; filename="{dst.name}"')},
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
    """
    Robustly decode potential single- or double-base64-encoded PDF payload.
    Returns bytes or None on failure.
    """

    if not s:
        return None

    candidate = "".join(s.split())

    try:
        first = base64.b64decode(candidate)
    except Exception:
        logger.exception("Failed first base64 decode")
        return None

    if first.startswith(b"%PDF"):
        return first

    idx = first.find(b"%PDF")

    if idx != -1:
        return first[idx:]

    b64_alph_re = re.compile(r"^[A-Za-z0-9+/=\s]+$")

    try:
        first_str = first.decode("ascii", errors="ignore").strip()
        clean = "".join(first_str.split())

        if b64_alph_re.match(clean):
            second = base64.b64decode(clean)

            if second.startswith(b"%PDF"):
                return second

            idx2 = second.find(b"%PDF")

            if idx2 != -1:
                return second[idx2:]

    except Exception:
        logger.exception("Failed second base64 decode")

    return first


@app.post("/render-all-parts-pdf")
async def render_all_parts_pdf(file: UploadFile):
    """
    Renders the score and all parts as individual PDF files
    and returns them as a zip archive.
    """

    logger.info("========================================")
    logger.info("Starting /render-all-parts-pdf")
    logger.info("========================================")
    logger.info(f"Filename: {file.filename}")

    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            src = tmp / file.filename
            src_stem = src.stem

            file_content = await file.read()

            logger.info(f"Received file size: {len(file_content)} bytes")

            src.write_bytes(file_content)

            logger.info(f"Source written to: {src}")
            logger.info(f"Source exists: {src.exists()}")

            cmd = [
                "musescore",
                "--score-parts-pdf",
                str(src),
            ]

            try:
                proc = run_musescore(cmd, timeout=300)

            except subprocess.TimeoutExpired:
                logger.exception("MuseScore timed out")
                raise HTTPException(504, "MuseScore timed out")

            if proc.returncode != 0:
                raise HTTPException(
                    500,
                    f"MuseScore failed.\n\nSTDERR:\n{proc.stderr}",
                )

            stdout_text = proc.stdout

            if not stdout_text:
                logger.error("MuseScore produced no stdout")
                raise HTTPException(
                    500,
                    "MuseScore produced no output",
                )

            try:
                json_text = _extract_json_from_text(stdout_text)

                logger.info(f"Extracted JSON length: {len(json_text)} chars")

                data = json.loads(json_text)

                logger.info(f"Parsed JSON keys: {list(data.keys())}")

            except Exception:
                logger.exception("Failed parsing MuseScore JSON")
                raise HTTPException(
                    500,
                    "Failed to parse MuseScore JSON output",
                )

            pdf_files = []

            # Score PDF
            if "scoreBin" in data:
                logger.info("Found scoreBin")

                score_b64 = data["scoreBin"]

                pdf_bytes = _decode_pdf_from_b64(score_b64)

                if pdf_bytes:
                    logger.info(f"Decoded score PDF: {len(pdf_bytes)} bytes")
                    pdf_files.append(("Score.pdf", pdf_bytes))
                else:
                    logger.warning("Failed to decode scoreBin")

            else:
                logger.warning("scoreBin missing from output")

            # Parts
            parts_list = data.get("partsBin", [])
            parts_names = data.get("parts", [])

            logger.info(f"partsBin count: {len(parts_list) if isinstance(parts_list, list) else 'invalid'}")

            logger.info(f"parts count: {len(parts_names) if isinstance(parts_names, list) else 'invalid'}")

            if not isinstance(parts_list, list):
                logger.warning(f"partsBin was not a list: {type(parts_list)}")
                parts_list = [parts_list] if parts_list else []

            if not isinstance(parts_names, list):
                parts_names = []

            for idx, b64 in enumerate(parts_list):
                name = parts_names[idx] if idx < len(parts_names) else f"Part {idx + 1}"

                logger.info(f"Processing part {idx + 1}/{len(parts_list)}: {name}")

                try:
                    if not b64:
                        logger.warning(f"No base64 for {name}")
                        continue

                    if not isinstance(b64, str):
                        logger.warning(f"Invalid base64 type for {name}: {type(b64)}")
                        continue

                    pdf_bytes = _decode_pdf_from_b64(b64)

                    if not pdf_bytes:
                        logger.warning(f"Failed to decode PDF for {name}")
                        continue

                    logger.info(f"Decoded {name}: {len(pdf_bytes)} bytes")

                    safe_name = "".join(c for c in str(name) if c not in r'\/:*?"<>|').strip() or f"Part {idx + 1}"

                    filename = f"{safe_name}.pdf"

                    pdf_files.append((filename, pdf_bytes))

                    logger.info(f"Queued {filename}")

                except Exception:
                    logger.exception(f"Failed processing part {name}")

            logger.info(f"Total PDFs generated: {len(pdf_files)}")

            if not pdf_files:
                raise HTTPException(
                    500,
                    "No PDFs were successfully generated",
                )

            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(
                zip_buffer,
                "w",
                zipfile.ZIP_DEFLATED,
            ) as zip_file:
                for name, pdf_bytes in pdf_files:
                    zip_file.writestr(name, pdf_bytes)

                    logger.info(f"Added to zip: {name} ({len(pdf_bytes)} bytes)")

            zip_buffer.seek(0)

            zip_size = len(zip_buffer.getvalue())

            logger.info(f"Final zip size: {zip_size} bytes")

            logger.info("render-all-parts-pdf completed successfully")

            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": (f'attachment; filename="{src_stem}_score_and_parts.zip"')},
            )


@dataclass(frozen=True)
class _MposExportTarget:
    """One MSCX inside an unpacked MSCZ, plus its style file if present."""

    key: str
    mscx_path: Path
    style_path: Path | None
    is_excerpt: bool


def _score_style_path(work_dir: Path) -> Path | None:
    preferred = work_dir / "score_style.mss"
    if preferred.is_file():
        return preferred
    mss_files = sorted(work_dir.glob("*.mss"))
    return mss_files[0] if mss_files else None


def _list_mpos_export_targets(work_dir: Path) -> list[_MposExportTarget]:
    """Discover the root score and every ``Excerpts/<key>/*.mscx`` target."""
    targets: list[_MposExportTarget] = []

    root_mscx = sorted(p for p in work_dir.glob("*.mscx") if p.is_file())
    if not root_mscx:
        raise ValueError(f"No root .mscx found under {work_dir}")
    if len(root_mscx) > 1:
        raise ValueError(
            f"Expected one root .mscx under {work_dir}, found: "
            f"{[p.name for p in root_mscx]}"
        )

    score_mscx = root_mscx[0]
    targets.append(
        _MposExportTarget(
            key=score_mscx.stem,
            mscx_path=score_mscx,
            style_path=_score_style_path(work_dir),
            is_excerpt=False,
        )
    )

    excerpts_dir = work_dir / "Excerpts"
    if excerpts_dir.is_dir():
        for excerpt_dir in sorted(p for p in excerpts_dir.iterdir() if p.is_dir()):
            mscx_files = sorted(excerpt_dir.glob("*.mscx"))
            if not mscx_files:
                continue
            mscx = mscx_files[0]
            style = excerpt_dir / f"{mscx.stem}.mss"
            if not style.is_file():
                sibling_mss = sorted(excerpt_dir.glob("*.mss"))
                style_path = sibling_mss[0] if sibling_mss else None
            else:
                style_path = style
            targets.append(
                _MposExportTarget(
                    key=excerpt_dir.name,
                    mscx_path=mscx,
                    style_path=style_path,
                    is_excerpt=True,
                )
            )

    return targets


def _export_one_mpos(
    target: _MposExportTarget,
    output_path: Path,
    *,
    timeout: int = 120,
) -> None:
    """Export a single .mpos via MuseScore CLI (``-S`` style when present)."""
    if output_path.exists():
        output_path.unlink()

    cmd = ["musescore", "-f"]
    if target.style_path is not None and target.style_path.is_file():
        cmd.extend(["-S", str(target.style_path)])
    cmd.extend(["-o", str(output_path), str(target.mscx_path)])

    proc = run_musescore(cmd, timeout=timeout)
    if proc.returncode != 0 or not output_path.is_file():
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"MuseScore failed exporting '{target.key}' to {output_path}"
            + (f":\n{detail}" if detail else f" (exit {proc.returncode})")
        )


@app.post("/export-all-mpos")
async def export_all_mpos(
    file: UploadFile,
    include_score: bool = Form(True),
):
    """
    Unpack a .mscz and export .mpos measure-position files for the score
    and/or each part excerpt, matching part-formatter-v2's generate helper.

    Returns a zip of ``{key}.mpos`` files (excerpt folder names / score stem).
    """
    logger.info("========================================")
    logger.info("Starting /export-all-mpos")
    logger.info("========================================")
    logger.info(f"Filename: {file.filename}")
    logger.info(f"include_score: {include_score}")

    async with render_lock:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / (file.filename or "score.mscz")
            work_dir = tmp / "unpacked"
            out_dir = tmp / "mpos"
            work_dir.mkdir()
            out_dir.mkdir()

            file_content = await file.read()
            logger.info(f"Received file size: {len(file_content)} bytes")
            src.write_bytes(file_content)

            try:
                with zipfile.ZipFile(src, "r") as zf:
                    zf.extractall(work_dir)
            except zipfile.BadZipFile as e:
                raise HTTPException(400, f"Invalid .mscz (not a zip): {e}") from e

            try:
                targets = _list_mpos_export_targets(work_dir)
            except ValueError as e:
                raise HTTPException(400, str(e)) from e

            mpos_files: list[tuple[str, bytes]] = []

            for target in targets:
                if target.is_excerpt:
                    pass
                elif not include_score:
                    continue

                mpos_path = out_dir / f"{target.key}.mpos"
                logger.info(f"Exporting {target.key} -> {mpos_path.name}")

                try:
                    _export_one_mpos(target, mpos_path, timeout=120)
                except subprocess.TimeoutExpired:
                    logger.exception(f"MuseScore timed out exporting {target.key}")
                    raise HTTPException(
                        504,
                        f"MuseScore timed out exporting '{target.key}'",
                    )
                except RuntimeError as e:
                    logger.exception(f"Failed exporting {target.key}")
                    raise HTTPException(500, str(e)) from e

                mpos_files.append((f"{target.key}.mpos", mpos_path.read_bytes()))
                logger.info(
                    f"Exported {target.key}: {mpos_path.stat().st_size} bytes"
                )

            if not mpos_files:
                raise HTTPException(
                    500,
                    "No .mpos files were generated (check parts / include_score)",
                )

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for name, content in mpos_files:
                    zip_file.writestr(name, content)
                    logger.info(f"Added to zip: {name} ({len(content)} bytes)")

            zip_buffer.seek(0)
            src_stem = Path(file.filename or "score").stem
            logger.info(f"export-all-mpos completed: {len(mpos_files)} file(s)")

            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{src_stem}_mpos.zip"'
                    )
                },
            )


@app.get("/health")
def health():
    logger.info("/health called")
    return {"status": "ok"}
