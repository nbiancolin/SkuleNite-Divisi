# musescore-score-diff
Python package to visually compare two versions of the same score, and show their differences


Inspired by Greg Chapman and Francesco Fortino's "Music-score-diff" -- specialized for musescore files

NOTE: This project is not actively being maintained. I took this MVP and applied it to my main project, Divisi App. The more up to date code exists there. 
(It was too much work to have these all be microservices, so they are all existing as one big monolith)

# General Flow

Compute Diff of 2 scores (ie. which measures are different) using the same algorithm (backtracing and lfs) that git uses when computing diffs

then, create a new score that has a duplicate copy of each staff from score1 and score 2 (so, a merged score)
- the second staff (from score2) will be empty if the measure is uncanged, but if the measure isc hanged in any way, the measure from staff1 is turned red, and the measure from staff2 is turned green

== OLD ==

## General Idea
Will need both files in memory, hereinafter refered to as "score1" (old version) and "score2" (new version)

create a new score to show diffs on: "diff-score" that is a copy of "score1"
- copy over staves from score2 into `diff-score`, ideally next to its corresponding one (for score 2, have the staff be names `<staff>-1`).
then, for each staff pair (`<staff>` and `<staff>-1`):
- if one of the two is missing, the entire staff was added. Highlight the whole thing green/red somehow (indicate that the part was either created in this version or deleted in this version)
- if they both exist, go through each measure one at a time.
  - MVP: If a difference is found, highlight the entire measure red (old version) and green (new version) to indicate there was a difference
  - V2: Id a difference is found, mark the measure as changed (somehow, yellow?) go through the measure, and colour the individual elements to be red/green respectively
- In any case, mark that the instrument was changed
- at the end, for all changed instruments, create a new "part" for it containing both of the staves, label it `diff-<staff>`, this will be used to view the differences.
- Finally, save this new `diff-score` as `diff-<score-name>` and tell the user it has been done

(another celery task can export it, or user can do it themselves)


### steps for coloring notes / rests in musescore

add tag: `<color r="242" g="102" b="34" a="255"/>` to note

If its a rest or a barline, it can be inserted at index 1, notes are different for some reason

### Steps for highlighting measures:

Add tag to top ov voice (start of measures to be highlighted):
```
<Spanner type="TextLine">
  <TextLine>
    <eid>icWAADvE7ZE_UNlVmVRZvkP</eid>
    <linkedMain/>
    <diagonal>0</diagonal>
    <lineWidth>5</lineWidth>
    <color r="242" g="102" b="34" a="100"/>
    <Segment>
      <subtype>0</subtype>
      <offset x="0" y="2"/>
      <off2 x="0" y="0"/>
      <minDistance>-999</minDistance>
      <eid>nblchKlbnaD_7SJXnVEKpAF</eid>
      </Segment>
    </TextLine>
  <next>
    <location>
      <measures>1</measures>
      </location>
    </next>
  </Spanner>
```

measures is num measures the line lasts

Add tag to measure AFTER last measure to be highlighted
```
<Spanner type="TextLine">
  <prev>
    <location>
      <measures>-1</measures>
      </location>
    </prev>
  </Spanner>
```

NB Note:
- Maybe, instead of mapping by conductor score, we map by parts -- create a new part with diff score and process it that way

To hide staff:
`<cutaway>1</cutaway>`

### Specs for musicXML:


`<score-part>` tags dictate how many different parts there are
`part` tags dictate the different parts (staves I assume?)
- `measure` tags all in parts, 
