import sys
from pathlib import Path

from scoreforge.io import (
    extract_mscx,
    write_mscz,
    generate_template_mscx,
    save_template_mscz,
    write_mscz_from_template,
)
from scoreforge.parser import parse_score
from scoreforge.converter import score_to_mscx, merge_measures_into_template
from scoreforge.serialization import save_canonical, load_score_from_json


def mscz_to_json(input_path: str, output_folder: str, output_filename: str = "output") -> None:
    """Convert a MSCZ file to canonical JSON format.
    
    Args:
        input_path: Path to input MSCZ file
        output_folder: Path to output folder
        output_filename: Base filename for output files (without extension)
    """
    mscz = Path(input_path)
    tree = extract_mscx(mscz)
    score = parse_score(tree)
    save_canonical(score, Path(f"{output_folder}/{output_filename}.json"))
    template = generate_template_mscx(mscz)
    save_template_mscz(template, Path(f"{output_folder}/{output_filename}.mscz"), mscz)


def json_to_mscz(
    input_path: str,
    out_mscz: str,
    template_mscz_path: str | None = None
) -> None:
    """Convert a canonical JSON file to MSCZ format.
    
    If a template MSCZ path is provided, the measures from the JSON will be
    merged into the template, preserving all metadata and structure.
    Otherwise, a minimal MSCZ file is created.
    
    Args:
        input_path: Path to input JSON file
        out_mscz: Path to output MSCZ file
        template_mscz_path: Optional path to template MSCZ file
    """
    json_path = Path(input_path)
    output_path = Path(out_mscz)
    score = load_score_from_json(json_path)
    
    if template_mscz_path:
        # Merge measures into template
        template_path = Path(template_mscz_path)
        template_tree = extract_mscx(template_path)
        merged_tree = merge_measures_into_template(template_tree, score)
        write_mscz_from_template(merged_tree, output_path, template_path)
    else:
        # Create minimal MSCZ (backward compatibility)
        tree = score_to_mscx(score)
        write_mscz(tree, output_path)


def main() -> None:
    """Main entry point for the CLI."""
    if len(sys.argv) < 4:
        print("Usage: scoreforge <json|mscz> <input_path> <output_path>")
        sys.exit(1)

    command = sys.argv[1]
    input_path = sys.argv[2]
    output_path = sys.argv[3]


    if command == "json":
        mscz_to_json(input_path, output_path)
    elif command == "mscz":
        if len(sys.argv) > 4:
            json_to_mscz(input_path, output_path, sys.argv[4])
        else:
            raise Exception("Cannot generate mscz without template mscz file")
    else:
        print(f"Unknown command: {command}")
        print("Usage: scoreforge <json|mscz> <input_path> <output_path>")
        sys.exit(1)

