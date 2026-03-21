"""Three-way merge of MuseScore (.mscx / .mscz) scores using measure-level hashes."""

from __future__ import annotations

import io
import zipfile
from copy import deepcopy
import xml.etree.ElementTree as ET

from .utils import extract_measures


class MergeConflict(Exception):
    """Raised when base, ours, and theirs cannot be merged without ambiguity."""

    def __init__(
        self,
        message: str,
        *,
        conflicts: list[tuple[str, int]] | None = None,
    ) -> None:
        # (staff_id, measure_number) — same roles as scoreforge (part_id, measure_number).
        self.conflicts: list[tuple[str, int]] = conflicts or []
        super().__init__(message)


def _mscz_primary_mscx_arcname(zf: zipfile.ZipFile) -> str:
    """Pick the main score .mscx inside an .mscz (exclude part excerpts)."""
    names = [
        n
        for n in zf.namelist()
        if n.endswith(".mscx") and "/Excerpts/" not in n.replace("\\", "/")
    ]
    if not names:
        raise ValueError("No score .mscx found in archive (excluding Excerpts).")
    if len(names) == 1:
        return names[0]
    root_only = [n for n in names if "/" not in n and "\\" not in n]
    if len(root_only) == 1:
        return root_only[0]
    raise ValueError(f"Ambiguous score .mscx in archive: {names!r}")


def load_score_tree(path: str) -> ET.ElementTree:
    """
    Load an uncompressed .mscx or the primary score .mscx embedded in a .mscz.
    """
    lower = path.lower()
    if lower.endswith(".mscx"):
        return ET.parse(path)
    if lower.endswith(".mscz"):
        with zipfile.ZipFile(path, "r") as zf:
            arc = _mscz_primary_mscx_arcname(zf)
            return ET.parse(io.BytesIO(zf.read(arc)))
    raise ValueError(f"Unsupported score format (expected .mscx or .mscz): {path!r}")


def _write_mscz_replacing_primary_mscx(
    template_zip_path: str,
    merged_tree: ET.ElementTree,
    output_zip_path: str,
) -> None:
    """Copy *template_zip_path* to *output_zip_path*, replacing the primary .mscx body."""
    buf = io.BytesIO()
    merged_tree.write(buf, encoding="UTF-8", xml_declaration=True)
    merged_bytes = buf.getvalue()

    with zipfile.ZipFile(template_zip_path, "r") as zin:
        arc = _mscz_primary_mscx_arcname(zin)
        with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = merged_bytes if info.filename == arc else zin.read(info.filename)
                zout.writestr(info, data)


def _top_level_staves_by_id(score_el: ET.Element) -> dict[str, ET.Element]:
    """
    Map staff id -> top-level <Staff> under <Score> (same notion as scoreforge Part.part_id).
    """
    out: dict[str, ET.Element] = {}
    for i, s in enumerate(score_el.findall("Staff")):
        sid = s.get("id")
        key = str(sid) if sid is not None else str(i + 1)
        if key in out:
            raise MergeConflict(
                f"Duplicate top-level <Staff id={key!r}> in score; ids must be unique.",
            )
        out[key] = s
    return out


def _lcs_align(seq_base: list[str], seq_other: list[str]) -> list[tuple[int | None, int | None]]:
    """
    Align seq_base with seq_other using LCS on hashes.
    Returns (base_idx, other_idx) pairs in document order; None marks an insertion
    in the other branch or a deletion from base.
    """
    n, m = len(seq_base), len(seq_other)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if seq_base[i] == seq_other[j]:
                L[i + 1][j + 1] = L[i][j] + 1
            else:
                L[i + 1][j + 1] = max(L[i][j + 1], L[i + 1][j])

    result: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and seq_base[i - 1] == seq_other[j - 1]:
            result.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or L[i][j - 1] >= L[i - 1][j]):
            result.append((None, j - 1))
            j -= 1
        elif i > 0 and (j == 0 or L[i][j - 1] < L[i - 1][j]):
            result.append((i - 1, None))
            i -= 1

    result.reverse()
    return result


