import sys
from pathlib import Path

from scoreforge.merger import MergeConflict, three_way_merge_scores
from scoreforge.serialization import load_score_from_json, save_canonical


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: scoreforge-merge-driver <base> <current> <other>", file=sys.stderr)
        return 2

    base_path = Path(argv[1])
    current_path = Path(argv[2])
    other_path = Path(argv[3])

    base = load_score_from_json(base_path)
    current = load_score_from_json(current_path)
    other = load_score_from_json(other_path)

    try:
        merged = three_way_merge_scores(user_score=current, base_score=base, head_score=other)
    except MergeConflict as e:
        print(str(e), file=sys.stderr)
        return 1

    save_canonical(merged, current_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

