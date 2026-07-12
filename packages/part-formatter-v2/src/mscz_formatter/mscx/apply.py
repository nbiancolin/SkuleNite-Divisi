"""Write planned Line / Page breaks back onto MSCX measure elements."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from logging import getLogger

from mscz_formatter.mscx.models import Page

LOGGER = getLogger("mscz_formatter")


def _make_layout_break(subtype: str) -> ET.Element:
    lb = ET.Element("LayoutBreak")
    st = ET.SubElement(lb, "subtype")
    st.text = subtype
    return lb


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


def _set_break_on_measure(measure: ET.Element, subtype: str) -> None:
    existing = measure.find("LayoutBreak")
    if existing is not None:
        st = existing.find("subtype")
        if st is None:
            st = ET.SubElement(existing, "subtype")
        st.text = subtype
        return
    _insert_before_voice(measure, _make_layout_break(subtype))


def apply_pages_to_staff(
    staff: ET.Element,
    pages: list[Page],
    measures_by_hash: dict[int, ET.Element],
) -> None:
    """
    Scrub existing layout breaks, then write line breaks at the end of each line
    and page breaks at the end of each page (except the final page).

    ``measures_by_hash`` must refer to the same Element objects under ``staff``.
    """
    scrub_layout_breaks(staff)

    for page_idx, page in enumerate(pages):
        is_last_page = page_idx == len(pages) - 1
        for line_idx, line in enumerate(page.lines):
            if not line.measures:
                continue
            last = line.measures[-1]
            measure = measures_by_hash.get(last.source_measure_hash)
            if measure is None:
                LOGGER.warning(
                    "Missing measure for hash %s; skipping layout break",
                    last.source_measure_hash,
                )
                continue

            is_last_line = line_idx == len(page.lines) - 1
            if is_last_line and not is_last_page:
                _set_break_on_measure(measure, "page")
            elif not (is_last_page and is_last_line):
                _set_break_on_measure(measure, "line")


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
