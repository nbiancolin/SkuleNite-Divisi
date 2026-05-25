import logging
import xml.etree.ElementTree as ET
import hashlib
from collections import deque
from copy import deepcopy
from enum import Enum

logger = logging.getLogger(__name__)

ALPHA_VALUE = 100

class State(Enum):
    UNCHANGED = 1
    MODIFIED = 2
    INSERTED = 3
    REMOVED = 4

# -- Compare Diff Utils --

# Entire elements with these tags are omitted from measure hashes (layout only).
_HASH_IGNORE_TAGS = frozenset(
    {
        "LayoutBreak",
        "layoutStretch",
        "stretch",
        "HBox",
        "VBox",
        "TBox",
    }
)

# Siblings with these tags may be reordered within a contiguous run for hashing.
# Musical events (Chord, Rest, …) keep document order.
_SORTABLE_SIBLING_TAGS = frozenset(
    {
        "StaffText",
        "RehearsalMark",
        "SystemText",
        "Marker",
        "Jump",
        "TimeSig",
        "KeySig",
        "Tempo",
        "Harmony",
        "FiguredBass",
    }
)


def _element_sort_key(elem: ET.Element) -> tuple[str, str]:
    """Stable key for ordering reorderable siblings."""
    raw = ET.tostring(elem, encoding="utf-8")
    normalized = b"".join(raw.split())
    return (elem.tag, normalized.decode("utf-8", errors="replace"))


def _sort_attribs(elem: ET.Element) -> None:
    if elem.attrib:
        elem.attrib = dict(sorted(elem.attrib.items()))


def _is_courtesy_or_invisible_timesig(elem: ET.Element) -> bool:
    """Time signatures used only for layout (not a real meter change)."""
    if elem.tag != "TimeSig":
        return False
    visible = elem.find("visible")
    if visible is not None and (visible.text or "").strip() in ("0", "false"):
        return True
    courtesy = elem.find("isCourtesy")
    if courtesy is not None and (courtesy.text or "").strip() in ("1", "true"):
        return True
    return False


def _canonicalize_measure_tree(elem: ET.Element) -> None:
    """
    Normalize measure XML so inconsequential sibling order differences hash the same.

    Recurses into children, sorts attributes, and sorts contiguous runs of
    annotation-like siblings (e.g. StaffText vs RehearsalMark) without moving
    them past Chord/Rest timeline events.
    """
    for child in list(elem):
        _canonicalize_measure_tree(child)
    _sort_attribs(elem)

    children = list(elem)
    if not children:
        return

    new_children: list[ET.Element] = []
    sortable_run: list[ET.Element] = []

    def flush_sortable_run() -> None:
        if not sortable_run:
            return
        sortable_run.sort(key=_element_sort_key)
        new_children.extend(sortable_run)
        sortable_run.clear()

    for child in children:
        if child.tag in _SORTABLE_SIBLING_TAGS:
            sortable_run.append(child)
        else:
            flush_sortable_run()
            new_children.append(child)
    flush_sortable_run()
    elem[:] = new_children


def _hash_measure(measure: ET.Element) -> str:
    """
    Return a stable hash of the measure's XML content.
    Allows for quick comparison
    """
    copy = deepcopy(measure)
    _sanitize_measure(copy)
    _canonicalize_measure_tree(copy)
    raw = ET.tostring(copy, encoding="utf-8")
    normalized = b"".join(raw.split())
    return hashlib.md5(normalized).hexdigest()

def _sanitize_measure(measure: ET.Element) -> ET.Element:
    """Remove IDs, layout-only elements, and other non-musical noise before hashing."""

    to_remove: list[tuple[ET.Element, ET.Element]] = []
    for elem in measure.iter():
        for child in list(elem):
            if child.tag in ("eid", "linkedMain"):
                to_remove.append((elem, child))
            elif child.tag in _HASH_IGNORE_TAGS:
                to_remove.append((elem, child))
            elif _is_courtesy_or_invisible_timesig(child):
                to_remove.append((elem, child))

    for parent, child in to_remove:
        parent.remove(child)
    return measure

