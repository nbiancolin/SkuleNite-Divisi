# Part Formatter v2

The current part formatter is pretty solid but the line / page break functionality is not quite there yet. 
The issue with this is that there is no real good way to "see" what the page looks like.
- and theres no good way to "force" a layout to be exactly th way that we want it to



IDEA 1: Can we get the "size" of each measure from musescore somehow? 

We can! using `.mpos` file to determine the width of each measure


MPOS structure:
```xml
<score>
    <elements>
        <element id="0", x=, sx=, y=, sy=, page=></element>
    </elements>
</score>
```
Each element corresponds to a visible measure. 
- we need to incorporate this into our structure

dataclass structure

phase 1: generate measure classes
phase 2: generate "lines" and "pages" (apply measure line break formatting)
phase 3: apply the phase 2 formatting to the measures 



## Phase 1: Load in measures
- generate a dict of the ET.Element measures, where the key is the "hash" of that measyre
- Then, generate a Measure class for each of the elements in the (ordered) list, and store the hash of the original measure on the class (so we can find it later)


Generate these from the `mscx`
```py
# map of raw XML measures, keyed by their hash
source_measures_by_hash: dict(str, ET.Element) 

# we need this for mapping "RenderedMeasures" to the ET.Element measures
@dataclass
class SourceMeasure:
    # Maps to a mscx measure in the list
    num: int
    hash_key: str

    is_mm_rest_span: bool = False
    is_hidden_by_mm_rest: bool = False
    mm_rest_count: int | None = None

```

Generate an ordered list of these from the `mpos`
```py
@dataclass
class RenderedMeasure:
    num: int

    # dont care about x and y, just sx and sy
    width: float
    height: float

    source_measure_hash: str
    source_measure: SourceMeasure # do we need this

    is_mm_rest: bool = False
    #only if is_mm_rest is true
    # hashes of all the measures inside the mm rest measure
    mm_rest_hashes: list[str]
    mm_rest_span: int = 1

    # line break props
    has_double_bar: bool
    has_existing_line_break: bool
    has_rehearsal_mark: bool

```


## Part 2: Apply processing

Want to build "Lines"

```py

MAX_LINE_WIDTH = 900000 #idk what it acc is

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


```


These lines then belong to pages
```py

MAX_PAGE_HEIGHT = 1000 # idk
TITLE BOX_OFFSET = 1000 # idk

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

```

With these dataclasses, we take the ordered RenderedMeasures list, and start making "Lines" of it. Apply the formatting rules in [formatting-rules.md](./formatting-rules.md#line-breaks) under the `Line Breaks` section to see how we should be building lines, and `Page Breaks` for how we should be building pages


## Part 3: Put it all back together

Now that we have these Page and Line classes, we can go backwards and update the mscx file to have line breaks as specified by our representation. and with our "is_valid" we know that these will fit!




TODO before V1 (Delete this)
- Make VS text centered and nicer
- add back rule about multiple MM rests on a single line is allowed
- test w fight!


---


# OLD

## phase 1:
- generate a dict of the ET.Element measures, where the key is the "hash" of that measyre
- Then, generate a Measure class for each of the elements in the (ordered) list, and store the hash of the original measure on the class (so we can find it later)


Then were done with the mscx part!

The mscz part (styles, etc) is the same as the existing part formatter!

```py
@dataclass(frozen=True)
class Measure:
    is_mm_rest: bool
    num: int # measure number
    
    x_sz: int
    y_sz: int

    original_measure_hash: str
```

## phase 2:

Build "Lines":


** Tweak the below so that it matches how I do engraving **

> Engraving Rules:
>
> ** ONLY APPLY THE LINE BREAK STUFF TO PARTS! **
>
> - double bar lines at every rehearsal mark
> - line breaks at every double bar (unless there is a slur across the barline of said rehearsal mark)
> - `mpl` (measures per line) is one of { 4, 6, }
> - `mpl` for regular line breaks
> - balancing somehow

Build "Pages"
> pass

```py
class Line:
    measures: list[Measure]

    @property
    def y_sz(self):
        return max([m.y_sz for m in self.measures])


    def is_valid():
        pass # check x_sz of line to ensure its fine

class Page:
    def lines: list[Line]

    def is_valid():
        pass # check y_sz of lines
```

## Phase 3:
- go back from the lines and pages, using the hashes of the original measures, update the xml to have the breaks