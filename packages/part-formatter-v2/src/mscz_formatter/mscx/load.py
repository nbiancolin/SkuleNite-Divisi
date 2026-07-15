"""
Code to load mscx files into memory and return the dataclasses
"""

from typing import TypedDict
import xml.etree.ElementTree as ET

from mscz_formatter.mscx.models import SourceMeasure, RenderedMeasure


class MusescoreFileData(TypedDict):
    tree: ET.ElementTree
    measures_by_hash: dict[int, ET.Element]
    source_measures: list[SourceMeasure]
    rendered_measures: list[RenderedMeasure]


def _load_xml_tree(path: str) -> ET.ElementTree:
    return ET.parse(path, ET.XMLParser())


def _load_xml_file(path: str) -> ET.Element:
    return _load_xml_tree(path).getroot()


def measure_is_mm_rest_start(m: ET.Element) -> int:
    """
    Returns the length of the MM rest, and 0 if it is not a MM rest
    """
    len_prop = m.attrib.get("len", None)
    mm_tag = m.find("multiMeasureRest")

    if mm_tag is not None:
        return int(mm_tag.text)
    if len_prop is not None:
        top, bottom = len_prop.split("/")
        res = int(top) / int(bottom)
        assert res.is_integer(), f"MM Rest 'len' property was not a whole number: found {len_prop}"
        return int(res)
    return 0


def _hidden_by_mm_rest_flags(ordered_xml_measures: list[ET.Element]) -> list[bool]:
    """
    MuseScore stores each multi-measure rest as:

      [first underlying rest] [synthetic <multiMeasureRest>N</…>] [N-1 trailing underlyings]

    Only the synthetic measure is drawn; all N underlying bars must be hidden when
    pairing against .mpos elements. Older logic only hid the trailing bars, which
    left the first underlying as a ghost rendered measure (e.g. M2R before M3*(8)R).
    """
    n = len(ordered_xml_measures)
    hidden = [False] * n
    for i, m in enumerate(ordered_xml_measures):
        mm_rest_len = measure_is_mm_rest_start(m)
        if mm_rest_len == 0:
            continue
        if i > 0:
            hidden[i - 1] = True
        for j in range(1, mm_rest_len):
            if i + j < n:
                hidden[i + j] = True
    return hidden


def load_mscx_file(
    mscx_path: str,
) -> tuple[ET.ElementTree, dict[int, ET.Element], list[SourceMeasure]]:
    """
    Load in mscx file, return the parse tree plus measure metadata.
    """
    tree = _load_xml_tree(mscx_path)
    root = tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    staves = score.findall("Staff")
    staff = staves[0]  # noqa  -- only add layout breaks to the first staff

    ordered_xml_measures = list(staff.findall("Measure"))
    hidden_flags = _hidden_by_mm_rest_flags(ordered_xml_measures)
    ordered_source_measures: list[SourceMeasure] = []
    measure_num = 1

    for i, m in enumerate(ordered_xml_measures):
        mm_rest_len = measure_is_mm_rest_start(m)
        is_mm_rest_span = mm_rest_len != 0
        is_hidden_by_mm_rest = hidden_flags[i]

        # is_rest calculation - TODO Check this
        is_rest: bool = False
        m_rests = m.findall("Rest")
        if len(m_rests) == 1 and m_rests[0].attrib["durationType"] == "measure":
            is_rest = True
        else:
            is_rest = False

        ordered_source_measures.append(
            SourceMeasure(
                num=measure_num,
                hash_key=hash(m),
                is_mm_rest_span=is_mm_rest_span,
                is_hidden_by_mm_rest=is_hidden_by_mm_rest,
                mm_rest_count=mm_rest_len if is_mm_rest_span else None,
                is_rest=is_rest
            )
        )

        if is_mm_rest_span:
            measure_num += mm_rest_len
        elif not is_hidden_by_mm_rest:
            measure_num += 1

    measures_by_hash = {hash(m): m for m in ordered_xml_measures}
    return tree, measures_by_hash, ordered_source_measures


def load_mpos_file(
    mpos_path: str,
    measures_by_hash: dict[int, ET.Element],
    ordered_source_measures: list[SourceMeasure],
) -> list[RenderedMeasure]:
    root = _load_xml_file(mpos_path)
    elements = root.find("elements")
    if elements is None:
        raise ValueError("No <elements> tag found in the mpos file.")

    rendered_measures: list[RenderedMeasure] = []
    outgoing_slur_tie_spans: list[int] = []
    source_measure_idx = 0

    for measure_num, elem in enumerate(elements.findall("element")):
        while (
            source_measure_idx < len(ordered_source_measures)
            and ordered_source_measures[source_measure_idx].is_hidden_by_mm_rest
        ):
            source_measure_idx += 1

        if source_measure_idx >= len(ordered_source_measures):
            raise ValueError(
                f"mpos has more rendered measures ({measure_num + 1}) than visible source measures"
            )

        sm = ordered_source_measures[source_measure_idx]
        etm = measures_by_hash[sm.hash_key]
        is_mm_rest = sm.is_mm_rest_span
        mm_rest_hashes: list[int] = []
        following_hidden = 0

        if is_mm_rest:
            # MuseScore: [leading underlying] [synthetic] [N-1 trailing underlyings]
            expected_underlyings = sm.mm_rest_count or 0
            if (
                source_measure_idx > 0
                and ordered_source_measures[source_measure_idx - 1].is_hidden_by_mm_rest
            ):
                mm_rest_hashes.append(
                    ordered_source_measures[source_measure_idx - 1].hash_key
                )
            idx = source_measure_idx + 1
            while (
                len(mm_rest_hashes) < expected_underlyings
                and idx < len(ordered_source_measures)
                and ordered_source_measures[idx].is_hidden_by_mm_rest
            ):
                mm_rest_hashes.append(ordered_source_measures[idx].hash_key)
                following_hidden += 1
                idx += 1

        outgoing_slur_tie_spans.append(
            SourceMeasure.get_outgoing_slur_or_tie_span(etm)
        )
        rendered_measures.append(
            RenderedMeasure(
                num=measure_num,
                width=float(elem.attrib["sx"]),
                height=float(elem.attrib["sy"]),
                source_measure_hash=sm.hash_key,
                source_measure=sm,
                has_double_bar=SourceMeasure.get_has_double_bar(etm),
                has_rehearsal_mark=SourceMeasure.get_has_rehearsal_mark(etm),
                has_existing_line_break=SourceMeasure.get_has_line_break(etm),
                is_mm_rest=is_mm_rest,
                mm_rest_hashes=mm_rest_hashes,
                mm_rest_span=sm.mm_rest_count if is_mm_rest else None,
            )
        )

        # Skip only the synthetic + trailing underlyings; the leading underlying
        # was already passed when we skipped hidden bars into this measure.
        source_measure_idx += 1 + following_hidden

    # Mark every bar a slur/tie still crosses: span=2 starting at i means
    # breaking after i or i+1 both split the spanner.
    for i, span in enumerate(outgoing_slur_tie_spans):
        for j in range(span):
            if i + j < len(rendered_measures):
                rendered_measures[i + j].has_slur_or_tie_into_next = True

    return rendered_measures


def load_in(mscx_path: str, mpos_path: str) -> MusescoreFileData:
    tree, measures_by_hash, ordered_source_measures = load_mscx_file(mscx_path)
    rendered_measures = load_mpos_file(mpos_path, measures_by_hash, ordered_source_measures)
    return MusescoreFileData(
        tree=tree,
        measures_by_hash=measures_by_hash,
        source_measures=ordered_source_measures,
        rendered_measures=rendered_measures,
    )
