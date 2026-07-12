"""Discover part excerpts inside an unpacked MSCZ and match them to MPOS inputs."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re


@dataclass(frozen=True)
class ExcerptInfo:
    """One part excerpt under Excerpts/ in an MSCZ."""

    key: str
    """Folder / stem name, e.g. ``0_Trumpet_in_Bb``."""

    index: int | None
    name: str
    """Part name without leading index, e.g. ``Trumpet_in_Bb``."""

    mscx_path: str


_INDEXED_KEY = re.compile(r"^(\d+)_(.+)$")


def _parse_excerpt_key(key: str) -> tuple[int | None, str]:
    m = _INDEXED_KEY.match(key)
    if m:
        return int(m.group(1)), m.group(2)
    return None, key


def list_excerpts(work_dir: str, mscx_files: list[str] | None = None) -> list[ExcerptInfo]:
    """
    Return every part MSCX under ``Excerpts/``, sorted by index then key.
    """
    if mscx_files is None:
        mscx_files = []
        for root, _, files in os.walk(work_dir):
            for filename in files:
                if filename.endswith(".mscx"):
                    mscx_files.append(os.path.join(root, filename))

    excerpts: list[ExcerptInfo] = []
    for path in mscx_files:
        rel = os.path.relpath(path, work_dir).replace("\\", "/")
        parts = rel.split("/")
        if len(parts) < 2 or parts[0] != "Excerpts":
            continue
        key = parts[1]
        index, name = _parse_excerpt_key(key)
        excerpts.append(
            ExcerptInfo(key=key, index=index, name=name, mscx_path=path)
        )

    excerpts.sort(key=lambda e: (e.index is None, e.index if e.index is not None else 0, e.key))
    return excerpts


def resolve_part_mpos(
    excerpts: list[ExcerptInfo],
    part_mpos: dict[str, str],
) -> dict[str, tuple[ExcerptInfo, str]]:
    """
    Map each ``part_mpos`` entry to an excerpt.

    Keys may be any of:
    - excerpt folder key (``0_Trumpet_in_Bb``)
    - part name without index (``Trumpet_in_Bb``)
    - excerpt index as a string (``0``)

    Raises ``ValueError`` if a key is missing/ambiguous, or if any excerpt that
    should be exported is not listed (callers decide which set is required).
    """
    by_key = {e.key: e for e in excerpts}
    by_name: dict[str, list[ExcerptInfo]] = {}
    by_index: dict[str, ExcerptInfo] = {}
    for e in excerpts:
        by_name.setdefault(e.name, []).append(e)
        if e.index is not None:
            by_index[str(e.index)] = e

    resolved: dict[str, tuple[ExcerptInfo, str]] = {}
    for raw_key, mpos_path in part_mpos.items():
        key = raw_key.strip()
        if not key:
            raise ValueError("Empty part key in part_mpos")
        if not os.path.isfile(mpos_path):
            raise FileNotFoundError(f"MPOS file not found for part '{key}': {mpos_path}")

        excerpt: ExcerptInfo | None = None
        if key in by_key:
            excerpt = by_key[key]
        elif key in by_index:
            excerpt = by_index[key]
        elif key in by_name:
            matches = by_name[key]
            if len(matches) > 1:
                raise ValueError(
                    f"Ambiguous part key '{key}' matches multiple excerpts: "
                    f"{[m.key for m in matches]}"
                )
            excerpt = matches[0]
        else:
            available = [e.key for e in excerpts]
            raise ValueError(
                f"No excerpt matched part key '{key}'. Available: {available}"
            )

        if excerpt.key in resolved:
            raise ValueError(
                f"Part '{excerpt.key}' matched more than once in part_mpos "
                f"(duplicate via '{key}')"
            )
        resolved[excerpt.key] = (excerpt, mpos_path)

    return resolved
