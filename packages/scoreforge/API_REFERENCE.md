# ScoreForge API Reference

This document describes all functions and classes that are part of the public API and can be used by external programs.

## Installation

```python
import scoreforge
# or
from scoreforge import Score, parse_score, merge_scores, ...
```

## Models

All model classes are available for type hints and direct instantiation:

- **`Score`**: Top-level container for a musical score
  - `parts: List[Part]` - List of parts in the score
  - `score_id: Optional[str]` - Optional identifier for the score

- **`Part`**: Represents a single part/instrument in the score
  - `part_id: str` - Unique identifier for the part
  - `measures: List[Measure]` - List of measures in this part

- **`Measure`**: Represents a single measure
  - `number: int` - Measure number (1-indexed)
  - `events: List[Event]` - List of musical events (notes, rests, dynamics)
  - `key_sig: Optional[KeySig]` - Optional key signature
  - `time_sig: Optional[TimeSig]` - Optional time signature
  - `irregular: Optional[float]` - Optional irregular measure length

- **`Note`**: Represents a musical note
  - `pitch: str` - Pitch in format 'NoteOctave' (e.g., 'C4', 'C#4')
  - `duration: float` - Base duration (without dots)
  - `dots: int` - Number of augmentation dots (0, 1, or 2)
  - `slur_start: Optional[SlurStart]` - Optional slur start marker
  - `slur_end: Optional[SlurEnd]` - Optional slur end marker
  - `tie_start: Optional[TieStart]` - Optional tie start marker
  - `tie_end: Optional[TieEnd]` - Optional tie end marker

- **`Rest`**: Represents a rest
  - `duration: float` - Base duration (without dots)
  - `dots: int` - Number of augmentation dots (0, 1, or 2)

- **`Dynamic`**: Represents a dynamic marking
  - `subtype: str` - Dynamic type (e.g., "p", "f", "mf")

- **`KeySig`**: Represents a key signature
  - `concert_key: int` - Concert key (number of sharps/flats)

- **`TimeSig`**: Represents a time signature
  - `sig_n: int` - Numerator (beats per measure)
  - `sig_d: int` - Denominator (note value for one beat)

- **`Event`**: Union type of `Note | Rest | Dynamic`

## Parsing & Conversion Functions

### `parse_score(tree: ET.ElementTree) -> Score`

Parse an MSCX ElementTree into a Score object.

Extracts all musical content from a MuseScore XML file, including parts, measures, notes, rests, dynamics, key signatures, time signatures, slurs, and ties.

**Parameters:**
- `tree`: ElementTree representing the MSCX file (typically obtained from `extract_mscx()`)

**Returns:**
- `Score` object containing all parsed parts and measures

**Example:**
```python
from scoreforge.io import extract_mscx
from scoreforge.parser import parse_score
from pathlib import Path

tree = extract_mscx(Path("score.mscz"))
score = parse_score(tree)
print(f"Parsed {len(score.parts)} parts")
```

### `score_to_mscx(score: Score) -> ET.ElementTree`

Convert a Score object to an MSCX XML ElementTree.

Creates a minimal MSCX XML structure from a Score object. This creates a basic MuseScore file with musical content but minimal metadata. For preserving full metadata, use the template-based workflow instead.

**Parameters:**
- `score`: Score object to convert

**Returns:**
- `ElementTree` representing the MSCX format, ready to be written to a file using `write_mscz()`

**Note:** This creates a minimal MSCX file. To preserve all metadata from an original file, use the template-based workflow with `merge_measures_into_template()` and `write_mscz_from_template()`.

**Example:**
```python
from scoreforge.serialization import load_score_from_json
from scoreforge.converter import score_to_mscx
from scoreforge.io import write_mscz
from pathlib import Path

score = load_score_from_json(Path("score.json"))
tree = score_to_mscx(score)
write_mscz(tree, Path("output.mscz"))
```

### `extract_mscx(mscz_path: Path) -> ET.ElementTree`

Extract and parse the MSCX file from a MSCZ archive.

MSCZ files are ZIP archives containing an MSCX XML file along with other resources (images, audio, etc.). This function extracts and parses the main MSCX file containing the musical score data.

