# CONTEXT

Working context for contributors and AI coding sessions. Keep this current.

## Project
RouteFlow — logistics operations platform with an Agentic RAG assistant.
Repository root: `RouteFlow/`. Platform of the author: Windows 11 (PowerShell/Git Bash).

## Working rules
- Build **phase by phase**. After each phase: explain, show decisions and files, run tests, fix, summarize learning, then STOP until told "Continue to Phase X".
- Don't build future phases early; no speculative abstractions.
- Learning mode: briefly explain key concepts (DI, async, sessions, repositories, migrations, transactions, indexes, vector search, embeddings, tool calling, agent loops, structured output, RAG) when first used.

## Non-negotiables
- Modular monolith; no giant `main.py`/files/functions. Type hints and Pydantic everywhere.
- Secrets only via environment variables; never committed.
- LLM never touches the DB directly; no SQL tools; tools are narrow, typed, read-only.
- Business logic lives in Python services, not prompts.
- Current operational facts come from tools; procedural knowledge from RAG; agent must cite evidence and may say "insufficient evidence".
- Don't call it "agentic" unless the model really chooses tools.
- No Redis/Celery until needed. Auth after the core works.
- Tests accompany each feature; fix root causes, no hacks, no TODO placeholders for core features.

## Conventions
- API prefix `/api/v1`. Human-readable ids: `ORD-xxxx`, `SHP-xxxx`, `RTE-xxx`.
- Python 3.12, ruff, mypy, pytest (real PostgreSQL).
- Seed geography: Hannover, Garbsen, Langenhagen, Hamburg, Berlin, Leipzig, Kassel.

## Reference UI
Dark control-center dashboard: left nav, KPI cards, logistics flow
(Order → Warehouse → Shipment → Route → Delivery), live events, shipment table,
fleet map, warehouse status, AI assistant panel. Original implementation, not a copy.
(The reference screenshot was not attached to the Phase 0 request; please provide it before Phase 9/10.)

## Current status
- [x] Phase 0 — design docs, `.env.example`, `docker-compose.yml`
- [x] Phase 1 — FastAPI foundation (backend/, uv, 15 tests, ruff+mypy clean)
- [x] Phase 2 — models, Alembic migrations, deterministic seed data, DB tests
- [x] Phase 3 — Orders API (CRUD, filters/sort/pagination, status rules)
- [x] Phase 4 — Warehouses, inventory, low stock, docks + equipment
- [x] Phase 5 — Shipments, tracking events, exceptions
- [x] Phase 6 — Routes + risk, vehicles, drivers, fleet overview, dashboard (263 tests)
- [x] Phase 7 — Backend testing + quality (380 tests, 100 % line+branch coverage, pre-commit)
- [x] Phase 8 — Docker + development environment (backend image, compose, migrations on start)
- [x] Phase 9 — Frontend shell (Next.js, layout, nav, 8 placeholder routes, 5 tests)
- [x] Phase 10 — Dashboard UI on mock data (16 frontend tests)
- [x] Phase 11 — Dashboard wired to the API + anime.js animations (25 frontend tests)
- [x] Phase 12 — Fleet map on /tracking (Leaflet, 34 frontend tests)
- [x] Phase 12.5 — 3D warehouse digital twin (backend: 430 tests, 100 % coverage; frontend: 63 tests). NOT yet checked visually in a browser by the assistant.
- [ ] Phase 13 — RAG foundation