def get_staves(filename: str) -> list[ET.Element]:
    parser = ET.XMLParser()
    tree = ET.parse(filename, parser)
    root = tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    return score.findall("Staff")


def get_parts_staff_elements(score: ET.Element) -> list[tuple[str, list[ET.Element]]]:
    """
    Map each <Part> to its score-level <Staff> elements (the ones that hold measures).

    MuseScore stores measure data on <Staff> children of <Score> in the same order as
    each part's <Staff> stubs (stub ``id`` attributes are not always present).
    """
    staves = score.findall("Staff")
    pos = 0
    out: list[tuple[str, list[ET.Element]]] = []
    for part in score.findall("Part"):
        track = part.find("trackName")
        name = (track.text or "") if track is not None else ""
        stubs = part.findall("Staff")
        if pos + len(stubs) > len(staves):
            raise ValueError(
                f"Part {name!r} references {len(stubs)} staves but only "
                f"{len(staves) - pos} remain in <Score>"
            )
        elems = staves[pos : pos + len(stubs)]
        pos += len(stubs)
        out.append((name, elems))
    if pos != len(staves):
        raise ValueError(
            f"{len(staves) - pos} score-level <Staff> elements are not assigned to a part"
        )
    return out


def pair_staves_by_part_order(
    score1: ET.Element, score2: ET.Element
) -> list[tuple[ET.Element, ET.Element]]:
    """Pair staves using matching part order and staff order within each part."""
    parts1 = get_parts_staff_elements(score1)
    parts2 = get_parts_staff_elements(score2)
    if len(parts1) != len(parts2):
        raise ValueError(
            f"Part count mismatch: {len(parts1)} in score1, {len(parts2)} in score2"
        )
    pairs: list[tuple[ET.Element, ET.Element]] = []
    for (name1, elems1), (name2, elems2) in zip(parts1, parts2):
        if len(elems1) != len(elems2):
            raise ValueError(
                f"Part {name1!r} / {name2!r}: {len(elems1)} vs {len(elems2)} staves"
            )
        if name1 != name2:
            logger.warning(
                "Pairing parts with different names: %r vs %r", name1, name2
            )
        pairs.extend(zip(elems1, elems2))
    return pairs


def pair_staves_by_track_name(score1: ET.Element, score2: ET.Element) -> list[tuple[ET.Element, ET.Element]]:
    """
    Pair score-level staves between two scores using part order in score1 and matching
    <trackName> in score2 (first unused match). Staves within a multi-staff part are
    paired in order.

    Parts with no name match in score2 are paired in document order with the remaining
    unmatched staves from score2 (same behavior as positional zip for those staves).
    """
    parts1 = get_parts_staff_elements(score1)
    parts2 = get_parts_staff_elements(score2)
    q2: deque[tuple[str, list[ET.Element]]] = deque(parts2)
    pairs: list[tuple[ET.Element, ET.Element]] = []
    unmatched1: list[ET.Element] = []

    for name1, elems1 in parts1:
        found_idx = None
        for idx, (name2, elems2) in enumerate(q2):
            if name2 == name1:
                if len(elems1) != len(elems2):
                    raise ValueError(
                        f"Part {name1!r} has {len(elems1)} staves in score1 but "
                        f"{len(elems2)} in score2."
                    )
                found_idx = idx
                break
        if found_idx is None:
            unmatched1.extend(elems1)
            continue
        for _ in range(found_idx):
            q2.append(q2.popleft())
        _, elems2 = q2.popleft()
        for s1, s2 in zip(elems1, elems2):
            pairs.append((s1, s2))

    unmatched2: list[ET.Element] = [s for _, staves in q2 for s in staves]
    if unmatched1 or unmatched2:
        if len(unmatched1) != len(unmatched2):
            raise ValueError(
                f"Cannot align staves: {len(unmatched1)} unmatched in score1, "
                f"{len(unmatched2)} in score2."
            )
        pairs.extend(zip(unmatched1, unmatched2))

    staves1 = score1.findall("Staff")
    staves2 = score2.findall("Staff")
    if len(staves1) != len(staves2):
        raise ValueError(
            f"Staff count mismatch: {len(staves1)} in score1, {len(staves2)} in score2."
        )
    if len(pairs) != len(staves1):
        raise ValueError(
            f"Staff pairing incomplete: matched {len(pairs)} of {len(staves1)} staves."
        )
    return pairs


