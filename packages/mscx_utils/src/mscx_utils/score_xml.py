"""Small helpers for MuseScore .mscx XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def load_score_element(mscx_path: str) -> ET.Element:
    tree = ET.parse(mscx_path)
    score = tree.getroot().find("Score")
    if score is None:
        raise ValueError(f"No <Score> in {mscx_path}")
    return score
