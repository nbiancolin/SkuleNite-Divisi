from dataclasses import dataclass
import xml.etree.ElementTree as ET

# MuseScore .mpos sx/sy are in the same units as layout positions.
# Across letter-size part systems in the e2e fixtures, a full system content
# width lands at ~105392 (pageWidth 8.5" minus margins). Using a much larger
# placeholder (900000) meant Line.is_valid() never rejected overfull lines.
MAX_LINE_WIDTH = 112500
# Multi-measure % repeats render tighter than the sum of their .mpos boxes;
# treat the group as this fraction of the raw summed width when packing.
MEASURE_REPEAT_WIDTH_FACTOR = 0.85
# Printable page height in .mpos units (letter 11" minus typical margins).
MAX_PAGE_HEIGHT = 120000
# Extra first-page space for title/composer: first-system y is ~14k higher
# than on later pages in broadway part fixtures (stars/bows/breathe).
TITLE_BOX_OFFSET = 14000
# .mpos `sy` is content bbox only. Pagination must add min system distance
# (broadway minSystemDistance=8.5 spatium; spatium ≈ 1000 .mpos units).
SPATIUM_MPOS_UNITS = 1000
MIN_SYSTEM_DISTANCE_SPATIA = 8.5
SYSTEM_DISTANCE = int(MIN_SYSTEM_DISTANCE_SPATIA * SPATIUM_MPOS_UNITS)

@dataclass
class SourceMeasure:
    # Maps to a mscx measure in the list
    num: int
    hash_key: int

    # If the measure is not a MM rest but it is a single bar of rest
    is_rest: bool

    is_mm_rest_span: bool = False
    is_hidden_by_mm_rest: bool = False
    mm_rest_count: int | None = None

    # Multi-measure % repeat (e.g. 4-bar): members share span N and index 1..N.
    # Only set for N >= 2; single-bar repeats are left unset.
    measure_repeat_span: int | None = None
    measure_repeat_index: int | None = None

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

    @classmethod
    def get_outgoing_slur_or_tie_span(cls, m: ET.Element) -> int:
        """
        Largest number of measures a Slur/Tie Spanner continues past this bar.

        MuseScore encodes cross-bar ties/slurs with
        ``<next><location><measures>N</measures>…`` where N >= 1.
        Same-bar spanners only have ``<fractions>`` and return 0.
        """
        max_span = 0
        for spanner in m.findall(".//Spanner"):
            if spanner.get("type") not in ("Slur", "Tie"):
                continue
            measures_el = spanner.find("./next/location/measures")
            if measures_el is None or not measures_el.text:
                continue
            span = int(measures_el.text)
            if span > max_span:
                max_span = span
        return max_span



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
    # Only if is_mm_rest: hashes of the N underlying MSCX measures covered by
    # the synthetic multi-measure rest (leading rest + N-1 trailing), in order.
    mm_rest_hashes: list[int]
    mm_rest_span: int | None = None
    # True when a slur/tie continues from this measure into the next;
    # used to discourage line breaks across the barline.
    has_slur_or_tie_into_next: bool = False

    # Multi-measure % repeat membership (copied from SourceMeasure).
    measure_repeat_span: int | None = None
    measure_repeat_index: int | None = None

    @property
    def is_rest(self) -> bool:
        return self.source_measure.is_rest

    @property
    def continues_measure_repeat(self) -> bool:
        """True if ending a line here would split a multi-measure % repeat."""
        return (
            self.measure_repeat_span is not None
            and self.measure_repeat_index is not None
            and self.measure_repeat_index < self.measure_repeat_span
        )



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
        """Vertical advance for this system: content bbox + min system distance."""
        if not self.measures:
            return 0.0
        content = max(m.height for m in self.measures)
        return content + SYSTEM_DISTANCE

    def is_valid(self):
        #use "is_valid" for balancing
        return self.width <= MAX_LINE_WIDTH

    def add_measure(self, m: RenderedMeasure):
        self.measures.append(m)
        self.rm_count += 1
        self.c_count += m.mm_rest_span if m.is_mm_rest else 1 # noqa
        
@dataclass
class Page:
    lines: list[Line]

    # First pages have the title box which takes up more vertical space
    is_first_page: bool

    # Intentionally empty odd page (full-page VBox + "V.S.") after a good
    # rest on the facing even page, so the player can turn during the rest.
    is_blank_vs: bool = False

    @property
    def height(self):
        if self.is_blank_vs:
            return MAX_PAGE_HEIGHT
        res = sum(l.height for l in self.lines)
        return res + TITLE_BOX_OFFSET if self.is_first_page else res
        

    def is_valid(self):
        if self.is_blank_vs:
            return not self.lines
        offset = 0
        if self.is_first_page:
            offset = TITLE_BOX_OFFSET
        return (self.height + offset) <= MAX_PAGE_HEIGHT