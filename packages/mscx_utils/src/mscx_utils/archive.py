"""Read/write MuseScore .mscz (ZIP) archives and locate .mscx members."""

from __future__ import annotations

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from contextlib import contextmanager
from typing import Iterator


def is_excerpt_mscx_arc(arcname: str) -> bool:
    normalized = arcname.replace("\\", "/")
    return normalized.startswith("Excerpts/") or "/Excerpts/" in normalized


def pick_main_mscx_arc_from_namelist(namelist: list[str]) -> str:
    """
    Choose the main score .mscx inside an archive (not excerpt/part scores).

    Prefers non-excerpt paths, then the shallowest path (typical MuseScore layout).
    """
    mscx = sorted(n for n in namelist if n.lower().endswith(".mscx"))
    if not mscx:
        raise ValueError("No .mscx members found in archive")
    main_candidates = [n.replace("\\", "/") for n in mscx if not is_excerpt_mscx_arc(n)]
    if not main_candidates:
        main_candidates = [n.replace("\\", "/") for n in mscx]
    main_candidates.sort(key=lambda p: (p.count("/") + p.count("\\"), len(p)))
    return main_candidates[0]


def mscx_path_from_extract_dir(extract_dir: str, arc: str) -> str:
    return os.path.normpath(os.path.join(extract_dir, *arc.replace("\\", "/").split("/")))


def mscx_arcnames(mscz_path: str) -> set[str]:
    with zipfile.ZipFile(mscz_path, "r") as zf:
        return {name for name in zf.namelist() if name.endswith(".mscx")}


def partition_mscx_arcs(arcs: set[str]) -> tuple[str, set[str]]:
    """Return the single main-score .mscx arc and any excerpt .mscx arcs."""
    main_arcs = sorted(a for a in arcs if not is_excerpt_mscx_arc(a))
    excerpt_arcs = {a for a in arcs if is_excerpt_mscx_arc(a)}
    if len(main_arcs) != 1:
        raise ValueError(f"Expected exactly one main .mscx file, found {main_arcs!r}")
    return main_arcs[0], excerpt_arcs


def write_mscz_from_dir(source_dir: str, output_path: str) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                arcname = os.path.relpath(full_path, source_dir).replace(os.sep, "/")
                zipf.write(full_path, arcname)


def extract_mscz(mscz_path: str, extract_dir: str) -> None:
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(mscz_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)


def extract_mscz_main_mscx(mscz_path: str, extract_dir: str) -> tuple[str, str]:
    """Extract one .mscz into ``extract_dir`` and return (main arc, path on disk)."""
    with zipfile.ZipFile(mscz_path, "r") as zip_ref:
        namelist = zip_ref.namelist()
        main_arc = pick_main_mscx_arc_from_namelist(namelist)
        zip_ref.extractall(extract_dir)
    return main_arc, mscx_path_from_extract_dir(extract_dir, main_arc)


def list_mscx_paths_in_extract_dir(extract_dir: str, namelist: list[str]) -> list[str]:
    return [
        mscx_path_from_extract_dir(extract_dir, name)
        for name in namelist
        if name.endswith(".mscx")
    ]


@contextmanager
def unpack_mscz_to_tempdir(
    mscz_path: str, *, repack: bool = True
) -> Iterator[tuple[str, list[str]]]:
    """
    Unpack a .mscz (zip) into a temporary directory.

    On successful exit and if ``repack`` is True, rezip contents back into the same .mscz.
    Yields ``(work_dir, list of absolute .mscx paths on disk)``.
    """
    with tempfile.TemporaryDirectory() as work_dir:
        with zipfile.ZipFile(mscz_path, "r") as z:
            z.extractall(work_dir)
            mscx_files = list_mscx_paths_in_extract_dir(work_dir, z.namelist())

        yield work_dir, mscx_files

        if repack:
            write_mscz_from_dir(work_dir, mscz_path)


def remove_excerpts_from_mscz_dir(mscz_dir: str) -> None:
    """Remove excerpt files and container references from an extracted MSCZ directory."""
    excerpts_dir = os.path.join(mscz_dir, "Excerpts")
    if os.path.isdir(excerpts_dir):
        shutil.rmtree(excerpts_dir)

    container_path = os.path.join(mscz_dir, "META-INF", "container.xml")
    if not os.path.isfile(container_path):
        return

    tree = ET.parse(container_path)
    rootfiles = tree.getroot().find("rootfiles")
    if rootfiles is None:
        return

    for rootfile in list(rootfiles.findall("rootfile")):
        full_path = rootfile.get("full-path", "").replace("\\", "/")
        if full_path.startswith("Excerpts/"):
            rootfiles.remove(rootfile)

    tree.write(container_path, encoding="UTF-8", xml_declaration=True)
