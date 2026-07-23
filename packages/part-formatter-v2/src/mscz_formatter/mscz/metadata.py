"""Score metaTags and first-page VBox header text (ported from part-formatter v1)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from logging import getLogger

LOGGER = getLogger("mscz_formatter")

CONDUCTOR_SCORE_PART_NAME = "CONDUCTOR SCORE"


def set_score_properties(score: ET.Element, properties: dict[str, str | None]) -> None:
    """Create or update ``<metaTag name="...">`` children on a ``<Score>`` element."""
    existing_meta = score.findall("metaTag")
    if existing_meta:
        insert_index = list(score).index(existing_meta[-1]) + 1
    else:
        insert_index = 0

    for key, value in properties.items():
        if value is None:
            continue
        text = str(value)
        tag = score.find(f"metaTag[@name='{key}']")
        if tag is not None:
            tag.text = text
        else:
            new_tag = ET.Element("metaTag")
            new_tag.set("name", key)
            new_tag.text = text
            score.insert(insert_index, new_tag)
            insert_index += 1


def _make_show_number_text(show_number: str) -> ET.Element:
    txt = ET.Element("Text")
    style = ET.SubElement(txt, "style")
    style.text = "user_2"
    text = ET.SubElement(txt, "text")
    text.text = show_number
    return txt


def _make_show_title_text(show_title: str) -> ET.Element:
    txt = ET.Element("Text")
    style = ET.SubElement(txt, "style")
    style.text = "user_3"
    text = ET.SubElement(txt, "text")
    text.text = show_title
    return txt


def _make_part_name_text(part_name: str) -> ET.Element:
    txt = ET.Element("Text")
    style = ET.SubElement(txt, "style")
    style.text = "instrument_excerpt"
    text = ET.SubElement(txt, "text")
    text.text = part_name
    return txt


def add_broadway_header(staff: ET.Element, show_number: str, show_title: str) -> None:
    """Append MvtNo / MvtTitle text to the first title VBox on ``staff``."""
    for elem in staff:
        if elem.tag == "VBox":
            elem.append(_make_show_number_text(show_number))
            elem.append(_make_show_title_text(show_title))
            return


def add_part_name(
    staff: ET.Element, part_name: str = CONDUCTOR_SCORE_PART_NAME
) -> None:
    """
    Ensure the first title VBox has an ``instrument_excerpt`` part-name text.

    Leaves existing ``instrument_excerpt`` text alone (typical for excerpts that
    MuseScore already labeled). Defaults to ``CONDUCTOR SCORE`` for the root score.
    """
    for elem in staff:
        if elem.tag == "VBox":
            for child in elem.findall("Text"):
                style = child.find("style")
                if style is not None and style.text == "instrument_excerpt":
                    return
            elem.append(_make_part_name_text(part_name))
            return


def apply_metadata_and_headers_to_mscx(
    mscx_path: str,
    *,
    show_title: str = "",
    show_number: str = "",
    version_num: str = "",
    work_title: str = "",
    composer: str | None = None,
    arranger: str | None = None,
    apply_score_metadata: bool = True,
    apply_broadway_vbox_header: bool = True,
    apply_part_name_in_header: bool = True,
    is_broadway: bool = False,
) -> None:
    """
    Write metaTags and optional VBox header texts into one ``.mscx`` file.

    Safe to call when layout is skipped (metadata-only export).
    """
    tree = ET.parse(mscx_path)
    root = tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError(f"No <Score> tag found in {mscx_path}")

    if apply_score_metadata:
        props: dict[str, str | None] = {
            "albumTitle": show_title or "",
            "trackNum": show_number or "",
            "versionNum": version_num or "",
        }
        work = (work_title or "").strip()
        if work:
            props["workTitle"] = work
        if composer is not None and str(composer).strip():
            props["composer"] = str(composer).strip()
        if arranger is not None and str(arranger).strip():
            props["arranger"] = str(arranger).strip()
        set_score_properties(score, props)

    staff = score.find("Staff")
    if staff is not None:
        if apply_broadway_vbox_header and is_broadway:
            add_broadway_header(staff, show_number or "", show_title or "")
        if apply_part_name_in_header:
            add_part_name(staff)
    else:
        LOGGER.warning("No <Staff> in %s; skipping VBox header updates", mscx_path)

    with open(mscx_path, "wb") as f:
        ET.indent(tree, space="  ", level=0)
        tree.write(f, encoding="utf-8", xml_declaration=True)
