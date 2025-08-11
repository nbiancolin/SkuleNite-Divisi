# SkuleNite-Divisi
Skule Nite Arrangement Management Website

Liam off-handedly referred to this as "Magellan but for Skule Nite" and I thinkt hat is the most perfect description ever. 

Magellan, but for skule nite, and open source! so we can acc fix issues that come up

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

> NOTE: If you log into DJANGO ADMIN then try to use the websirte it wont work. Clear cookies for the site then try again