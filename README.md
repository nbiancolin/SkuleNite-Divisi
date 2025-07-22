# SkuleNite-Divisi
Skule Nite Arrangement Management Website

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

for dev, will do live reloads so no need to re-run it every time
(need to figure something out for prod)

> NOTE: If you log into DJANGO ADMIN then try to use the websirte it wont work. Clear cookies for the site then try again