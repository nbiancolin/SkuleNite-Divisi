"""
Generate MuseScore ``.mpos`` measure-position files for a ``.mscz``.

MuseScore's CLI only lays out the score (or a single opened MSCX) when writing
``.mpos``, so this helper unpacks the archive and exports one ``.mpos`` per
embedded MSCX. Each export loads the matching ``.mss`` via ``-S`` — score style
for the root score, part style for each excerpt.

Example::

    python generate_mpos_for_mscz.py bows.mscz
    python generate_mpos_for_mscz.py bows.mscz --parts 11_Violin --parts Guitar
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


_WINDOWS_MUSESCORE_CANDIDATES = (
    Path(r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"),
    Path(r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe"),
    Path(r"C:\Program Files (x86)\MuseScore 3\bin\MuseScore3.exe"),
)


@dataclass(frozen=True)
class _ExportTarget:
    """One MSCX inside an unpacked MSCZ, plus its style file if present."""

    key: str
    mscx_path: Path
    style_path: Path | None
    is_excerpt: bool


def find_musescore(explicit: str | None = None) -> str:
    """Resolve the MuseScore binary (``MUSESCORE`` env, PATH, or common installs)."""
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"MuseScore binary not found: {explicit}")
        return str(path)

    env = os.environ.get("MUSESCORE") or os.environ.get("MUSESCORE_PATH")
    if env:
        path = Path(env)
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"MUSESCORE env points to missing file: {env}")

    for name in ("musescore", "mscore", "MuseScore4", "MuseScore3"):
        found = shutil.which(name)
        if found:
            return found

    if sys.platform.startswith("win"):
        for candidate in _WINDOWS_MUSESCORE_CANDIDATES:
            if candidate.is_file():
                return str(candidate)

    raise FileNotFoundError(
        "Could not find MuseScore. Install it, add it to PATH, or set MUSESCORE."
    )


def _score_style_path(work_dir: Path) -> Path | None:
    preferred = work_dir / "score_style.mss"
    if preferred.is_file():
        return preferred
    mss_files = sorted(work_dir.glob("*.mss"))
    return mss_files[0] if mss_files else None


def list_export_targets(work_dir: Path) -> list[_ExportTarget]:
    """Discover the root score and every ``Excerpts/<key>/*.mscx`` target."""
    targets: list[_ExportTarget] = []

    root_mscx = sorted(
        p for p in work_dir.glob("*.mscx") if p.is_file()
    )
    if not root_mscx:
        raise ValueError(f"No root .mscx found under {work_dir}")
    if len(root_mscx) > 1:
        raise ValueError(
            f"Expected one root .mscx under {work_dir}, found: "
            f"{[p.name for p in root_mscx]}"
        )

    score_mscx = root_mscx[0]
    targets.append(
        _ExportTarget(
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
                _ExportTarget(
                    key=excerpt_dir.name,
                    mscx_path=mscx,
                    style_path=style_path,
                    is_excerpt=True,
                )
            )

    return targets


def _export_one_mpos(
    musescore: str,
    target: _ExportTarget,
    output_path: Path,
    *,
    timeout: float = 120,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    cmd = [musescore, "-f"]
    if target.style_path is not None and target.style_path.is_file():
        cmd.extend(["-S", str(target.style_path)])
    cmd.extend(["-o", str(output_path), str(target.mscx_path)])

    env = os.environ.copy()
    # Docker / CI image sets this; don't force it on desktop MuseScore (Windows).
    if not sys.platform.startswith("win"):
        env.setdefault("QT_QPA_PLATFORM", "offscreen")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0 or not output_path.is_file():
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"MuseScore failed exporting '{target.key}' to {output_path}"
            + (f":\n{detail}" if detail else f" (exit {proc.returncode})")
        )


def _matches_part_filter(key: str, part_filters: set[str] | None) -> bool:
    if not part_filters:
        return True
    if key in part_filters:
        return True
    # Allow matching by bare name without leading index: Violin vs 11_Violin
    for filt in part_filters:
        if key.endswith(f"_{filt}") or key == filt:
            return True
        if "_" in key and key.split("_", 1)[1] == filt:
            return True
    return False


def generate(
    mscz_path: str,
    output_dir: str | None = None,
    *,
    musescore: str | None = None,
    parts: list[str] | None = None,
    include_score: bool = True,
    copy_styles: bool = True,
    timeout: float = 120,
) -> dict[str, str]:
    """
    Unpack ``mscz_path`` and export ``.mpos`` files for the score and/or parts.

    Args:
        mscz_path: Source ``.mscz``.
        output_dir: Where to write ``.mpos`` (and optional ``.mss``) files.
            Defaults to the directory containing the MSCZ.
        musescore: Optional path to the MuseScore binary.
        parts: If set, only export excerpts whose key/name matches one of these.
        include_score: Also export the root score ``.mpos``.
        copy_styles: Copy each used ``.mss`` next to the corresponding ``.mpos``.
        timeout: Per-export MuseScore timeout in seconds.

    Returns:
        Map of target key → absolute ``.mpos`` path.
    """
    mscz = Path(mscz_path).resolve()
    if not mscz.is_file():
        raise FileNotFoundError(f"MSCZ not found: {mscz}")

    out_dir = Path(output_dir).resolve() if output_dir else mscz.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    musescore_bin = find_musescore(musescore)
    part_filters = {p.strip() for p in (parts or []) if p.strip()} or None

    results: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="generate_mpos_") as tmp:
        work_dir = Path(tmp)
        with zipfile.ZipFile(mscz, "r") as zf:
            zf.extractall(work_dir)

        targets = list_export_targets(work_dir)
        for target in targets:
            if target.is_excerpt:
                if not _matches_part_filter(target.key, part_filters):
                    continue
            elif not include_score:
                continue
            # When filtering parts, skip the score unless include_score is True
            # and no part filter is set — actually keep include_score independent.

            mpos_path = out_dir / f"{target.key}.mpos"
            print(f"Exporting {target.key} -> {mpos_path.name}", flush=True)
            _export_one_mpos(musescore_bin, target, mpos_path, timeout=timeout)
            results[target.key] = str(mpos_path)

            if copy_styles and target.style_path is not None and target.style_path.is_file():
                style_out = out_dir / f"{target.key}.mss"
                shutil.copy2(target.style_path, style_out)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Unpack a .mscz and export .mpos measure positions for the score "
            "and each part, applying score vs part .mss styles via MuseScore -S."
        )
    )
    parser.add_argument("mscz", help="Path to input .mscz")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Directory for .mpos/.mss outputs (default: same folder as the .mscz)",
    )
    parser.add_argument(
        "--musescore",
        default=None,
        help="Path to MuseScore binary (or set MUSESCORE)",
    )
    parser.add_argument(
        "--parts",
        action="append",
        default=None,
        metavar="KEY",
        help="Only export these excerpt keys/names (repeatable)",
    )
    parser.add_argument(
        "--no-score",
        action="store_true",
        help="Skip exporting the root score .mpos",
    )
    parser.add_argument(
        "--no-copy-styles",
        action="store_true",
        help="Do not copy .mss style files next to the .mpos outputs",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120,
        help="Per-part MuseScore timeout in seconds (default: 120)",
    )

    args = parser.parse_args(argv)

    try:
        results = generate(
            args.mscz,
            args.output_dir,
            musescore=args.musescore,
            parts=args.parts,
            include_score=not args.no_score,
            copy_styles=not args.no_copy_styles,
            timeout=args.timeout,
        )
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not results:
        print("No targets exported (check --parts / --no-score).", file=sys.stderr)
        return 1

    print(f"Wrote {len(results)} .mpos file(s):")
    for key, path in results.items():
        print(f"  {key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
