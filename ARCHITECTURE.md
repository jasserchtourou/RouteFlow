# RouteFlow Architecture

## 1. Style: modular monolith

One deployable backend, internally split by domain module. Cheaper to run and refactor than
microservices, and module boundaries keep a later split possible.

```
backend/app/
  main.py                 app factory (create_app)
  core/                   config, database engine/session, logging, errors
  api/                    top-level router, shared dependencies, /api/v1 versioning
  modules/<domain>/       one folder per domain: orders, warehouses, inventory,
                          shipments, routes, tracking, vehicles, drivers, exceptions,
                          dashboard, yard
      models.py           SQLAlchemy models
      schemas.py          Pydantic request/response models
      repository.py       DB queries (only where it earns its keep)
      service.py          business rules, transactions
      router.py           HTTP endpoints (thin)
backend/alembic/          migrations
backend/tests/
```

Layering rule: **router → service → repository → DB**. Routers contain no business logic;
services own rules and transaction boundaries; repositories own queries. Modules call other
modules through services, never through each other's repositories.
(Per-module folders replace the global `models/ schemas/ services/` split from the initial
sketch: it keeps related code together and avoids cross-cutting giant folders.)

## 2. Domain model (initial)

Order 1—* Shipment; Warehouse 1—* InventoryItem; Warehouse 1—* Shipment;
Vehicle 1—* Shipment; Route *—* Shipment (via shipment.route_id, decided in Phase 2);
Shipment 1—* TrackingEvent; Shipment 1—* Exception; Vehicle *—1 Driver (assignment);
Warehouse 1—* Dock / Equipment; Dock 1—* DockAppointment (truck visit).

Entities: Order, Warehouse, InventoryItem, Shipment, Route, Vehicle, Driver,
TrackingEvent, Exception, Dock, Equipment, DockAppointment. Field lists follow the project brief and
will be refined in Phase 2. Status fields are DB-backed enums; all tables have
`created_at/updated_at`; UUID primary keys; human-readable numbers like `SHP-2211` are separate unique columns.

Shipment lifecycle (enforced in the service layer):
`CREATED → PICKED → PACKED → LOADED → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED`.
Exception types: DELAYED, TEMPERATURE_DEVIATION, DAMAGED, MISSING_DOCUMENT, STOCK_SHORTAGE.

## 3. API strategy

- REST, JSON, versioned under `/api/v1`.
- Pydantic v2 schemas separate from ORM models (Create / Update / Read).
- Pagination (`limit/offset`, with total), filtering and sorting via query params.
- Consistent error envelope; domain errors mapped to HTTP codes in one place.
- Auth is deferred until the core works.

## 4. Database strategy

- PostgreSQL 16 (official `postgres:16` image).
- SQLAlchemy 2.x async (`asyncpg`), one session per request via FastAPI dependency;
  services commit, repositories never do.
- Alembic for all schema changes. No `create_all` outside tests.
- Indexes on foreign keys and frequent filters (status, destination, timestamps); add more only after measuring (Phase 21).
- Separate test database; seed script for realistic dev data.

## 5. Testing strategy

- pytest + pytest-asyncio + httpx `AsyncClient` against the ASGI app.
- Tests run against real PostgreSQL, not SQLite, to avoid dialect drift;
  each test isolated by transaction rollback.
- Layers: unit (pure logic, e.g. status transitions), service, API integration, validation.
- Concurrency: race conditions in write paths are reproduced with two real sessions on committed
  data (A works without committing, B must block, then A finishes), not mocked.
- Quality gates: ruff (incl. security, async and pytest-style rules), strict mypy, `alembic check`
  (a test fails when a model changes without a migration), warnings as errors, randomised test
  order, coverage floor of 95 % (line + branch), pre-commit hooks (see `.pre-commit-config.yaml`).

## 6. Frontend strategy

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui; TanStack Query for server state;
Motion for subtle animation. Frontend never re-implements business rules; it renders API data.
A typed API client is generated from/aligned with the FastAPI OpenAPI schema.
Built shell-first with mock data, then wired to the backend (Phase 11).
Routes: `/dashboard /orders /shipments /warehouses /warehouses/[id]/3d /routes /tracking /events`.

### 3D warehouse digital twin (Phase 12.5)
Inspired by the "WareTrack" demo (reference screenshots: `docs/reference/3d-warehouse-ref-*.jpg`).
Original implementation in RouteFlow's own branding, not a copy. Route `/warehouses/[id]/3d`.

**Scene (React Three Fiber + drei, no game engine)**
- Isometric orthographic camera over one site: warehouse building with numbered dock doors
  (`In 1..n`, `Out 1..n`), yard with outlined parking/staging slots, road, fence, trees,
  containers, racks, pallets. Low-poly, instanced meshes; soft shadows; clean SaaS look.
