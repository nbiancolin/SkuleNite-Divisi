"""MSCX element trees as JSON (stable canonical form), omitting volatile MuseScore ids."""

from __future__ import annotations

import xml.etree.ElementTree as ET

_IGNORE_TAGS = frozenset({"eid", "linkedMain"})


def _local_tag(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def element_to_json(el: ET.Element | None) -> dict | None:
    """Serialize an XML element to a JSON-serializable dict; skip eid and linkedMain."""
    if el is None:
        return None
    tag = _local_tag(el.tag)
    node: dict = {"tag": tag}
    if el.attrib:
        node["attrs"] = dict(el.attrib)
    text = (el.text or "").strip()
    if text:
        node["text"] = text
    children: list[dict] = []
    for ch in el:
        if _local_tag(ch.tag) in _IGNORE_TAGS:
            continue
        children.append(element_to_json(ch))
    if children:
        node["children"] = children
    return node


def json_to_element(data: dict) -> ET.Element:
    """Rebuild an XML element from :func:`element_to_json` output."""
    tag = data["tag"]
    attrs = data.get("attrs") or {}
    el = ET.Element(tag, attrs)
    if "text" in data:
        el.text = data["text"]
    for ch in data.get("children") or []:
        el.append(json_to_element(ch))
    return el