**Parameters:**
- `mscz_path`: Path to the MSCZ file (or MSCX file - both are supported)

**Returns:**
- `ElementTree` parsed from the MSCX file, ready for parsing with `parse_score()` or other XML operations

**Raises:**
- `ValueError`: If no .mscx file is found in the archive

**Example:**
```python
from pathlib import Path
from scoreforge.io import extract_mscx
from scoreforge.parser import parse_score

tree = extract_mscx(Path("score.mscz"))
score = parse_score(tree)
```

### `write_mscz(tree: ET.ElementTree, out_path: Path) -> None`

Write an ElementTree to a MSCZ file.

Creates a minimal MSCZ archive containing only the MSCX XML file. This is suitable for basic scores but does not preserve metadata files, images, or other resources from the original file.

**Parameters:**
- `tree`: ElementTree representing the MSCX content to write
- `out_path`: Path where the MSCZ file should be written

**Note:** This creates a minimal MSCZ file. To preserve all files from an original MSCZ, use `write_mscz_from_template()` instead.

**Example:**
```python
from scoreforge.converter import score_to_mscx
from scoreforge.io import write_mscz
from pathlib import Path

tree = score_to_mscx(score)
write_mscz(tree, Path("output.mscz"))
```

## Serialization Functions

### `save_canonical(score: Score, path: Path) -> None`

Save a Score object to a canonical JSON file.

Serializes a Score object to the ScoreForge canonical JSON format. This format is designed for version control and text-based diffing, with a structure that minimizes merge conflicts.

The JSON format uses dictionaries keyed by part_id and measure number, making it easy to see changes at the measure level.

**Parameters:**
- `score`: Score object to serialize
- `path`: Path where the JSON file should be written

**Example:**
```python
from scoreforge.parser import parse_score
from scoreforge.io import extract_mscx
from scoreforge.serialization import save_canonical
from pathlib import Path

tree = extract_mscx(Path("score.mscz"))
score = parse_score(tree)
save_canonical(score, Path("score.json"))
```

### `load_score_from_json(path: Path) -> Score`

Load a Score object from a canonical JSON file.

Deserializes a Score object from the ScoreForge canonical JSON format. Supports both the current format (dictionaries) and legacy formats (lists) for backward compatibility.

**Parameters:**
- `path`: Path to the JSON file

**Returns:**
- `Score` object deserialized from the JSON file, ready for conversion to MSCX or merging with other scores

**Example:**
```python
from pathlib import Path
from scoreforge.serialization import load_score_from_json
from scoreforge.converter import score_to_mscx
from scoreforge.io import write_mscz

score = load_score_from_json(Path("score.json"))
tree = score_to_mscx(score)
write_mscz(tree, Path("output.mscz"))
```

## Merging Functions

### `merge_scores(score1: Score, score2: Score) -> Score`

Merge two Score objects based on their canonical form.

This function combines two scores into a single merged score. The merging strategy can be customized based on the specific requirements (e.g., taking the union of parts, merging measures by part_id, handling conflicts, etc.).

The function operates on the canonical representation of scores, making it suitable for merging scores that have been loaded from JSON or parsed from different sources.

**Parameters:**
- `score1`: First Score object to merge
- `score2`: Second Score object to merge

**Returns:**
- A new `Score` object containing the merged content from both input scores. The merged score combines parts and measures from both inputs according to the merging strategy.

**Raises:**
- `MergeConflict`: When the same measure exists in both scores with different content. The exception contains a `conflicts` dictionary mapping `(part_id, measure_number)` to tuples of `(measure1, measure2)`, allowing programmatic access to conflicting measures.

**Note:** This is a placeholder implementation. The actual merging logic should be implemented based on the specific requirements for how scores should be combined. Common strategies include:
- Part-by-part merging: Combine parts with matching part_id
- Measure-by-measure merging: Merge measures within each part
- Union merging: Include all parts from both scores
- Conflict resolution: Handle cases where the same part/measure exists in both scores with different content