- **Everything moves:** trucks drive in on the road, wait in the yard, reverse into a dock,
  then leave; forklifts shuttle pallets between dock and racks/staging; loading progress
  (e.g. `2/6` pallets) advances. Motion is client-side interpolation between backend states.
- Map pins over pallets/objects with open issues; floating hover labels
  (`PAL-1026 · Safety Helmet`, `In 2 · Booked`); selection brackets + glowing target zone.
- Camera controls: zoom in/out, rotate left/right, reset to home view; drag to pan.

**UI overlay (HTML on top of the canvas)**
- Top bar: global search (sites, trucks, forklifts, pallets, shipments; `/` shortcut),
  site switcher (`WH-GAR · 96% full · 2/6 docked`), `Live` indicator with clock.
- KPI cards: stock on hand (pallets), trucks on site (inbound count), on-time delivery
  (30 days), each with a trend delta.
- Detail panel for the selected object, by type: pallet/SKU (quantity, weight, location/slot,
  lot, received, site), dock bay (status `Booked/Occupied/Available`, assigned truck + ETA
  "due in 3 min", trucks today), truck, forklift. Pin and close actions; links into
  shipments/vehicles/inventory pages.
- Bottom left: shipment tracking stepper for the selected truck's shipment
  (Order confirmed → Picked → Loading x/n → In transit → Delivered, with times/ETAs) plus a
  compact shipment card (number, destination, status chip, dock, time left).
- Bottom right: tabbed operations list `Docks n/m | Forklifts n/m | Trucks n` with status
  chips and progress bars; clicking a row focuses the camera on that object.
- Theme: follows RouteFlow's dark theme by default; a light "daylight" scene like the
  reference is available via the theme toggle (colors are tokens, not hard-coded).

**Data (the 3D view is just another layer over the data model)**
- No business logic in the scene. It renders `GET /warehouses/{id}/scene` (one aggregated,
  typed payload: layout + live state) and polls it (TanStack Query, ~5 s); SSE only if needed.
- Backend additions, kept small and planned with their phases:
  - Phase 4: `docks` (warehouse, code, direction inbound/outbound, status) and
    `equipment` (forklifts: code, status, battery); rack/slot layout is *derived*
    deterministically from inventory (no hand-edited 3D coordinates).
  - Start of Phase 12.5 (moved from Phase 6): `dock_appointments` (truck visit: vehicle, shipment, dock, scheduled/arrived/
    departed, state EN_ROUTE/WAITING/DOCKED/LOADING/UNLOADING/DEPARTED, pallets done/total) and a
    yard simulator that advances these states over time so the site is alive in demos.
    The simulator runs in-process first; a background worker only if it proves necessary.
- Accessibility/performance: lazy-loaded canvas, instancing, reduced-motion support, and the
  same data available as plain tables (the ops list) without WebGL.

## 7. Infrastructure

Docker Compose: `postgres`, `backend` (migrations run on start) and `frontend`, all with
health checks; multi-stage, non-root images. No Redis/Celery until a real background-job need
appears (the yard simulator runs in-process).

## 8. Key decisions log

| Decision | Reason |
|----------|--------|
| Modular monolith | Simplicity, one deploy, clear seams |
| Per-module folders | Cohesion over layer-global folders |
| Real Postgres in tests | Catches enum/index/constraint behavior SQLite can't |
| UUID primary keys | Non-guessable ids in URLs, safe to generate client-side |
| VARCHAR+CHECK enums | Easy to evolve in migrations; DB still enforces validity |
| `lazy="raise"` relationships | No hidden queries in async code; prevents N+1 |
| Migrations build the test DB | Tests exercise the real schema, including migrations |
| Rules as pure functions + hybrid properties | One definition of "low stock" etc. for Python and SQL; a test checks they agree |
| Status changes only through events | Shipment history is the source of truth; every change is explained by a tracking event |
| Validate -> apply -> commit once | Multi-table writes (event, shipment, exception, order) are atomic |
| Row lock on event recording | Concurrent scanner events can't both pass the next-step check |
| Partial unique index for active incidents | DB guarantees one active exception per type; history unlimited |
| Explainable route risk score | Weighted, capped, with stated factors: testable and shown to the user |
| Business timezone + injectable clock | "Today" is the operator's calendar day; time-dependent logic is testable |
| Row locks for related write paths | Manual and automatic exception creation both lock the shipment, so they serialize instead of deadlocking |
| Safety guards raise, never `assert` | Asserts are stripped under `python -O`; guards on destructive actions must not be |
| Read models may join across modules | Aggregates (e.g. low-stock count per warehouse) in one query; writes stay with the owning module's service |
