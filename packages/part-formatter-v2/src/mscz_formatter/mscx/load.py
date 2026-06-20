"""
Code to load mscx files into memory and return the dataclasses
"""

from typing import TypedDict
import xml.etree.ElementTree as ET

from mscz_formatter.mscx.models import SourceMeasure, RenderedMeasure


class MusescoreFileData(TypedDict):
    measures_by_hash: dict[int, ET.Element]
    source_measures: list[SourceMeasure]
    rendered_measures: list[RenderedMeasure]


def _load_xml_file(path: str) -> ET.Element:
    parser = ET.XMLParser()
    tree = ET.parse(path, parser)
    return tree.getroot()


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


def load_mscx_file(mscx_path: str) -> tuple[dict[int, ET.Element], list[SourceMeasure]]:
    """
    Load in mscx file, return list of measures
    """
    root = _load_xml_file(mscx_path)
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    staves = score.findall("Staff")
    staff = staves[0]  # noqa  -- only add layout breaks to the first staff

    ordered_xml_measures = list(staff.findall("Measure"))
    ordered_source_measures: list[SourceMeasure] = []
    measure_num = 1
    remaining_mm_rest_measures = 0

    for m in ordered_xml_measures:
        mm_rest_len = measure_is_mm_rest_start(m)
        is_mm_rest_span = mm_rest_len != 0
        if is_mm_rest_span:
            remaining_mm_rest_measures = mm_rest_len

        is_hidden_by_mm_rest = remaining_mm_rest_measures > 0 and not is_mm_rest_span

        ordered_source_measures.append(
            SourceMeasure(
                num=measure_num,
                hash_key=hash(m),
                is_mm_rest_span=is_mm_rest_span,
                is_hidden_by_mm_rest=is_hidden_by_mm_rest,
                mm_rest_count=mm_rest_len if is_mm_rest_span else None,
            )
        )

        if not is_mm_rest_span and not is_hidden_by_mm_rest:
            measure_num += 1

        if remaining_mm_rest_measures > 0:
            remaining_mm_rest_measures -= 1
            if remaining_mm_rest_measures == 0:
                measure_num += 1

    measures_by_hash = {hash(m): m for m in ordered_xml_measures}
    return measures_by_hash, ordered_source_measures


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

        if is_mm_rest:
            idx = source_measure_idx + 1
            while idx < len(ordered_source_measures) and ordered_source_measures[idx].is_hidden_by_mm_rest:
                mm_rest_hashes.append(ordered_source_measures[idx].hash_key)
                idx += 1

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

        source_measure_idx += 1 + len(mm_rest_hashes)

    return rendered_measures


def load_in(mscx_path: str, mpos_path: str) -> MusescoreFileData:
    measures_by_hash, ordered_source_measures = load_mscx_file(mscx_path)
    rendered_measures = load_mpos_file(mpos_path, measures_by_hash, ordered_source_measures)
    return MusescoreFileData(
        measures_by_hash=measures_by_hash,
        source_measures=ordered_source_measures,
        rendered_measures=rendered_measures,
    )