def _merge_staff_measures(
    mb: list[tuple[int, str, ET.Element]],
    mo: list[tuple[int, str, ET.Element]],
    mt: list[tuple[int, str, ET.Element]],
    staff_id: str,
) -> tuple[list[ET.Element], list[tuple[str, int]]]:
    """
    Merge one staff's measures (already sanitized). Ours = local, theirs = remote
    (same roles as scoreforge's user / head).

    Returns merged measure elements and conflict list (staff_id, output measure index).
    """
    hb = [h for (_, h, _) in mb]
    ho = [h for (_, h, _) in mo]
    ht = [h for (_, h, _) in mt]

    align_base_ours = _lcs_align(hb, ho)
    align_base_theirs = _lcs_align(hb, ht)

    base_to_ours: dict[int, int] = {}
    base_to_theirs: dict[int, int] = {}
    ours_insertions: list[int] = []
    theirs_insertions: list[int] = []

    for bi, oi in align_base_ours:
        if bi is not None:
            base_to_ours[bi] = oi
        elif oi is not None:
            ours_insertions.append(oi)

    for bi, ti in align_base_theirs:
        if bi is not None:
            base_to_theirs[bi] = ti
        elif ti is not None:
            theirs_insertions.append(ti)

    same_length = len(mb) == len(mo) == len(mt)
    if same_length:
        base_to_ours = {i: i for i in range(len(mb))}
        base_to_theirs = {i: i for i in range(len(mb))}
        ours_insertions = []
        theirs_insertions = []

    merged: list[ET.Element] = []
    conflicts: list[tuple[str, int]] = []
    out_measure_num = 1
    theirs_ins_idx = 0
    ours_ins_idx = 0
    ours_ins_sorted = sorted(ours_insertions)
    theirs_ins_sorted = sorted(theirs_insertions)

    for base_idx in range(len(mb)):
        theirs_idx = base_to_theirs.get(base_idx)
        ours_idx = base_to_ours.get(base_idx)

        while ours_ins_idx < len(ours_ins_sorted):
            oi = ours_ins_sorted[ours_ins_idx]
            if ours_idx is not None and oi >= ours_idx:
                break
            merged.append(deepcopy(mo[oi][2]))
            out_measure_num += 1
            ours_ins_idx += 1

        while theirs_ins_idx < len(theirs_ins_sorted):
            ti = theirs_ins_sorted[theirs_ins_idx]
            if theirs_idx is not None and ti >= theirs_idx:
                break
            merged.append(deepcopy(mt[ti][2]))
            out_measure_num += 1
            theirs_ins_idx += 1

        base_meas = mb[base_idx]
        base_hash = hb[base_idx]
        elem_b = base_meas[2]

        elem_o = mo[ours_idx][2] if ours_idx is not None else None
        elem_t = mt[theirs_idx][2] if theirs_idx is not None else None
        ho_cur = ho[ours_idx] if ours_idx is not None else None
        ht_cur = ht[theirs_idx] if theirs_idx is not None else None

        if elem_t is not None and elem_o is not None:
            if base_hash == ht_cur == ho_cur:
                merged.append(deepcopy(elem_b))
            elif base_hash == ht_cur:
                merged.append(deepcopy(elem_o))
            elif base_hash == ho_cur:
                merged.append(deepcopy(elem_t))
            elif ht_cur == ho_cur:
                merged.append(deepcopy(elem_t))
            else:
                conflicts.append((staff_id, out_measure_num))
            out_measure_num += 1
        elif elem_t is not None and elem_o is None:
            if base_hash == ht_cur:
                pass
            else:
                conflicts.append((staff_id, out_measure_num))
                out_measure_num += 1
        elif elem_o is not None and elem_t is None:
            if base_hash == ho_cur:
                pass
            else:
                conflicts.append((staff_id, out_measure_num))
                out_measure_num += 1

    for ti in theirs_ins_sorted[theirs_ins_idx:]:
        merged.append(deepcopy(mt[ti][2]))
        out_measure_num += 1

    for oi in ours_ins_sorted[ours_ins_idx:]:
        merged.append(deepcopy(mo[oi][2]))
        out_measure_num += 1

    return merged, conflicts


