# KudiReady

**Credit-readiness for Nigerian micro and small businesses.**
Upload a bank or mobile-money statement (CSV). KudiReady turns it into the picture a loan officer actually looks at — monthly cash flow, margin, stability, existing debt — scores it across four explainable pillars, lists exactly what to fix, and lets the owner share a read-only, expiring credit file with a lender.

> Live app: `https://<your-vercel-app>.vercel.app` · API docs: `https://<your-render-api>.onrender.com/docs`

[![CI](https://github.com/ADAGBON/kudiready/actions/workflows/ci.yml/badge.svg)](https://github.com/ADAGBON/kudiready/actions/workflows/ci.yml)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ADAGBON/kudiready)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FADAGBON%2Fkudiready&root-directory=frontend&env=VITE_API_URL&envDescription=Your%20Render%20API%20URL%2C%20no%20trailing%20slash&project-name=kudiready)

![Dashboard](docs/screenshots/06-dashboard-after.png)

## Why

Nigerian MSMEs make up the overwhelming majority of businesses and jobs, yet finance is their most-cited growth constraint, and most never obtain a bank loan. A large part of the problem is not that the businesses are uncreditworthy, but that their records aren't legible to lenders. KudiReady works on that gap: it doesn't lend or make credit decisions; it helps an owner arrive at the lender's desk with a complete, consistent, explainable file. See the [report](docs/) for the full literature review.

## Features

- Email/password accounts (bcrypt, JWT), one business profile per owner
- CSV statement import that copes with real Nigerian exports: signed amount *or* debit/credit columns, `₦`/`NGN`/commas/brackets, five date formats, per-row error reporting
- Duplicate-safe re-uploads (per-line SHA-256 fingerprint + DB unique constraint + `ON CONFLICT DO NOTHING`)
- Rule-based categorisation tuned to Nigerian narrations (POS, NIP, Moniepoint/OPay, LAPO, IKEDC, FIRS/LIRS…), user-overridable
- Deterministic readiness engine: 12-month window, 18 indicators, 4 × 25-point pillars, an evidence cap for short histories, prioritised gap list with point uplift, indicative repayment capacity
- Lender share links: random 192-bit token, only its hash stored, frozen snapshot, 14-day expiry, revocable, view counter, printable
- Manual cash entries, search, filter, pagination; responsive down to 375 px

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 19 + TypeScript + Vite, React Router — deployed on **Vercel** |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, gunicorn/uvicorn — Docker on **Render** |
| Database | PostgreSQL 16 (Render managed) |
| CI/CD | GitHub Actions → Render & Vercel auto-deploy |

Architecture, data model and pipeline diagrams: [docs/architecture.md](docs/architecture.md).

## Run locally

```bash
# 1. Database
docker run -d --name kudi-pg -e POSTGRES_USER=kudi -e POSTGRES_PASSWORD=kudi -e POSTGRES_DB=kudiready -p 5432:5432 postgres:16

# 2. API  (http://localhost:8000/docs)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# 3. Web  (http://localhost:5173)
cd ../frontend
npm install
npm run dev
```

Try it with [`frontend/public/sample-statement.csv`](frontend/public/sample-statement.csv) (a synthetic Lagos provisions shop, February deliberately missing), then upload `sample-statement-feb-2026.csv` and watch the score move.

## Tests

```bash
cd backend
pytest                                    # fast, SQLite in-memory
DATABASE_URL=postgresql+psycopg://kudi:kudi@localhost:5432/kudiready pytest --cov=app   # real Postgres, as CI runs
```

39 tests, 94% line coverage: the scoring engine, CSV parsing edge cases, and full API flows including tenant isolation, duplicate uploads, share-link revocation and rate limiting.

## Deploy

See [docs/DEPLOY.md](docs/DEPLOY.md) — about 15 minutes, free tiers only.

## Project layout

```
backend/   FastAPI app, Alembic migrations, tests, Dockerfile
frontend/  React SPA, vercel.json
docs/      architecture, diagrams, screenshots, deployment guide, demo script
render.yaml            Render blueprint (API + Postgres as code)
.github/workflows/ci.yml
```

## Disclaimer

The readiness score measures how complete and lender-legible a business's records are. It is not a credit score or a lending decision. All sample data is synthetic.

---
Built by Lawrence Adagbon.
