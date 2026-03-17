# musescore-part-formatter-poc
POC for programmatically formatting musescore parts

To run tests, need to manually build your code for the tests to be able to find it
> TODO: Is this something I did wrong? or is this just how it works?

```
pip install -e .
```


Current Project: Inspecting a score, and getting its properties (from the title box, and meta properties)
by-project: Using these inspected values to format the score intelligently
by-by project: using different nmpl's 

TODO: last test: get all part names of all parts in score


Notes about the Musescore Uncompressed (XML Based) File Format:
- MM Rests appear to have changed?
  - It seems that now, for a MM rest of length 4, there are 5 measures ??
  - one rest measure BEFORE the MM rest, plus x many after



=== OLD OLD =====

Usage:
Requires Python 3.11 (I think)
```
python new_prog_part_formatter.py <path to mscz file>
```
Also works on individual parts (WIP)
```
python new_prog_part_formatter.py <path to mscx file>
```

> NOTE: I am gonna refactor this eventually. Putting it into the Divisi Website, once its refactored and fixed there, I'll update this repo



Currently Does:
- Adds line breaks at rehearsal marks
- For regular stuff, every 4 - 6 bars of music, add a line break. When a rehearsal mark / Line Break is encounterd, reset the count (ie, leave it on a new line)
- If there is the scenario: (MM Repeat) <Rehearsal Mark>[LineBreak] (MM Repeat)<Rehearsal Mark>[LineBreak] -- there should only be one line break
  - In words: If there is a lineBreak added to a MultiMeasureRest, and then another line break added to a multimeasure rest, remove the initial one, only keep the second one
  - BUT: IF its is one mutimeasure rest and then notes, add the line break

In progress
- If right after a rehearsal mark, there is a multimeasure rest and then a measure with notes: (goal: want an even # of measures on line)
  - count how many measures there are until either the next rehearsal mark or next mltimeasre rest
- If a slur goes across a barline (and there is a multimeasure rest after it), add the linebreak to the measure itself instead of the one before





==OLD==

Things it needs to do:
- Add the text in a consistent spot according to data in database (Number, Show Title)
- Add double bar lines at rehearsal marks
- Drum Parts should add the text for long and broken up slashes
- Add Line Breaks (LLM?)
- For adding styles, can literally just "replace" the existing file
- 
- 