**Example:**
```python
from scoreforge.serialization import load_score_from_json
from scoreforge import merge_scores, MergeConflict
from scoreforge.serialization import save_canonical
from pathlib import Path

score1 = load_score_from_json(Path("score1.json"))
score2 = load_score_from_json(Path("score2.json"))

try:
    merged = merge_scores(score1, score2)
    save_canonical(merged, Path("merged.json"))
except MergeConflict as e:
    # Access conflicting measures
    for (part_id, measure_num), (m1, m2) in e.conflicts.items():
        print(f"Conflict in {part_id}, measure {measure_num}")
        print(f"  Score1: {len(m1.events)} events")
        print(f"  Score2: {len(m2.events)} events")
        # Resolve conflict programmatically or prompt user
```

### `MergeConflict`

Exception raised when merging two scores results in conflicts.

This exception contains information about all conflicting measures, allowing the caller to inspect and resolve conflicts programmatically.

**Attributes:**
- `conflicts`: Dictionary mapping `(part_id, measure_number)` tuples to tuples of `(measure_from_score1, measure_from_score2)`. Each conflict represents a measure that exists in both scores with different content.

**Example:**
```python
from scoreforge import merge_scores, MergeConflict

try:
    merged = merge_scores(score1, score2)
except MergeConflict as e:
    # Get all conflicts
    for (part_id, measure_num), (measure1, measure2) in e.conflicts.items():
        print(f"Part '{part_id}', measure {measure_num}:")
        print(f"  From score1: {measure1.events}")
        print(f"  From score2: {measure2.events}")
    
    # Access specific conflict
    if ("P1", 5) in e.conflicts:
        m1, m2 = e.conflicts[("P1", 5)]
        # Resolve this specific conflict
```

## Utility Functions

### `midi_to_pitch(midi: int) -> str`

Convert MIDI note number to pitch string (e.g., 60 -> 'C4').

Converts a MIDI note number to a pitch string representation used in the ScoreForge canonical format. Middle C (MIDI 60) becomes 'C4'.

**Parameters:**
- `midi`: MIDI note number (0-127)

**Returns:**
- Pitch string in format 'NoteOctave' (e.g., 'C4', 'C#4', 'Bb3')

**Example:**
```python
from scoreforge.converter import midi_to_pitch

midi_to_pitch(60)  # Returns 'C4'
midi_to_pitch(61)  # Returns 'C#4'
```

### `pitch_to_midi(pitch: str) -> int`

Convert pitch string to MIDI note number (e.g., 'C4' -> 60).

Converts a pitch string from the ScoreForge canonical format to a MIDI note number. This is the inverse of `midi_to_pitch()`.

**Parameters:**
- `pitch`: Pitch string in format 'NoteOctave' (e.g., 'C4', 'C#4', 'Bb3')

**Returns:**
- MIDI note number (0-127)

**Example:**
```python
from scoreforge.converter import pitch_to_midi

pitch_to_midi('C4')   # Returns 60
pitch_to_midi('C#4')  # Returns 61
```

## Complete Workflow Examples

### Converting MSCZ to JSON

```python
from pathlib import Path
from scoreforge.io import extract_mscx
from scoreforge.parser import parse_score
from scoreforge.serialization import save_canonical

# Load and parse
tree = extract_mscx(Path("input.mscz"))
score = parse_score(tree)

# Save to canonical JSON
save_canonical(score, Path("output.json"))
```

### Converting JSON to MSCZ

```python
from pathlib import Path
from scoreforge.serialization import load_score_from_json
from scoreforge.converter import score_to_mscx
from scoreforge.io import write_mscz

# Load from JSON
score = load_score_from_json(Path("input.json"))

# Convert to MSCX and write
tree = score_to_mscx(score)
write_mscz(tree, Path("output.mscz"))
```

### Merging Two Scores

```python
from pathlib import Path
from scoreforge.serialization import load_score_from_json, save_canonical
from scoreforge import merge_scores

# Load both scores
score1 = load_score_from_json(Path("score1.json"))
score2 = load_score_from_json(Path("score2.json"))

# Merge them
merged = merge_scores(score1, score2)

# Save the result
save_canonical(merged, Path("merged.json"))
```