def extract_measures(staff: ET.Element) -> list[tuple[int, str, ET.Element]]:
    """Return ``(1-based index, content hash, measure element)`` without mutating the staff."""
    measures: list[tuple[int, str, ET.Element]] = []
    for i, measure in enumerate(staff.findall("Measure"), start=1):
        measures.append((i, _hash_measure(measure), measure))
    return measures


# -- Visualize Diff Utils

def _make_cutaway() -> ET.Element:
    """Create cutaway element (from your existing code)."""
    return ET.fromstring("<cutaway>1</cutaway>")


def _measure_duration(measure: ET.Element) -> str | None:
    """Return the measure-length duration string (e.g. ``4/4``, ``3/4``) if present."""
    len_attr = measure.get("len")
    if len_attr:
        return len_attr

    for rest in measure.iter("Rest"):
        dt = rest.find("durationType")
        if dt is not None and (dt.text or "").strip() == "measure":
            dur = rest.find("duration")
            if dur is not None and dur.text:
                return dur.text.strip()

    for ts in measure.iter("TimeSig"):
        sig_n = ts.find("sigN")
        sig_d = ts.find("sigD")
        if (
            sig_n is not None
            and sig_d is not None
            and sig_n.text
            and sig_d.text
        ):
            return f"{sig_n.text.strip()}/{sig_d.text.strip()}"

    return None


def _effective_measure_duration(staff: ET.Element, index: int) -> str:
    """Duration at ``index``, walking backward for inherited time signatures."""
    measures = staff.findall("Measure")
    if not measures:
        return "4/4"
    for i in range(min(index, len(measures) - 1), -1, -1):
        duration = _measure_duration(measures[i])
        if duration:
            return duration
    return "4/4"


def _make_empty_measure(duration: str = "4/4") -> ET.Element:
    measure = ET.Element("Measure")
    voice = ET.SubElement(measure, "voice")
    rest = ET.SubElement(voice, "Rest")
    durationType = ET.SubElement(rest, "durationType")
    durationType.text = "measure"
    duration_elem = ET.SubElement(rest, "duration")
    duration_elem.text = duration

    return measure


def _make_placeholder_staff(reference_staff: ET.Element) -> ET.Element:
    """Score-level staff of rests for the LHS column when only the RHS has a part."""
    staff = ET.Element("Staff")
    measure_count = max(len(reference_staff.findall("Measure")), 1)
    for i in range(measure_count):
        staff.append(_make_empty_measure(_effective_measure_duration(reference_staff, i)))
    staff.append(_make_cutaway())
    return staff


def build_unified_diff_union(
    score1: ET.Element,
    score2: ET.Element,
    *,
    rhs_label_suffix: str = "-1",
) -> tuple[list[ET.Element], list[ET.Element], list[str]]:
    """
    Build interleaved <Part> and score-level <Staff> lists for a unified diff score.

    Uses staff alignment (track name + fingerprint rename heuristic), not raw part index.
    """
    from .alignment import align_staves, build_union_from_alignment

    alignment = align_staves(score1, score2)
    return build_union_from_alignment(
        score1, score2, alignment, rhs_label_suffix=rhs_label_suffix
    )


