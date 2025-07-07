# SkuleNite-Divisi
Skule Nite Arrangement Management Website

Runs inside a docker containter!

3 main apps:
- React Frontend (/frontend)
- Django Backend (/backend)
  - (& associated postgresql database)
  - And associated Celery Server

to run:
```
docker-compose up --build
```
for dev, will do live reloads so no need to re-run it every time
(need to figure something out for prod)