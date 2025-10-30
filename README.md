# SkuleNite-Divisi
Skule Nite Arrangement Management Website

Liam off-handedly referred to this as "Magellan but for Skule Nite" and I think that is the most perfect description ever. 

http://divisi.nbiancolin.ca

Runs inside a docker containter!

3 main apps:
- React Frontend (/frontend)
- Django Backend (/backend)
  - (& associated postgresql database)
  - And associated Celery Server

to run (dev):
```
docker-compose up --build -d
```

to run prod:
```
docker compose -f docker-compose.prod.yml up --build -d
```

Backend:
- `backend` contains django config things
- `divisi` contains everything needed to do the part-prep stuff
- `ensembles` contains everything needed for score management



## How Files storage is structured

### Part Formatter (Divisi):

- On upload action, the files are stored to `/blob/uploads/<uuid>/<file>.mscz`
- Then, the process step grabs the file from its uuid, copies it into a temp working directory, then outputs the processed file in `/blob/processed/<uuid>/<file>`
- From there, the output msc file and score pdf have the same name.

### Score Management (Ensembles)

- raw uploaded files are stored in `/blob/_ensembles/<ensemble>/<arrangement>/<version uuid>/raw/`
- Once processed, moved out of raw folder (`/blob/_ensembles/<ensemble>/<arrangement>/<version uuid>/processed/`)
- Files Exported:
  - Formatted Mscz (same file name, in root uuid folder)
  - Formatted Score (same file name, extension.pdf)
  - Raw score XML (for computing Diffs)   TODO: This should probably export with just notes and text, no other formatting at all.

> NOTE: If you log into DJANGO ADMIN then try to use the website it wont work. Clear cookies for the site then try again

# How to Contribute:

- Reach out to me (Nick) for access to the Shortcut (https://app.shortcut.com/divisi-app/epics)
- Add yourself as an owner to a ticket
- Create a new branch with your changes
- Open a PR describing your changes, and request a review from me!

The reason for doing it this way is because ** the main branch needs to ALWAYS be in a deployable state**. On every merge/commit to main, a new deploy is triggered. This is so that I / we can ship code quickly, and incrementally
