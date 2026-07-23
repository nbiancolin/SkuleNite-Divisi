"""Write planned Line / Page breaks back onto MSCX measure elements."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from logging import getLogger

from mscz_formatter.mscx.models import MAX_PAGE_HEIGHT, SPATIUM_MPOS_UNITS, Page, RenderedMeasure

LOGGER = getLogger("mscz_formatter")

# VBox height is in spatium. Match our printable page budget so the frame
# fills the blank odd page after a volti-subito rest.
VS_BLANK_FRAME_HEIGHT_SPATIA = MAX_PAGE_HEIGHT / SPATIUM_MPOS_UNITS


def _make_layout_break(subtype: str) -> ET.Element:
    lb = ET.Element("LayoutBreak")
    st = ET.SubElement(lb, "subtype")
    st.text = subtype
    return lb


def _generate_vs_text() -> ET.Element:
    return ET.fromstring("<b><font size=\"16\"/>V.S.<br/><br/>&gt;&gt;&gt;&gt;&gt;&gt;&gt;</b>")


def _make_vs_blank_frame() -> ET.Element:
    """Full-page vertical frame with V.S. text and a trailing page break."""
    vbox = ET.Element("VBox")
    height = ET.SubElement(vbox, "height")
    height.text = f"{VS_BLANK_FRAME_HEIGHT_SPATIA:g}"
    boxAutoSize = ET.SubElement(vbox, "boxAutoSize")
    boxAutoSize.text = "0"
    text = ET.SubElement(vbox, "Text")
    style = ET.SubElement(text, "style")
    style.text = "frame"
    size = ET.SubElement(text, "size")
    size.text = "16"
    bold = ET.SubElement(text, "bold")
    bold.text = "1"
    align = ET.SubElement(text, "align")
    align.text = "center,baseline"
    position = ET.SubElement(text, "position")
    position.text = "center"
    body = ET.SubElement(text, "text")
    body.append(_generate_vs_text())
    vbox.append(_make_layout_break("page"))
    return vbox


def _is_vs_blank_frame(elem: ET.Element) -> bool:
    if elem.tag != "VBox":
        return False
    text_el = elem.find("./Text/text")
    lb = elem.find("LayoutBreak")
    return (
        text_el is not None
        and (text_el.text or "").strip() == VS_BLANK_TEXT
        and lb is not None
    )


def _insert_before_voice(measure: ET.Element, child: ET.Element) -> None:
    index = 0
    for i, elem in enumerate(measure):
        if elem.tag == "voice":
            index = i
            break
        index = i + 1
    measure.insert(index, child)


def scrub_layout_breaks(staff: ET.Element) -> None:
    for measure in staff.findall("Measure"):
        for lb in list(measure.findall("LayoutBreak")):
            measure.remove(lb)


def scrub_vs_blank_frames(staff: ET.Element) -> None:
    """Remove previously inserted V.S. blank-page frames (not title VBoxes)."""
    for child in list(staff):
        if _is_vs_blank_frame(child):
            staff.remove(child)


def _set_break_on_measure(measure: ET.Element, subtype: str) -> None:
    existing = measure.find("LayoutBreak")
    if existing is not None:
        st = existing.find("subtype")
        if st is None:
            st = ET.SubElement(existing, "subtype")
        st.text = subtype
        return
    _insert_before_voice(measure, _make_layout_break(subtype))


def _break_target_hashes(measure: RenderedMeasure) -> list[int]:
    """
    Hashes of MSCX measures that need the layout break for this RenderedMeasure.

    For a normal bar: just the source measure.
    For an MM rest: both the visible span measure and the last hidden measure
    covered by that rest (MuseScore keeps both in sync).
    """
    hashes = [measure.source_measure_hash]
    if measure.is_mm_rest and measure.mm_rest_hashes:
        hashes.append(measure.mm_rest_hashes[-1])
    return hashes


def _staff_index_of_measure(staff: ET.Element, measure: ET.Element) -> int | None:
    for i, child in enumerate(staff):
        if child is measure:
            return i
    return None


def _insert_vs_blank_after_measure(staff: ET.Element, measure: ET.Element) -> None:
    idx = _staff_index_of_measure(staff, measure)
    if idx is None:
        LOGGER.warning("Could not locate measure for V.S. blank frame; skipping")
        return
    staff.insert(idx + 1, _make_vs_blank_frame())


def apply_pages_to_staff(
    staff: ET.Element,
    pages: list[Page],
    measures_by_hash: dict[int, ET.Element],
) -> None:
    """
    Scrub existing layout breaks, then write line breaks at the end of each line
    and page breaks at the end of each page (except the final page).

    Blank ``is_blank_vs`` pages become a full-page VBox with ``V.S.`` text
    inserted after the preceding page's last measure.

    ``measures_by_hash`` must refer to the same Element objects under ``staff``.
    """
    scrub_vs_blank_frames(staff)
    scrub_layout_breaks(staff)

    for page_idx, page in enumerate(pages):
        if page.is_blank_vs:
            continue

        trailing = pages[page_idx + 1 :]
        is_last_music_page = not any(not p.is_blank_vs for p in trailing)

        for line_idx, line in enumerate(page.lines):
            if not line.measures:
                continue
            last = line.measures[-1]

            is_last_line = line_idx == len(page.lines) - 1
            next_is_blank = (
                is_last_line
                and page_idx + 1 < len(pages)
                and pages[page_idx + 1].is_blank_vs
            )
            if is_last_line and (not is_last_music_page or next_is_blank):
                subtype = "page"
            elif not (is_last_music_page and is_last_line):
                subtype = "line"
            else:
                continue

            target_measure: ET.Element | None = None
            for measure_hash in _break_target_hashes(last):
                measure = measures_by_hash.get(measure_hash)
                if measure is None:
                    LOGGER.warning(
                        "Missing measure for hash %s; skipping layout break",
                        measure_hash,
                    )
                    continue
                _set_break_on_measure(measure, subtype)
                target_measure = measure

            if next_is_blank and target_measure is not None:
                _insert_vs_blank_after_measure(staff, target_measure)


def apply_layout_to_tree(
    tree: ET.ElementTree,
    pages: list[Page],
    measures_by_hash: dict[int, ET.Element],
    mscx_path: str,
) -> None:
    """Mutate ``tree`` in place and write it back to ``mscx_path``."""
    root = tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError(f"No <Score> tag found in {mscx_path}")
    staves = score.findall("Staff")
    if not staves:
        raise ValueError(f"No <Staff> tag found in {mscx_path}")

    apply_pages_to_staff(staves[0], pages, measures_by_hash)

    with open(mscx_path, "wb") as f:
        ET.indent(tree, space="  ", level=0)
        tree.write(f, encoding="utf-8", xml_declaration=True)
