from dataclasses import dataclass
import xml.etree.ElementTree as ET

MAX_LINE_WIDTH = 900000 #idk what it acc is
MAX_PAGE_HEIGHT = 1000 # idk
TITLE_BOX_OFFSET = 1000 # idk

@dataclass
class SourceMeasure:
    # Maps to a mscx measure in the list
    num: int
    hash_key: int

    is_mm_rest_span: bool = False
    is_hidden_by_mm_rest: bool = False
    mm_rest_count: int | None = None

    # TODO: Could these be properties?
    @classmethod
    def get_has_double_bar(cls, m: ET.Element):
        return m.find(".//BarLine") is not None

    @classmethod
    def get_has_rehearsal_mark(cls, m: ET.Element):
        return m.find(".//RehearsalMark") is not None

    @classmethod
    def get_has_line_break(cls, m: ET.Element):
        return m.find(".//LayoutBreak") is not None



@dataclass
class RenderedMeasure:
    num: int

    # dont care about x and y, just sx and sy
    width: float
    height: float

    source_measure_hash: int
    source_measure: SourceMeasure # do we need this

    # line break props
    has_double_bar: bool
    has_existing_line_break: bool
    has_rehearsal_mark: bool

    is_mm_rest: bool
    #only if is_mm_rest is true
    # hashes of all the measures inside the mm rest measure
    mm_rest_hashes: list[int]
    mm_rest_span: int | None = None


@dataclass
class Line:
    measures: list[RenderedMeasure]

    @property
    def width(self):
        return sum(m.width for m in self.measures)

    @property
    def height(self):
        return max(m.height for m in self.measures)

    def is_valid(self):
        #use "is_valid" for balancing
        return self.width <= MAX_LINE_WIDTH
    
@dataclass
class Page:
    lines: list[Line]

    # First pages have the title box which takes up more vertical space
    is_first_page: bool

    @property
    def height(self):
        return sum(l.height for l in self.lines)

    def is_valid(self):
        offset = 0
        if self.is_first_page:
            offset = TITLE_BOX_OFFSET
        return (self.height + offset) <= MAX_PAGE_HEIGHT