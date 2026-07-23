"""Inspect / mutate score metadata inside an unpacked MSCX."""

from typing import TypedDict
import xml.etree.ElementTree as ET


class ScoreInfo(TypedDict):
    title: str
    subtitle: str
    composer: str
    lyricist: str | None
    instrument_excerpt: str
    user_2: str
    user_3: str
    meta_arranger: str
    meta_composer: str
    meta_subtitle: str
    meta_workTitle: str
    num_instruments: int
    num_staves: int
    time_signatures: list[str]


TITLE_BOX_PROPERTIES = [
    "title",
    "subtitle",
    "composer",
    "lyricist",
]
META_PROPERTIES = ["arranger", "composer", "workTitle", "subtitle"]


def get_properties_from_title_box(score: ET.Element) -> dict[str, str]:
    staff = score.find("Staff")
    assert staff is not None, "Couldn't find staff -- malformed mscx file"
    vbox = staff.find("VBox")
    if vbox is None:
        return {}

    res: dict[str, str] = {}
    for text_elem in vbox.findall("Text"):
        style = text_elem.find("style")
        text = text_elem.find("text")
        if style is not None and text is not None and style.text is not None:
            res[style.text] = text.text or ""
    return res


def get_score_properties_from_meta(score: ET.Element) -> dict[str, str]:
    res: dict[str, str] = {}
    for tag in score.findall("metaTag"):
        name = tag.attrib.get("name")
        if name in META_PROPERTIES:
            res[f"meta_{name}"] = tag.text or ""
    return res


def get_num_staves(score: ET.Element) -> int:
    return len(score.findall("Staff"))


def get_num_instruments(score: ET.Element) -> int:
    return len(score.findall("Part"))


def get_time_signatures(score: ET.Element) -> list[str]:
    staff = score.find("Staff")
    assert staff is not None, "Couldn't find staff -- malformed mscx file"
    res: list[str] = []
    for measure in staff.findall("Measure"):
        voice = measure.find("voice")
        if voice is None:
            continue
        time_sig = voice.find("TimeSig")
        if time_sig is None:
            continue
        n = time_sig.find("sigN")
        d = time_sig.find("sigD")
        if n is not None and d is not None and n.text and d.text:
            res.append(f"{n.text}/{d.text}")
    return res


def _set_staff_spacing(style_file_txt: str, value: str) -> str:
    return style_file_txt.replace("DIVISI:staff_spacing", value)


def set_style_params(style_file_txt: str, **kwargs) -> str:
    if "staff_spacing" in kwargs:
        style_file_txt = _set_staff_spacing(
            style_file_txt, str(kwargs["staff_spacing"])
        )
    else:
        style_file_txt = _set_staff_spacing(style_file_txt, "1.74978")
    return style_file_txt


def get_all_properties(score: ET.Element) -> ScoreInfo:
    res = get_properties_from_title_box(score) | get_score_properties_from_meta(score)
    res["num_instruments"] = get_num_instruments(score)
    res["num_staves"] = get_num_staves(score)
    res["time_signatures"] = get_time_signatures(score)
    return res  # type: ignore[return-value]
