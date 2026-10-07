# RouteFlow

**A logistics operations platform: orders, shipments, routes, fleet, warehouses and a live 3D view of a warehouse yard.**
FastAPI + PostgreSQL backend, Next.js + React Three Fiber frontend, fully containerised.

![Dashboard](docs/screenshots/dashboard.png)

| 3D warehouse yard (night) | 3D warehouse yard (day) |
|---|---|
| ![3D night](docs/screenshots/warehouse-3d-night.png) | ![3D day](docs/screenshots/warehouse-3d-day.png) |

> **Status:** the operations platform (backend, frontend, 3D site view, Docker) is complete and tested.
> The **Agentic RAG assistant is the planned final step and is not built yet** — see the [roadmap](#roadmap).

## What it does

- **Dashboard** — live KPIs (active and delayed shipments, on-time delivery vs yesterday, open exceptions, warehouse and fleet utilization), the logistics flow, live exceptions, animated numbers.
- **Orders / Shipments / Routes / Events** — sortable, filterable, paginated lists. Filters live in the URL, so a view can be shared. Side panels show shipment tracking history and open exceptions; routes get an **explainable risk score** ("2 delayed shipments, worst delay 95 min") and a *highest risk first* ranking; a network-wide event feed refreshes live.
- **Fleet map** — vehicles and warehouses on a map, filterable by status, synced with a vehicle list.
- **3D warehouse yard** — an isometric digital twin of a site: trucks drive in, reverse into dock doors and leave; forklifts carry pallets to the racks and give way to trucks and each other; pins mark pallets with stock problems. Click anything for details, search with `/`, collapse panels, switch day/night, full screen, keyboard shortcuts (`?`).

| Shipment details | Highest-risk routes |
|---|---|
| ![Shipments](docs/screenshots/shipments.png) | ![Routes](docs/screenshots/routes.png) |

## Quick start (Docker)

You need [Docker](https://docs.docker.com/get-docker/) with Compose. Nothing else.

```bash
git clone <your-fork-or-this-repo-url> routeflow
cd routeflow
cp .env.example .env                  # then set POSTGRES_PASSWORD (any value)
docker compose up -d --build          # database + API + web app; migrations run automatically
docker compose run --rm -e RUN_MIGRATIONS=0 backend python -m app.seed   # demo data
```

Open **http://localhost:3000** (web app) · **http://localhost:8000/docs** (API docs).

Stop with `docker compose down` (add `-v` to also delete the database). Re-create the demo data
with the seed command plus `--reset`. If port 5432, 8000 or 3000 is taken, change
`POSTGRES_PORT`, `BACKEND_PORT` or `FRONTEND_PORT` in `.env`.

> The 3D yard is populated by a small deterministic **yard simulator** that keeps a rolling
> schedule of truck visits. Turn it off with `YARD_SIMULATION_ENABLED=false` once you feed real
> dock appointments.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| Database | PostgreSQL 16 (pgvector image, for the later RAG step) |
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4, TanStack Query, anime.js |
| Maps / 3D | Leaflet (fleet map), three.js + React Three Fiber (yard) |
| Quality | pytest, ruff, strict mypy, Vitest, Testing Library, ESLint, pre-commit |
| Dev / ship | Docker, Docker Compose (multi-stage, non-root images), GitHub Actions |

## How it is built

- **Modular monolith.** Each domain (orders, warehouses, inventory, shipments, tracking, exceptions, routes, fleet, yard, dashboard) has its own models, schemas, pure business rules, repository, service and thin router. Business rules are plain functions with unit tests; SQL and Python versions of the same rule are checked to agree.
- **State is derived, not stored.** A truck visit stores only its planned timestamps; "en route / waiting / docked / loading / departed" is computed from the clock. The 3D view animates from the same timestamps.
- **Honest data layer.** UUID keys with human-readable numbers (`ORD-…`, `SHP-…`), CHECK constraints for every enum, race conditions reproduced and fixed with two real concurrent transactions.
- **Frontend renders, backend decides.** The UI never re-implements business rules; risk scores, delays and statuses come from the API. Accessibility: keyboard-reachable tables and panels, `aria-sort`, `aria-expanded`, colour is never the only signal, reduced-motion is respected.
- Design notes: [ARCHITECTURE.md](ARCHITECTURE.md) · working notes and decisions: [CONTEXT.md](CONTEXT.md).

## Development without Docker

```bash
# backend (needs uv: https://docs.astral.sh/uv/)
docker compose up -d postgres
cd backend
uv sync
uv run alembic upgrade head && uv run python -m app.seed
uv run uvicorn app.main:app --reload          # http://localhost:8000/docs

# frontend (Node 20+)
cd frontend
npm install
npm run dev                                   # http://localhost:3000
```

## Tests and quality

```bash
cd backend
uv run pytest --cov                    # 434 tests against real PostgreSQL, 100 % coverage
uv run pytest -m "not integration"     # fast tests without a database
uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
uv run alembic check                   # migrations match the models

cd frontend
npm test                               # 109 tests (Vitest + Testing Library)
npm run lint && npm run typecheck && npm run build
```

| Layer | What it proves |
|---|---|
| Unit | Business rules (status transitions, risk score, yard visit states, forklift traffic) without a database |
| Service / API | Use cases and HTTP behaviour against real PostgreSQL: filters, sorting, pagination, the error envelope, validation on every endpoint |
| Database | Constraints, migrations equal models, seed data, concurrency (real concurrent transactions) |
| Frontend | Components, URL-backed filters, accessibility roles, 3D logic (paths, collisions) as plain functions |

The test database is rebuilt from the real Alembic migrations on every run, warnings are errors, and test order is randomised.

## API at a glance

Interactive docs at `/docs`. Main resources:

| Resource | Endpoints |
|---|---|
| Orders | `GET/POST /api/v1/orders`, `GET/PATCH/DELETE /api/v1/orders/{id}`, `GET …/by-number/{number}` |
| Shipments | `GET /api/v1/shipments` (status, delayed, exceptions, search, ETA range), `GET …/{id}`, `GET …/{id}/tracking`, `POST …/{id}/events`, `POST …/{id}/exceptions` |
| Events | `GET /api/v1/events` — network-wide feed (type, search, since) |
| Exceptions | `GET /api/v1/exceptions`, `PATCH …/{id}` (investigate / resolve) |
| Routes | `GET /api/v1/routes`, `GET /api/v1/routes/at-risk` (ranked, explainable), `GET …/{id}` |
| Fleet | `GET /api/v1/vehicles`, `/drivers`, `/fleet/overview` |
| Warehouses | `GET /api/v1/warehouses`, `…/{id}/inventory`, `…/{id}/docks`, `…/{id}/equipment`, `…/{id}/scene` (3D view payload) |
| Dashboard | `GET /api/v1/dashboard/overview` |

## Roadmap

| Step | Status |
|---|---|
| Backend: orders, warehouses, inventory, shipments, tracking, exceptions, routes, fleet, dashboard | Done |
| Quality tooling, Docker (backend + frontend) | Done |
| Frontend: dashboard, orders, shipments, routes, events, fleet map | Done |
| 3D warehouse digital twin + yard simulator | Done |
| Write actions in the UI (record events, resolve exceptions, create orders), authentication and roles | Next |
| CI, end-to-end tests, generated API client, production hardening | Next |
| **Agentic RAG assistant** — document ingestion and pgvector search, an agent that chooses read-only tools over the live data, cited answers, evaluation | Last |

Design rules for the assistant: the model never touches the database or runs SQL, tools are narrow, typed and read-only, business logic stays in Python, and "insufficient evidence" is a valid answer.

## Credits and license

The 3D yard view was inspired by the "WareTrack" warehouse demo shared by Stanislav Beliaev;
all code, models and branding in this repository are original. Map data © OpenStreetMap contributors.

Released under the [MIT License](LICENSE).
