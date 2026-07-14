"""
Dump the planned line breaks for each part in an MSCZ + sibling .mpos files.

Use this to compare parts that look good vs cramped after the e2e formatter:
any line whose width exceeds ``MAX_LINE_WIDTH`` would have been overfull under
the previous unbounded budget.

Example::

    python dump_line_plan.py
    python dump_line_plan.py bows.mscz
    python dump_line_plan.py bows.mscz --parts 10_Drum_Kit --parts Violin
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

# Allow running from the fixtures dir without an editable install.
# .../tests/test-data/e2e/this.py → package root is parents[3]
_SRC = Path(__file__).resolve().parents[3] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mscz_formatter.mscx.lines import add_line_breaks  # noqa: E402
from mscz_formatter.mscx.load import load_in  # noqa: E402
from mscz_formatter.mscx.models import MAX_LINE_WIDTH  # noqa: E402


def _matches_part_filter(key: str, part_filters: set[str] | None) -> bool:
    if not part_filters:
        return True
    if key in part_filters:
        return True
    for filt in part_filters:
        if key.endswith(f"_{filt}") or key == filt:
            return True
        if "_" in key and key.split("_", 1)[1] == filt:
            return True
    return False


def _format_measure(m) -> str:
    label = f"M{m.source_measure.num}"
    if m.is_mm_rest:
        label += f"*({m.mm_rest_span})"
    if m.has_rehearsal_mark:
        label += "R"
    if m.has_double_bar:
        label += "D"
    return label


def dump_part(mscx_path: Path, mpos_path: Path) -> tuple[int, int]:
    """Print the line plan for one part. Returns (line_count, overflow_count)."""
    data = load_in(str(mscx_path), str(mpos_path))
    lines = add_line_breaks(data["rendered_measures"])

    overflows = 0
    print(
        f"\n=== {mpos_path.stem}: {len(lines)} line(s), "
        f"budget={MAX_LINE_WIDTH} ==="
    )
    if not lines:
        print("  (no lines planned — check for DP failure / unmatched mpos)")
        return 0, 0

    for i, line in enumerate(lines):
        over = line.width > MAX_LINE_WIDTH
        if over:
            overflows += 1
        ratio = line.width / MAX_LINE_WIDTH if MAX_LINE_WIDTH else 0.0
        flag = " OVER" if over else ""
        measures = ",".join(_format_measure(m) for m in line.measures)
        print(
            f"  L{i}: c={line.c_count} rm={line.rm_count} "
            f"w={line.width:.0f} ({ratio:.0%}){flag}  [{measures}]"
        )

    print(f"  -> {overflows}/{len(lines)} line(s) over budget")
    return len(lines), overflows


def dump_mscz(
    mscz_path: Path,
    mpos_dir: Path,
    *,
    parts: list[str] | None = None,
    include_score: bool = False,
) -> int:
    """
    Unpack ``mscz_path`` and dump line plans for each excerpt with a matching
    ``.mpos`` under ``mpos_dir``.

    Returns process exit code (0 ok, 1 on missing inputs / no matches).
    """
    if not mscz_path.is_file():
        print(f"Error: MSCZ not found: {mscz_path}", file=sys.stderr)
        return 1

    part_filters = {p.strip() for p in (parts or []) if p.strip()} or None
    matched = 0
    total_overflows = 0

    with tempfile.TemporaryDirectory(prefix="dump_line_plan_") as tmp:
        work_dir = Path(tmp)
        with zipfile.ZipFile(mscz_path, "r") as zf:
            zf.extractall(work_dir)

        if include_score:
            root_mscx = sorted(p for p in work_dir.glob("*.mscx") if p.is_file())
            if root_mscx:
                score_mpos = mpos_dir / f"{root_mscx[0].stem}.mpos"
                if score_mpos.is_file() and _matches_part_filter(
                    root_mscx[0].stem, part_filters
                ):
                    _, overflows = dump_part(root_mscx[0], score_mpos)
                    matched += 1
                    total_overflows += overflows

        excerpts = work_dir / "Excerpts"
        if excerpts.is_dir():
            for excerpt_dir in sorted(p for p in excerpts.iterdir() if p.is_dir()):
                key = excerpt_dir.name
                if not _matches_part_filter(key, part_filters):
                    continue
                mscx_files = sorted(excerpt_dir.glob("*.mscx"))
                mpos_path = mpos_dir / f"{key}.mpos"
                if not mscx_files:
                    print(f"\n=== {key}: no .mscx in excerpt ===", file=sys.stderr)
                    continue
                if not mpos_path.is_file():
                    print(f"\n=== {key}: missing {mpos_path.name} ===", file=sys.stderr)
                    continue
                _, overflows = dump_part(mscx_files[0], mpos_path)
                matched += 1
                total_overflows += overflows

    if matched == 0:
        print("No parts dumped (check --parts / .mpos files).", file=sys.stderr)
        return 1

    print(
        f"\nSummary: {matched} part(s), {total_overflows} overfull line(s) "
        f"(budget={MAX_LINE_WIDTH})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Dump DP line plans for MSCZ parts using sibling .mpos widths, "
            "flagging lines over MAX_LINE_WIDTH."
        )
    )
    parser.add_argument(
        "mscz",
        nargs="?",
        default=str(here / "bows.mscz"),
        help="Path to input .mscz (default: bows.mscz next to this script)",
    )
    parser.add_argument(
        "--mpos-dir",
        default=None,
        help="Directory containing .mpos files (default: same dir as the .mscz)",
    )
    parser.add_argument(
        "--parts",
        action="append",
        default=None,
        metavar="KEY",
        help="Only dump these excerpt keys/names (repeatable)",
    )
    parser.add_argument(
        "--include-score",
        action="store_true",
        help="Also dump the root score if a matching .mpos exists",
    )

    args = parser.parse_args(argv)
    mscz_path = Path(args.mscz).resolve()
    mpos_dir = Path(args.mpos_dir).resolve() if args.mpos_dir else mscz_path.parent

    return dump_mscz(
        mscz_path,
        mpos_dir,
        parts=args.parts,
        include_score=args.include_score,
    )


if __name__ == "__main__":
    raise SystemExit(main())
