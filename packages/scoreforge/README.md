# ScoreForge
Git Utility to enable MSCZ files to be git tracked like text files (incl merging)
(This is to replace the existing score-diff tool I was working on)

This project leverages Git to version control musescore files to allow for lots of collaboration




TODO: convert musescore diff tool as a diff viewer of the 2 scores -- user picks and chooses from which staff they want the data!
- (then, have the user delete the unused staves before saving, and that file can become the new one)
- (Can also have it build files from the canonical form which probably makes it easier to parse from)


https://app.shortcut.com/divisi-app/epic/141?ct_workflow=all&cf_workflow=500000005

## How it works under the hood

When a score is created, we load in 2 distinct files

1. A `template.mscz` file.
2. A `canonical.json` file.

The `template.mscz` file is the barebones mscz file. This contains all the metadata, instrument mappings, and all other things
The `canonical.json` file is a representation of all of the music data in the file, converted into very very barebones json. It is essentially json text of how musescore scores note and measure data.

When a score is being committed, we convert it into its canonical form, and we use this canonical form to store, diff, and merge changes.

Then, when a score


Flow of a user who wants to use this:

User "pulls" changes to get the latest canoncical / template data
Then, user "builds" the mscz file from the canonical and template data to get a current musescore file
user can edit file
When they are done, they commit their changes (this internally converts it back to canonical and template form to process diffs)
then, does the same git stuff, of if there is a diff, then visually display (using divv tool), then get new file and commit that


For now -- only working with the score file, and completely ignoring parts. 
Perhaps in the future, will apply this to parts as well


### TODO Right now

take musescore file in, and spit out template.mscz and canonical json

template.mscz will be a modified version of the initial mscz file where all mscx files have their measures removed (replaced with a placeholer so we know where to access it from), and the "Thumbnails" folder also removed (to save space)