import xml.etree.ElementTree as ET
import hashlib
from enum import Enum

ALPHA_VALUE = 100

class State(Enum):
    UNCHANGED = 1
    MODIFIED = 2
    INSERTED = 3
    REMOVED = 4

# -- Compare Diff Utils --

def _hash_measure(measure: ET.Element) -> str:
    """
    Return a stable hash of the measure's XML content.
    Allows for quick comparison
    """
    raw = ET.tostring(measure, encoding="utf-8")
    # normalize whitespace
    normalized = b"".join(raw.split())
    return hashlib.md5(normalized).hexdigest()

def _sanitize_measure(measure: ET.Element) -> ET.Element:
    """ Remove all the useless (to us) junk from musescore measures"""

    #remove any tag that says "EID"
    #remove any "LinkedMain"
    to_remove = []
    for elem in measure.iter():
        for child in list(elem):
            if child.tag in ("eid", "linkedMain"):
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


def extract_measures(staff: ET.Element) -> list[tuple[int, str, ET.Element]]:
    """Parse uncompressed mcsx and return list of (number, hash, element)."""
    

    measures = []
    score_measures = staff.findall("Measure")
    for i in range(len(score_measures)):
        m = _sanitize_measure(score_measures[i])
        num = i+1
        
        h = _hash_measure(m)
        measures.append((num, h, m))
    return measures


# -- Visualize Diff Utils

def _make_cutaway() -> ET.Element:
    """Create cutaway element (from your existing code)."""
    return ET.fromstring("<cutaway>1</cutaway>")

def _make_empty_measure() -> ET.Element:
    measure = ET.Element("Measure")
    voice = ET.SubElement(measure, "voice")
    rest = ET.SubElement(voice, "Rest")
    durationType = ET.SubElement(rest, "durationType")
    durationType.text = "measure"
    duration = ET.SubElement(rest, "duration")
    duration.text = "4/4"

    return measure

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

def make_highlight_end_empty_measure():
    m = _make_empty_measure()
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