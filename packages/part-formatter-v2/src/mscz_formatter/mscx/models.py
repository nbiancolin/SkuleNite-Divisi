from dataclasses import dataclass
import xml.etree.ElementTree as ET

MAX_LINE_WIDTH = 900000 #idk what it acc is
MAX_PAGE_HEIGHT = 143424 # idk - round this to a nicer number
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

    # How many RenderedMeasures long it is
    rm_count: int

    # How conceptually long the line is (ie, how many bars in that line (counting MM rests))
    c_count: int

    @property
    def width(self):
        return sum(m.width for m in self.measures)

    @property
    def height(self):
        return max(m.height for m in self.measures)

    def is_valid(self):
        #use "is_valid" for balancing
        return self.width <= MAX_LINE_WIDTH
    
    @classmethod
    # def page_turn_quality(cls, line: "Line") -> int:
    #     """
    #     2 - MM rest
    #     1 - 1 measure rest
    #     0 - no rest
    #     """
    #     assert line.measures.__len__() > 0
    #     if line.measures[0].is_mm_rest:
    #         return 2
    #     return 1 if line.


    
    def add_measure(self, m: RenderedMeasure):
        self.measures.append(m)
        self.rm_count += 1
        self.c_count += m.mm_rest_span if m.is_mm_rest else 1 # noqa
        
@dataclass
class Page:
    lines: list[Line]

    # First pages have the title box which takes up more vertical space
    is_first_page: bool

    @property
    def height(self):
        res = sum(l.height for l in self.lines)
        return res + TITLE_BOX_OFFSET if self.is_first_page else res
        

    def is_valid(self):
        offset = 0
        if self.is_first_page:
            offset = TITLE_BOX_OFFSET
        return (self.height + offset) <= MAX_PAGE_HEIGHT