def install_union_layout_into_score(
    score: ET.Element,
    union_parts: list[ET.Element],
    union_staves: list[ET.Element],
) -> None:
    """Replace score <Part> / <Staff> children and assign consecutive matching IDs."""
    list_score = list(score)
    part_first_index = -1
    staff_first_index = -1
    parts_to_delete: list[ET.Element] = []

    for i, elem in enumerate(list_score):
        if elem.tag == "Part":
            if part_first_index == -1:
                part_first_index = i
            parts_to_delete.append(elem)
        elif elem.tag == "Staff":
            if staff_first_index == -1:
                staff_first_index = i
            score.remove(elem)

    if part_first_index == -1 or staff_first_index == -1:
        raise ValueError("Score is missing <Part> or <Staff> elements")

    next_staff_id = 1
    for part in union_parts:
        for stub in part.findall("Staff"):
            stub.attrib["id"] = str(next_staff_id)
            next_staff_id += 1

    if next_staff_id - 1 != len(union_staves):
        raise ValueError(
            f"Staff ID assignment mismatch: {next_staff_id - 1} stubs vs "
            f"{len(union_staves)} staves"
        )

    for staff_id, staff in enumerate(union_staves, start=1):
        staff.attrib["id"] = str(staff_id)

    num_staves = len(union_staves)
    for staff in reversed(union_staves):
        score.insert(staff_first_index, staff)

    for part in parts_to_delete:
        score.remove(part)

    num_parts = len(union_parts)
    for part_id, part in enumerate(union_parts, start=1):
        part.attrib["id"] = str(part_id)

    for part in reversed(union_parts):
        score.insert(part_first_index, part)


def _make_highlight_begin(rgb: tuple[int, int, int], num_measures:int = 1) -> ET.Element:
    spanner = ET.Element("Spanner")
    spanner.attrib["type"] = "TextLine"
    textLine = ET.SubElement(spanner, "TextLine")
    color = ET.SubElement(textLine, "color")
    color.attrib["r"] = f"{rgb[0]}"
    color.attrib["g"] = f"{rgb[1]}"
    color.attrib["b"] = f"{rgb[2]}"
    color.attrib["a"] = f"{ALPHA_VALUE}"
    diagonal = ET.SubElement(textLine, "diagonal")
    diagonal.text = "1"
    lineWidth = ET.SubElement(textLine, "lineWidth")
    lineWidth.text = "5"

    segment = ET.SubElement(textLine, "Segment")
    subtype = ET.SubElement(segment, "subtype")
    subtype.text = "0"
    offset = ET.SubElement(segment, "offset")
    offset.attrib["x"] = "0"
    offset.attrib["y"] = "2.3"
    off2 = ET.SubElement(segment, "off2")
    off2.attrib["x"] = "0"
    off2.attrib["y"] = "0"

    minDistance = ET.SubElement(segment, "minDistance")
    minDistance.text = "-999"
    innerColor = ET.SubElement(segment, "color")
    innerColor.attrib["r"] = f"{rgb[0]}"
    innerColor.attrib["g"] = f"{rgb[1]}"
    innerColor.attrib["b"] = f"{rgb[2]}"
    innerColor.attrib["a"] = f"{ALPHA_VALUE}"

    nextElem = ET.SubElement(spanner, "next")
    location = ET.SubElement(nextElem, "location")
    measures = ET.SubElement(location, "measures")
    measures.text = f"{num_measures}"

    return spanner
    
def _make_highlight_end(num_measures:int = 1):
    spanner = ET.Element("Spanner")
    spanner.attrib["type"] = "TextLine"
    prevElem = ET.SubElement(spanner, "prev")
    location = ET.SubElement(prevElem, "location")
    measures = ET.SubElement(location, "measures")
    measures.text = f"-{num_measures}"

    return spanner

def _make_alt_highlight_end():
    return ET.fromstring(
"""
<Spanner type="TextLine">
    <prev>
        <location>
        <fractions>-1/1</fractions>
        </location>
        </prev>
    </Spanner>
"""
    )

def make_highlight_end_empty_measure(duration: str = "4/4"):
    m = _make_empty_measure(duration)
    voice = m.find("voice")
    assert voice is not None
    voice.insert(0, _make_highlight_end())
    return m

def highlight_measure(color: tuple[int, int, int],  measure: ET.Element, next_measure: ET.Element|None = None) -> ET.Element:
    voice = measure.find("voice")
    assert voice is not None
    if voice[0].tag == "Spanner":
        voice.insert(1, _make_highlight_end())
    else:
        voice.insert(0, _make_highlight_begin(color))

    if next_measure is not None:
        next_measure.find("voice").insert(0, _make_highlight_end())
    else:
        voice.insert(-1, _make_alt_highlight_end())
           

    return measure