# SkuleNite-Divisi

Skule Nite Arrangement Management Website

Liam off-handedly referred to this as "Magellan but for Skule Nite" and I think that is the most perfect description ever.

http://divisi.nbiancolin.ca

Runs inside a Docker container.

## Repository layout

- **React frontend**: [`apps/frontend`](apps/frontend) (Vite)
- **Django backend**: [`apps/backend`](apps/backend) (REST API, PostgreSQL, Celery)
- **Python packages**: [`packages/`](packages/) (e.g. MuseScore tooling), installed editable from the backend

**Python version**: CI and production use **Python 3.11**. Match that locally to avoid subtle differences (use a 3.11 venv when working on the backend or packages).

## Developer commands (from repo root)

- **Frontend**: `npm run lint --prefix apps/frontend`, `npm run typecheck --prefix apps/frontend`, `npm run test --prefix apps/frontend`, `npm run build --prefix apps/frontend`
- **Python lint** (install [Ruff](https://docs.astral.sh/ruff/) via `pip install -r requirements-dev.txt`): `python -m ruff check apps/backend/ensembles/views` (matches CI; expand paths locally as needed)
- **Package tests** (with dev deps installed): `pytest packages/musescore-part-formatter/tests`, `pytest packages/musescore-score-diff/tests`
- **Pre-commit** (optional): `pre-commit install` then hooks run on commit

The backend dev image installs `requirements-dev.txt` so Ruff is available inside the container.

## Local development (Docker)

1. Copy environment templates and fill in secrets (never commit real secrets):

   ```bash
   cp .env.example .env
   # Edit .env: set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET for Discord OAuth.
   ```

   For the Vite app, see [`apps/frontend/.env.example`](apps/frontend/.env.example) (e.g. copy to `apps/frontend/.env.development`).

2. Start the stack:

   ```bash
   docker compose -f docker-compose.dev.yml up --build -d
   ```

## Production

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Backend apps (Django)

- `backend` — Django project settings and URLs
- `divisi` — part-prep / formatter flows
- `ensembles` — score and arrangement management

## How file storage is structured

### Part Formatter (Divisi)

- On upload, files are stored under `/blob/uploads/<uuid>/<file>.mscz`
- Processing copies into a temp working directory and writes output to `/blob/processed/<uuid>/<file>`
- The processed `.msc` and score PDF share the same base name

### Score Management (Ensembles)

- Raw uploads: `/blob/_ensembles/<ensemble>/<arrangement>/<version uuid>/raw/`
- After processing: `/blob/_ensembles/<ensemble>/<arrangement>/<version uuid>/processed/`
- Exported artifacts: formatted `.mscz`, PDF, and raw score XML for diffs (the XML export may later be narrowed to notes and text only)

> **Note:** If you log into Django Admin and then use the site, auth can conflict. Clear cookies for the site and try again.

## Contributing

- Reach out for access to [Shortcut](https://app.shortcut.com/divisi-app/epics)
- Own a ticket, branch from `main`, open a PR with a clear description, and request review

**Main must stay deployable.** Every merge to `main` triggers a deploy so we can ship incrementally.