## Planned feature: 3D warehouse digital twin (Phase 12.5)
User request: a feature like the "WareTrack" 3D warehouse demo (LinkedIn post by Stanislav
Beliaev, https://lnkd.in/p/eYD2Bzb9). Reference screenshots: `docs/reference/3d-warehouse-ref-yard.jpg`,
`docs/reference/3d-warehouse-ref-docks.jpg`. Key points: isometric 3D site, **trucks and forklifts
move**, every object clickable with a detail panel, KPI cards, shipment stepper, Docks/Forklifts/
Trucks list. Full spec: ARCHITECTURE.md section 7. Backend groundwork: `docks` + `equipment`
(Phase 4, done). `dock_appointments` + yard simulator + `GET /warehouses/{id}/scene` were moved
from Phase 6 to the start of Phase 12.5, to be designed against the real 3D frontend needs.
Use RouteFlow branding, not WareTrack's.

## Open questions (to settle in later phases)
- Embedding model and dimension (Phase 13; default candidate `all-MiniLM-L6-v2`, 384 dims)
- Default local LLM for Ollama with reliable tool calling (Phase 14)

## Dev notes
- Backend: `cd backend && uv sync && uv run uvicorn app.main:app --reload`; checks: `uv run pytest`, `uv run ruff check .`, `uv run mypy app tests`. Unit-only: `pytest -m "not integration"`.
- If a local PostgreSQL already occupies 5432, set `POSTGRES_PORT=5433` and the port in `DATABASE_URL` in `.env` (happened on the author's machine).

## Database notes (Phase 2)
- Primary keys are UUIDs (generated client-side and by `gen_random_uuid()`); human-readable numbers (`ORD-`, `SHP-`, `RTE-`) are separate unique columns.
- Enums are VARCHAR + one explicit CHECK per column (`enum_checks`), not native PG enums. Do not use `Enum(create_constraint=True)` (creates duplicate constraints with the naming convention).
- Every relationship is `lazy="raise"`: load related data explicitly (`selectinload`/`joinedload`).
- Migrations: `uv run alembic upgrade head`; new one: `uv run alembic revision --autogenerate -m "..."` then REVIEW it. `alembic check` must report no drift (a test enforces it).
- Seed: `uv run python -m app.seed [--reset] [--seed N]`. Scripted cases: SHP-2211 (late, cold chain, temperature deviation, Hamburg->Hannover), SHP-2208 (in transit, 95 min delay, Hannover->Berlin), Garbsen warehouse (DISRUPTED, 96% full, low stock).
- DB tests (`tests/db`, marked `integration`) rebuild `routeflow_test` from migrations each run; set `TEST_DATABASE_URL` in `.env`.

## API conventions (Phase 3, apply to every module)
- Module layout: `models.py`, `schemas.py` (Create/Update/Read/ListParams), `rules.py` (pure business rules), `repository.py` (queries only, never commits), `service.py` (use cases, owns commit), `router.py` (thin). Register routers in `app/api/v1/router.py`.
- Lists return `Page[T]` (`items,total,limit,offset`); query params are one Pydantic model with `extra="forbid"`; sort keys are a whitelisted enum with `-` for descending and an `id` tie-breaker.
- Errors: 422 validation (Pydantic), 409 business rule (`ConflictError` subclasses with a specific `code`), 404 `NotFoundError`. Document with `responses=error_responses(404, 409)`.
- PATCH: absent field = unchanged, explicit null = 422; validate the *resulting* entity in the service.
- Escape user input in LIKE patterns. Server generates human-readable numbers (`order_number_seq`, ORD-20001+).
- `create_app()` imports `app.models` and calls `configure_mappers()`; `tests/test_startup.py` imports the app in a fresh process (the test-suite's own imports can hide missing model imports).

## Domain definitions (Phase 4) — single source of truth
- `available = quantity - reserved`; stock status: OUT_OF_STOCK (available <= 0), LOW (available <= reorder_threshold), else OK. "Low stock count" = LOW + OUT_OF_STOCK. `coverage_ratio = available / threshold` (lower = more urgent, null if threshold 0). `shortfall = threshold - available + 1`.
- Utilization level: HIGH >= 85 %, CRITICAL >= 95 %.
- Defined in `modules/*/rules.py`, exposed as SQLAlchemy hybrid properties (same rule in Python and SQL); `tests/db/test_hybrid_properties.py` enforces agreement. Cast SQL arithmetic to Float (PostgreSQL `100.0` is NUMERIC -> Decimal).
- Docks store only physical availability (AVAILABLE / OUT_OF_SERVICE); occupancy will be derived from dock appointments (Phase 12.5).
- Seed: site infrastructure uses its own RNG stream (`f"{seed}-site"`) so adding it did not change other seeded data. Garbsen: both inbound docks out of service, 2 forklifts in maintenance.

## Shipments / tracking / exceptions (Phase 5)
- Shipment status changes ONLY via `POST /shipments/{id}/events` (lifecycle events: PICKED, PACKED, LOADED, DEPARTED->IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED; strictly next step). Informational: CHECKPOINT, ARRIVED_HUB, DELAY_REPORTED (`details.delay_minutes`, shifts ETA, raises DELAYED), TEMPERATURE_ALERT (`details.temperature_c`, outside 2-8 °C -> DEVIATION + TEMPERATURE_DEVIATION, CRITICAL if >= 3 °C outside).
- `TrackingService.record`: validate everything -> apply -> single commit (event + shipment + exception + order). Shipment row locked with SELECT ... FOR UPDATE (`tests/db/test_concurrency.py`).
- Orders follow shipments forward only (`orders.rules.advance_to`); DELIVERED only when all shipments delivered; cancelled orders block shipment progress.
- "Delayed" = not delivered and ETA < now. One `now` per request for SQL filter and flags.
- Exceptions: OPEN -> INVESTIGATING -> RESOLVED (or OPEN -> RESOLVED); resolved is closed; resolving needs `resolution_note` (DB CHECK). At most one *active* exception per (shipment, type): partial unique index; automatic signals escalate the existing one (`raise_or_escalate`).
- Module dependency direction: tracking -> shipments -> exceptions (exceptions depends on no other service).
- `Base.__mapper_args__ = {"eager_defaults": True}`: server-generated timestamps come back via RETURNING (avoids MissingGreenlet in async).

## Routes / fleet / dashboard (Phase 6)
- Route risk = explainable score 0-100 (`routes/rules.py`): planned risk base + delayed shipments + worst delay + active HIGH/CRITICAL exceptions + DELAYED flag (each capped); returns `factors` strings. `GET /routes/at-risk` ranks active routes by it (computed in Python; the network is small).
- "Delayed route" = flagged DELAYED OR carrying a delayed shipment.
- On-time = `actual_delivery <= order.promised_delivery_at` (customer promise, not the movable ETA).
- "Today/yesterday" = calendar days in `BUSINESS_TIMEZONE` (Europe/Berlin), via `core/clock.business_day` (DST-safe). The dashboard takes `now` from the injectable `Clock` dependency (tests freeze it).
- Network utilization is capacity-weighted. Low fuel < 20 %.
- Seed: delivered shipments span 2-96 h ago so "today" has deliveries.
- Doc edit scripts must assert that each replacement matched (silent `str.replace` misses left stale status lines until Phase 6).

## Frontend tooling requested by the author (use from Phase 9)
- UI/UX design skill: `ui-ux-pro-max` (github.com/nextlevelbuilder/ui-ux-pro-max-skill, also listed on claudemarketplaces.com). Review its SKILL.md before installing.
- 21st.dev Magic MCP (component search/generation for React/Tailwind; relevant for animation/polish): configured in `.mcp.json` (hosted server `https://21st.dev/api/mcp`, key read from env var `API_KEY_21ST`, obtained at 21st.dev/mcp; never commit it). Claude Code asks for approval the first time a project-level MCP server is used. Source: the official repo github.com/21st-dev/magic-mcp.
- Both are frontend-only: no impact on backend phases.

## Docker (Phase 8)
- `docker compose up -d --build` starts postgres + backend; the entrypoint (`backend/docker-entrypoint.sh`) runs `alembic upgrade head` then the server. `RUN_MIGRATIONS=0` skips it for one-off commands.
- Seed in the container: `docker compose run --rm -e RUN_MIGRATIONS=0 backend python -m app.seed [--reset]`.
- Inside compose the backend reaches the DB as `postgres:5432` (compose overrides `DATABASE_URL`); the host-published port (`POSTGRES_PORT`, 5433 on the author's machine) only matters for host tools and tests. Backend host port: `BACKEND_PORT` (default 8000).
- Image: multi-stage, uv installs locked prod deps only, non-root user, healthcheck on `/api/v1/health/ready`. `.env` and `tests/` are not in the image.
- Docker Desktop must be running (start it before `docker compose`).

## Frontend shell (Phase 9)
- `frontend/`: Next.js 15 (App Router, Turbopack) + TypeScript strict + Tailwind v4 + TanStack Query provider + lucide icons + Motion (installed, not used yet). No shadcn CLI: small hand-written primitives in `components/ui`; adopt shadcn components when a phase needs them.
- Layout: `app/(app)/layout.tsx` wraps all pages in `AppShell` (sidebar >= lg, drawer below, topbar, skip link). Nav is data: `lib/nav.ts` (`NAV_ITEMS`, `isActivePath`). Pages for the 8 planned routes are placeholders (`ComingSoon`) until Phases 10-12/18.
- Dark-only palette as semantic tokens in `globals.css` (`bg-surface`, `text-muted`, `text-accent`, ...). Never raw hex in components. Reduced-motion respected.
- Commands (from `frontend/`): `npm run dev|build|lint|typecheck|test`. Tests: Vitest + Testing Library on **happy-dom** (jsdom 27+ breaks on Node 20.10). Config is `vitest.config.mts` (ESM).
- Node here is 20.10 (npm warns it wants >=20.17); everything works, but upgrading Node is advisable. `npm audit` reports advisories fixed only by Next 16 (breaking); revisit before Phase 21.
- `create-next-app` runs `git init` inside `frontend/`; it was removed so the repo root can be the single repository.
- The ui-ux-pro-max skill was NOT installed (cloning/running third-party scripts was blocked); the design follows its published rules (contrast, 44px targets, focus rings, reduced motion) by hand. 21st.dev MCP needs `API_KEY_21ST` set in the OS environment.

## Frontend Docker image and GitHub packaging
- `frontend/Dockerfile`: 3 stages (npm ci -> build -> runtime) on node:22-alpine, Next `output: "standalone"` (`node server.js`, ~354 MB image), non-root user, healthcheck. `NEXT_PUBLIC_API_URL` is a **build arg** (inlined into the browser bundle; must be the address the BROWSER uses, default http://localhost:8000/api/v1). `docker compose up -d --build` now starts postgres + backend + frontend (`FRONTEND_PORT`, default 3000; stop any local `npm run dev` first, same port).
- Do not run `npm run build` while `npm run dev` is running (both use `.next`; the dev server breaks).
- GitHub packaging: README rewritten with screenshots (`docs/screenshots/`, taken with headless Chrome), MIT `LICENSE` (holder name to be confirmed by the owner), `.github/workflows/ci.yml` (backend, frontend, docker build: written but NOT yet run on GitHub), `.gitignore` excludes `.claude/`, `docs/reference/` (third-party WareTrack screenshots) and `.env.*`. The folder was not a git repository until the owner runs `git init`.
- Re-seed for fresh demo timestamps: `docker compose run --rm -e RUN_MIGRATIONS=0 backend python -m app.seed --reset`.

## Orders, Shipments, Routes, Events pages (built after the user noticed they were still placeholders)
- These four pages had been left as "Arrives in Phase 11/12" stubs when the roadmap numbering shifted; they are real now. Only `/ai` remains a placeholder (Phases 14-19).
- Shared list kit (`components/data/`): `DataTable` (sortable headers with `aria-sort`, skeleton rows, empty state, first cell is a real button so rows are keyboard-reachable), `Pagination` (20 per page), `FilterBar` (`SearchField` debounced 300 ms, `ChipFilter` multi-select with `aria-pressed`, `ToggleChip`), `Drawer` (slide-over `aside`, Esc closes, focus moves in). `hooks/use-list-state.ts` keeps filters/sort/page/open item in the URL query string (shareable, back button works; changing a filter resets the page, opening a drawer does not). `features/ops/use-page-query.ts` keeps the previous rows (dimmed) while a new page loads.
- Orders: filters status/priority/search, sortable columns, drawer lists the order's shipments (`/shipments?search=ORD-...`). Shipments: **open shipments by default** (URL: no `status` = open, `status=all` = no filter, else a list; helpers `selectedStatuses`/`statusParam`), delayed-only and with-exceptions toggles, drawer shows facts, open exceptions and the tracking history (newest first). Routes: "All routes" with status/planned-risk/delayed filters, or "Highest risk first" (`/routes/at-risk`, min level chips); risk shown as a meter + number + level (never colour alone), drawer explains the score with the backend's `factors` and lists the route's shipments. Events: network-wide feed refreshed every 10 s, filters by type/time range/search, links to `/shipments?open=SHP-...`.
- Backend addition: `GET /api/v1/events` (modules/tracking: `FeedEventRead`, `EventFeedParams`, `TrackingRepository.feed`) - paginated, newest first, filters `event_type[]`, `search` (shipment number, origin, destination, location), `since`. 3 new API tests; backend now 434 tests at 100 % coverage.
- Tests: `tests/ops-views.test.tsx` (19 tests) uses an in-memory `next/navigation` (`tests/helpers/navigation.ts`) so URL-backed filters really round-trip, and `mockBackend` (`tests/fixtures/ops.ts`) that records requests. Tables show skeleton rows first: tests must wait for real rows (`loadedTable`).
- Read-only for now: recording events, editing orders or resolving exceptions from the UI is not built (the API supports it).

## 3D warehouse digital twin (Phase 12.5)
**Backend (`modules/yard/`)**
- `dock_appointments` table = the *plan* of a truck visit (dock, direction, optional shipment, truck code, carrier, `arrives_at < docked_at < departs_at`, pallets_total, `sequence` per dock). The visit's **state is never stored**: `rules.visit_state(...)` derives SCHEDULED/EN_ROUTE/WAITING/DOCKED/LOADING/UNLOADING/DEPARTED/COMPLETED from the timestamps and the injectable Clock (constants APPROACH 6 min, DOCKING 1 min, LEAVING 2 min). Dock occupancy (AVAILABLE/BOOKED/OCCUPIED/OUT_OF_SERVICE) is derived the same way. Active forklifts are assigned round-robin to docks with pallets moving.
- Simulator (`simulator.py`): deterministic `plan_visit` seeded by (warehouse, dock, sequence); `YardService.top_up_schedule` runs inside `GET /warehouses/{id}/scene` under a row lock (idempotent), keeps 3 h ahead, prunes after 36 h, skips out-of-service docks, links outbound visits to shipments still at the warehouse. A deliberate *read that tops up demo data*; switch off with `YARD_SIMULATION_ENABLED=false` (default true) when real appointments exist. No background worker.
- `GET /api/v1/warehouses/{id}/scene` returns layout + `timings` + docks + visits + equipment + pallets (derived from inventory, ordered by SKU, `has_issue` for LOW/OUT) + KPIs (stock, trucks on site, per-site on-time 30 d vs previous 30 d).
- Migration `550953e34734`; FK `shipment_id` needed its own index (the "every FK indexed" test caught it).

**Frontend (`features/site3d/`, route `/warehouses/[id]/3d`, list at `/warehouses`)**
- Pure, tested logic: `geometry.ts` (world layout from dock/bay counts), `motion.ts` (truck/forklift pose from timestamps, polyline paths, reversing into bays/docks), `tracker.ts` (stepper), `selection.ts`, `mapper.ts`. The client clock is the server's `generated_at` advanced by `performance.now()`, so animation is right even if the user's clock is wrong. Under reduced motion positions only change on data refresh.
- Scene (`scene/`): React Three Fiber 9 + drei 10, orthographic isometric camera with fixed elevation (drei `CameraControls`: left-drag pan, right-drag rotate, wheel zoom, buttons for zoom/rotate/reset, animated focus on selection), night (default) and day palettes, building with dock doors tinted by state, yard bays, road, trees, fence, racks + pallets, trucks and forklifts (plain meshes: with <= ~50 pallets instancing was not worth it), hover labels, selection edges + glow zone, "!" pins on pallets with stock issues. Canvas is `dynamic(..., { ssr: false })`.
- Overlay (`overlay/`): KPI tiles, detail panel by object type, shipment tracker, tabbed ops list (Docks/Forklifts/Trucks) that focuses the camera, camera buttons, site switcher + live indicator + theme toggle. The ops list is the non-WebGL equivalent of the scene.
- Polled every 5 s (`useScene`). Tests replace the canvas with a stub (no WebGL in happy-dom).
- Forklift traffic (revised three times after user feedback: drove through trailers; crossed each other; only moved beside the trucks): forklifts are a small per-frame simulation (`fleet.ts`, `ForkliftFleet`, stepped in `FleetDriver` inside the Canvas; trucks stay timestamp-driven). Each working unit cycles `out` (carry pallet from truck to strip exit) -> `trip` (shared yard lanes to the racks beside the building: loaded lane z=11 going right, up a rack road, drop at `RACK_DROP_Z`, down the second rack road, empty lane z=9.6 back) OR `local` (short shuffle) -> `back` -> `turn`. Routes are built in `geometry.ts` (`forkliftRoutes`). Rules: every dock has two private strips (one each side of its truck, `DOCK_SPACING` 7.8; backend caps 2 forklifts per working dock); the shared lanes carry ONE unit at a time (token, `lanesHeldBy`) and units that find them busy do a local shuffle and try next lap; units stop (`blocked`, probing along their own route incl. next stage) while a truck is in the way (`truckObstacles`), trucks never wait. Sync keeps a unit's position across 5 s refreshes and restarts it only if its dock/lane changed. Tests (`tests/site3d-fleet.test.ts`) simulate 15 min with 14 units + a docked truck at each of 7 docks: min distance >= 1.2 m, no trailer hits, <= 1 unit on shared lanes, >5 units reach racks carrying then dropping, every unit travels >300 m. Not simulated: forklifts entering trailers, pallets appearing in racks, curved turns.
- UI pass after user feedback ("too many problems, forklifts don't look good, make it more pro, tabs collapsible"): found by finally *looking* at the page - headless Chrome with software WebGL works for screenshots: `chrome --headless=new --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --virtual-time-budget=22000 --window-size=1600,950 --screenshot=out.png <url>` (add `--enable-logging=stderr --v=0` and grep CONSOLE for browser console output). Always check screenshots + console after 3D/layout changes; unit tests cannot see them.
  - Panels: `components/ui/panel.tsx` (`Panel`): collapsible card, header is a button (`aria-expanded`/`aria-controls`), body animates via CSS grid rows and is `inert` while closed, header shows a one-line digest when collapsed, state remembered per panel in localStorage (`hooks/use-stored-state.ts`, guarded: private mode / blocked storage / garbage values all fall back to defaults). Metrics + Tracking start collapsed on short viewports (< 820 px high); a first-time default only, the user's choice is remembered.
  - App shell: sidebar collapses to icons (labels stay as `title`/sr-only), remembered.
  - Site view toolbar (zoom, rotate, reset, hide/show all panels, day/night, full screen, shortcuts), combobox search (`/`; trucks by code/carrier/dock/shipment/destination, docks, forklifts, pallets), keyboard shortcuts (`/ H F R + - [ ] ? Esc`), shortcut dialog, theme remembered and settable with `?theme=day|night`.
  - Camera: own framing (`Rig.fit`) computes zoom from the site's extents in view space and keeps the fixed isometric angle; camera-controls `fitToBox` must NOT be used (it re-orients the camera to face the building and flattens the angle). Re-fits on resize until the user moves the camera; "reset" re-fits.
  - Labels and pins are canvas-texture sprites (`scene/label.tsx`), not drei `<Html>`: `Html` mounts a separate React root per label and unmounting those inside a commit made React 19 log "Attempted to synchronously unmount a root while React was already rendering" (the Next dev badge counted them as issues). Sprites keep constant pixel size under zoom.
  - Forklift model rebuilt (1.35x scale): chassis, counterweight, seat and driver, steering wheel, overhead guard with pulsing beacon, two-part mast, carriage that lifts with a load, wheels with hubs. Strip/probe geometry adjusted for the bigger body (`DOCK_SPACING` 8.4, loop lanes 0.9 m apart, probe padding 0.8).
  - Palette: lighter night ground + paved pad in front of the doors; the day look is bright like the reference screenshots.
  - Issue pins: a single counted pin while zoomed out, one pin per pallet once zoomed in (zoom >= 22); problem pallets are tinted amber/red either way.
  - Remaining console noise: "THREE.Clock deprecated" comes from react-three-fiber internals; harmless.
- Known gaps: no keyboard navigation inside the canvas (use the search and the list); trucks do not yield to forklifts (forklifts yield to trucks); motion itself is verified by simulation tests only (screenshots are static); the Operations panel covers part of the racks on the right at default zoom (collapse it with its header).
- `lib/api.ts` now reads the backend error envelope `{error:{code,message}}` (previously it only handled FastAPI's `detail`).

## Fleet map (Phase 12)
- Decision: **Leaflet + react-leaflet 5**. Tiles: OpenStreetMap public tiles (no key) darkened with a CSS filter (`.map-tiles-dark`); CARTO's free `dark_all` tiles were used first but now answer with an "API KEY REQUIRED" watermark. OSM public tiles are for light use: for production use a keyed provider or your own tile server. Leaflet needs `invalidateSize()` when its container resizes (`InvalidateOnResize`) or a grey band appears. MapLibre GL was not needed for ~25 markers. The map module is loaded with `next/dynamic({ ssr: false })` because Leaflet touches `window` on import.
- `features/tracking/`: `use-fleet.ts` (`/vehicles?limit=100` + `/warehouses?limit=100`, refetch 10 s), `mappers.ts` (drops vehicles without a position and reports the count; in-transit first), `fleet-map.tsx` (divIcon markers styled with Tailwind classes; pulsing ring for in-transit, red ring for low fuel, selected ring; fit-to-bounds once; fly-to on selection, no animation under reduced motion), `vehicle-list.tsx` (the accessible equivalent of the map), `tracking-view.tsx` (status filter chips with counts, selection shared between list and map).
- Map wrapper uses `isolate` so Leaflet's z-indexes stay under the mobile drawer. Leaflet tooltip/attribution restyled in `globals.css`.
- Tests mock `next/dynamic` with a stub map (Leaflet needs real layout); the real map is only verified in a browser. Fixtures: `tests/fixtures/fleet.ts`.
- Not done: route lines (routes have city names, no coordinates in the API), vehicle movement history/trails, tile hosting for production (CARTO free tier terms apply).

## API integration + animation (Phase 11)
- Data flow: `lib/api.ts` (`apiGet`, `ApiError`, base `NEXT_PUBLIC_API_URL`, default http://localhost:8000/api/v1) -> `features/dashboard/use-dashboard.ts` (one TanStack `useQuery`, 3 parallel calls: `/dashboard/overview`, `/shipments` (all non-delivered, soonest ETA, limit 6), `/exceptions?active=true`; refetch every 15 s) -> `mappers.ts` (pure, tested) -> view-models in `types.ts`. Raw response types in `api-types.ts` (hand-written subset; consider generating from OpenAPI later).
- There is no global tracking-event feed endpoint, so "Live events" shows active exceptions. A real feed (e.g. `GET /events`) is a backend addition for the Events page.
- `DashboardView`: skeleton -> data; error with retry when nothing loaded; keeps stale data with a warning when a refresh fails. Null KPIs render as an em dash.
- Animation uses **anime.js v4** (`animejs`; `motion` was removed): `AnimatedNumber` (count-up), `AnimatedBar` (grow), `Reveal` (staggered entrance), flow arrows loop, live events slide in only when new, CSS ping on alerts/live dot. Everything checks `prefersReducedMotion()` (`lib/motion.ts`) and renders final values without animating. Layout effects are used so there is no flash of the final value.
- Tests stub `matchMedia` as reduced-motion (`tests/setup.ts`, in `beforeEach` because `vi.unstubAllGlobals` removes global stubs) and freeze `Date` only for the view test. Test data: `tests/fixtures/api.ts`.
- Verified against the running backend (seeded): response shapes match; CORS allows http://localhost:3000. Visual/animation quality has not been checked in a browser by the assistant.

## Dashboard UI (Phase 10)
- Feature code lives in `frontend/src/features/dashboard/` (`types.ts`, `mock-data.ts`, one file per panel). `app/(app)/dashboard/page.tsx` is a server component that reads `MOCK_DASHBOARD`; Phase 11 replaces that constant with `GET /api/v1/dashboard/overview` (+ shipments/events endpoints) via TanStack Query and maps the response to the same view-models in `types.ts`.
- The UI renders values only; thresholds (utilization HIGH 85 / CRITICAL 95) are display colours mirroring the backend, not business rules. Status is never colour-only (badges carry text, bars are `role=progressbar`).
- Shared primitives: `Badge` (tones), `Card`, `FadeIn` (Motion, skipped under reduced motion), formatters in `lib/format.ts`.
- Phase 10 started on mock data; Phase 11 replaced it with the API (mock file deleted).
- Not yet in the dashboard: fleet map (Phase 12), AI panel (Phase 18), live updates (Phase 11/12). The reference "left nav / KPI / flow / events / table / warehouse" layout is covered except map and AI panel.

## Testing and quality (Phase 7)
- Layout: `tests/unit` (pure rules/schemas, no DB), `tests/service` (use cases called directly), `tests/api` (HTTP -> real PostgreSQL), `tests/db` (constraints, migrations, hybrid properties, seed, races). Anything using the `test_database_url` fixture is auto-marked `integration`.
- Commands (from `backend/`): `uv run pytest` (all), `uv run pytest -m "not integration"` (111 fast tests, ~2 s), `uv run pytest --cov` (fails under 95 %; currently 100 %), `uv run ruff check . && uv run ruff format --check .`, `uv run mypy app tests`, `uv run alembic check`.
- Config: warnings are errors (`filterwarnings = ["error"]`); `pytest-randomly` shuffles test order (a failure prints its seed: rerun with `-p randomly --randomly-seed=N`); coverage uses `concurrency = ["greenlet", "thread"]` (without it, code after every `await session...` is reported as untested).
- Race conditions: reproduce them with two real sessions on committed data (`tests/db/test_races.py`, fixtures in `tests/db/conftest.py`): session A does work without committing, B must block, then A finishes. Bugs found this way in Phase 7: manual vs automatic exception deadlock (fix: lock the shipment before raising a manual exception) and a MissingGreenlet in the order-delete conflict handler (fix: read attributes before `rollback()`, which expires all ORM objects).
- Safety checks must raise, not `assert` (asserts disappear under `python -O`), e.g. the "refusing to wipe a non-test database" guard.
- Ruff `TC003` is disabled for model files: SQLAlchemy needs `uuid`/`datetime` at runtime for `Mapped[...]`.
- Pre-commit (`.pre-commit-config.yaml`): hygiene, private-key detection, ruff, strict mypy, blocks `.env`; unit tests on pre-push. Not yet installed: the folder is not a git repository. After `git init`: `cd backend && uv run pre-commit install --install-hooks`.
- `.gitattributes` forces LF; reference screenshots are JPEGs in `docs/reference/`. Original full-size screenshots in the repo root are git-ignored.