def merge_three_way_musescore(
    base_path: str,
    ours_path: str,
    theirs_path: str,
    output_path: str | None = None,
) -> ET.ElementTree:
    """
    Merge three scores (.mscx or .mscz) using the same 3-way rules as
    ``scoreforge.merger.three_way_merge_scores``:

    - Top-level ``<Staff id=\"…\">`` elements are matched by ``id`` (same as
      scoreforge ``Part.part_id`` from ``parse_score``), not by list position.
    - Part ids are the sorted union of ids present in base, ours, or theirs;
      staves present on only one side are copied like scoreforge's early exits.
    - LCS on measure hashes per staff, with positional alignment when all three
      sides have the same measure count.
    - Conflicts on any staff are collected and raised together in one
      ``MergeConflict`` (``conflicts`` entries are ``(staff_id, measure_number)``).

    Non-measure score metadata and ``<Part>`` blocks come from a deep copy of
    *ours*; top-level ``<Staff>`` nodes are replaced in sorted staff-id order
    with merged staves.

    If *output_path* ends with ``.mscz``, the archive layout is copied from
    *ours_path*, which must be an ``.mscz`` so thumbnails, styles, and paths
    stay consistent; only the primary score ``.mscx`` inside the zip is replaced.

    Raises:
        MergeConflict: Duplicate staff ids, ambiguous measure resolution, or
            asymmetric delete/edit (mirrors scoreforge rules).
        ValueError: Unsupported extensions, or ``.mscz`` output with non-``.mscz`` ours.
    """
    tree_b = load_score_tree(base_path)
    tree_o = load_score_tree(ours_path)
    tree_t = load_score_tree(theirs_path)

    score_b = tree_b.getroot().find("Score")
    score_o_src = tree_o.getroot().find("Score")
    score_t = tree_t.getroot().find("Score")
    if score_b is None or score_o_src is None or score_t is None:
        raise ValueError("No <Score> tag found in the XML.")

    db = _top_level_staves_by_id(score_b)
    do = _top_level_staves_by_id(score_o_src)
    dt = _top_level_staves_by_id(score_t)

    part_ids = sorted(set(db.keys()) | set(do.keys()) | set(dt.keys()))

    tree_merged = deepcopy(tree_o)
    score_merged = tree_merged.getroot().find("Score")
    assert score_merged is not None

    rebuilt: list[ET.Element] = []
    all_conflicts: list[tuple[str, int]] = []

    for sid in part_ids:
        sb = db.get(sid)
        so = do.get(sid)
        st = dt.get(sid)

        if sb is None and st is None:
            if so is not None:
                rebuilt.append(deepcopy(so))
            continue
        if sb is None and so is None:
            if st is not None:
                rebuilt.append(deepcopy(st))
            continue
        if st is None and so is None:
            if sb is not None:
                rebuilt.append(deepcopy(sb))
            continue

        mb = extract_measures(sb) if sb is not None else []
        mo = extract_measures(so) if so is not None else []
        mt = extract_measures(st) if st is not None else []

        merged_measures, loc = _merge_staff_measures(mb, mo, mt, sid)
        all_conflicts.extend(loc)

        template = so if so is not None else (st if st is not None else sb)
        assert template is not None
        elem = deepcopy(template)
        if not loc:
            # Preserve siblings before the first measure (e.g. VBox) and after the
            # last measure (e.g. <cutaway>). Appending only would place merged
            # measures after trailing markup and MuseScore can drop or ignore them.
            children = list(elem)
            measure_elems = [c for c in children if c.tag == "Measure"]
            insert_pos = (
                children.index(measure_elems[0]) if measure_elems else len(children)
            )
            for old in measure_elems:
                elem.remove(old)
            for j, m in enumerate(merged_measures):
                elem.insert(insert_pos + j, m)
        rebuilt.append(elem)

    children = list(score_merged)
    staff_indices = [i for i, c in enumerate(children) if c.tag == "Staff"]
    if staff_indices:
        insert_at = staff_indices[0]
        for i in reversed(staff_indices):
            score_merged.remove(children[i])
        for off, staff_el in enumerate(rebuilt):
            score_merged.insert(insert_at + off, staff_el)
    else:
        for staff_el in rebuilt:
            score_merged.append(staff_el)

    if all_conflicts:
        raise MergeConflict(
            f"Merge conflict: {len(all_conflicts)} measure slot(s) could not be merged.",
            conflicts=all_conflicts,
        )

    if output_path is not None:
        out_lower = output_path.lower()
        if out_lower.endswith(".mscz"):
            if not ours_path.lower().endswith(".mscz"):
                raise ValueError(
                    "output_path is .mscz but ours_path is not; "
                    "use an .mscz for ours (container template) when writing .mscz."
                )
            _write_mscz_replacing_primary_mscx(ours_path, tree_merged, output_path)
        else:
            tree_merged.write(output_path, encoding="UTF-8", xml_declaration=True)

    return tree_merged
