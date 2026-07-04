# Formatting Rules


## Line Breaks

- MVP: `mpl` (measures per line) is hard-coded to 6
- (eventually allow for any number)

When building lines we should build them as legibly as possible
What does legible mean:
- **not** cramped (want to spread measures out as much as possible)
- Line breaks in places that make sense
    - (ie, if there is a slur across measures, we should **not** be adding a line break)
    - rehearsal marks should start on new lines wherever possible
    - double bar lines should mark a new line wherever possible


for a given RenderedMeasure:
- if it is a MM rest
    - if the measure starts on a new line:
        - if the next measure is a mm rest:
            don't add a break
        - If the MM rest is a multiple of `mpl`: 
            add a line break
        - else:
            ensure the line "conceptual length" (ie, \delta of measure numbers) is a multiple of `mpl` (or 4 - hard coded value bc 4 is a nice number)
            ie. add a line break to the target measure, then move the iterator to that
    - else (not on a new line):
        - **I actually dont know what to do here..., id probably add a bar before so its on a new line**
        - if the line conceptual length is a multiple of mpl:
            don'y add a breal
        else:
            Idk lmao, add a line break before it?
- else (not in a MM rest):
    - if the length of the line is `mpl`:
        add a line break (balancing needed)
    - else:
        dont add a break



### Line Break Balancing:
        



## Page Breaks