from typing import TypedDict
import shutil
import tempfile
import zipfile
import os

import xml.etree.ElementTree as ET


class ScoreInfo(TypedDict):
    title: str
    subtitle: str
    composer: str
    lyricist: str | None  # I dont think ive ever seen this but you never know
    instrument_excerpt: str  # this is what the part name of the XML file is
    user_2: str  # this is what show number is
    user_3: str  # this is what show title is

    meta_arranger: str
    meta_composer: str
    meta_subtitle: str
    meta_workTitle: str  # (title)

    # READ ONLY PROPERTIES
    num_instruments: int
    num_staves: int
    time_signatures: list[str]  # ['4/4', ... etc]


TITLE_BOX_PROPERTIES = [
    "title",
    "subtitle",
    "composer",
    "lyricist",
]
META_PROPERTIES = ["arranger", "composer", "workTitle", "subtitle"]


def get_properties_from_title_box(score: ET.Element, debug=False) -> dict[str, str]:
    staff = score.find("Staff")
    assert staff is not None, "Couldnt find staff -- malformed mscx file"
    vbox = staff.find("VBox")
    if debug:
        assert vbox is not None, "Couldnt find vbox"
    if vbox is None:
        return {}

    res = {}

    for text_elem in vbox.findall("Text"):
        res[text_elem.find("style").text] = text_elem.find("text").text

    return res


def get_score_properties_from_meta(score: ET.Element) -> dict[str, str]:
    metatags = score.findall("metaTag")
    res = {}
    for tag in metatags:
        if tag.attrib.get("name") in META_PROPERTIES:
            res[f"meta_{tag.attrib.get('name')}"] = tag.text

    return res


def set_title_box_score_properties(
    score: ET.Element, title_properties: dict[str, str], debug=False
) -> None:
    staff = score.find("Staff")
    assert staff is not None, "Couldnt find staff -- malformed mscx file"
    vbox = staff.find("VBox")
    if debug:
        assert vbox is not None, "Couldnt find vbox"
    if vbox is None:
        return

    for text_elem in vbox.findall("Text"):
        provided_text = text_elem.find("style").text
        if provided_text in title_properties:
            text_elem.find("text").text = title_properties[provided_text]


def set_meta_score_properties(score: ET.Element, meta_properties: dict[str, str]):
    score_metatags = score.findall("metaTag")
    for tag in score_metatags:
        if tag_name := tag.attrib.get("name"):
            if tag_name in meta_properties:
                tag.text = meta_properties[tag_name]


def get_num_staves(score: ET.Element) -> int:
    return len(score.findall("Staff"))


def get_num_instruments(score: ET.Element) -> int:
    return len(score.findall("Part"))


def get_time_signatures(score: ET.Element) -> list[str]:
    staff = score.find("Staff")
    assert staff is not None, "Couldnt find staff -- malformed mscx file"
    measures = staff.findall("Measure")
    res = []
    for measure in measures:
        if time_sig := measure.find("voice").find("TimeSig"):
            res.append(f"{time_sig.find('sigN').text}/{time_sig.find('sigD').text}")
    return res


def _set_staff_spacing(style_file_txt: str, value: str) -> str:
    return style_file_txt.replace("DIVISI:staff_spacing", value)


def set_style_params(style_file_txt: str, **kwargs) -> str:
    print("STYLE PARAMS FUNCTION CALLED!")

    if "staff_spacing" in kwargs:
        style_file_txt = _set_staff_spacing(
            style_file_txt, str(kwargs["staff_spacing"])
        )
    else:
        style_file_txt = _set_staff_spacing(style_file_txt, "1.74978")

    # TODO: Other Params
    return style_file_txt


def get_all_properties(score: ET.Element) -> ScoreInfo:
    res = get_properties_from_title_box(score) | get_score_properties_from_meta(score)
    res["num_instruments"] = get_num_instruments(score)
    res["num_staves"] = get_num_staves(score)
    res["time_signatures"] = get_time_signatures(score)

    return res  # type-ignore


def set_all_properties(score: ET.Element, properties: dict[str, str]) -> None:
    meta_properties = {
        k.removeprefix("meta_"): v
        for k, v in properties.items()
        if k.startswith("meta_")
    }

    title_box_properties = {
        k: v for k, v in properties.items() if k in TITLE_BOX_PROPERTIES
    }

    set_meta_score_properties(score, meta_properties)
    set_title_box_score_properties(score, title_box_properties, debug=True)
