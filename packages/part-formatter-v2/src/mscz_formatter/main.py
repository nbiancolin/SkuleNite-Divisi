"""Command-line entry point for formatting MuseScore .mscz files."""

from __future__ import annotations

import argparse
import json
import sys

from mscz_formatter.mscz import Style, format_mscz


def _parse_part_mpos(values: list[str]) -> dict[str, str]:
    """
    Accept repeated ``PART=PATH`` arguments, or a single JSON object string.
    """
    if len(values) == 1 and values[0].strip().startswith("{"):
        data = json.loads(values[0])
        if not isinstance(data, dict):
            raise ValueError("--part-mpos JSON must be an object of part → path")
        return {str(k): str(v) for k, v in data.items()}

    result: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(
                f"Invalid --part-mpos '{item}'; expected PART=PATH or a JSON object"
            )
        part, path = item.split("=", 1)
        part = part.strip()
        path = path.strip()
        if not part or not path:
            raise ValueError(f"Invalid --part-mpos '{item}': empty part or path")
        result[part] = path
    return result


def main(argv: list[str] | None = None) -> int:
    """
    Example::

        python -m mscz_formatter.main in.mscz out.mscz \\
            --part-mpos 0_Trumpet_in_Bb=trumpet.mpos \\
            --part-mpos Trombone=trombone.mpos \\
            --style broadway
    """
    parser = argparse.ArgumentParser(
        description=(
            "Format a MuseScore .mscz file. Provide one .mpos file for each "
            "part you expect to export."
        )
    )
    parser.add_argument("input", help="Path to input .mscz file")
    parser.add_argument("output", help="Path to output .mscz file")
    parser.add_argument(
        "--part-mpos",
        action="append",
        required=True,
        metavar="PART=PATH",
        help=(
            "Part key and its .mpos path (repeatable). Part keys may be excerpt "
            "folder names, names without index, or indices. "
            "Alternatively pass a single JSON object."
        ),
    )
    parser.add_argument(
        "--style",
        dest="selected_style",
        default="broadway",
        choices=[s.value for s in Style],
        help="Style to apply (default: broadway)",
    )
    parser.add_argument(
        "--staff-spacing-strategy",
        choices=("predict", "preserve", "override"),
        default="predict",
        dest="staff_spacing_strategy",
        help="Spatium: predict from staff count, keep input .mss values, or override.",
    )
    parser.add_argument(
        "--staff-spacing-value",
        default=None,
        help="When strategy is override, MuseScore spatium (e.g. 1.74978).",
    )
    parser.add_argument(
        "--no-styles",
        action="store_true",
        help="Skip replacing .mss style templates",
    )
    parser.add_argument(
        "--no-layout",
        action="store_true",
        help="Skip MPOS-based line/page layout on parts",
    )

    args = parser.parse_args(argv)

    try:
        part_mpos = _parse_part_mpos(args.part_mpos)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error parsing --part-mpos: {e}", file=sys.stderr)
        return 1

    params = {
        "selected_style": args.selected_style,
        "staff_spacing_strategy": args.staff_spacing_strategy,
        "staff_spacing_value": args.staff_spacing_value,
        "apply_mss_style": not args.no_styles,
        "apply_part_layout": not args.no_layout,
    }

    try:
        success = format_mscz(args.input, args.output, part_mpos, params)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if success:
        print(f"Formatted score written to {args.output}")
        return 0

    print("Formatting failed. See logs for details.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
