# RouteFlow frontend

Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS 4. See the [main README](../README.md)
for the full project; this app talks to the FastAPI backend at `NEXT_PUBLIC_API_URL`
(default `http://localhost:8000/api/v1`).

```bash
npm install
npm run dev          # http://localhost:3000
npm test             # Vitest + Testing Library
npm run lint && npm run typecheck && npm run build
```

`NEXT_PUBLIC_*` values are baked into the browser bundle when the app is built, so when building
the Docker image pass the API address **as the browser reaches it** (`docker compose` does this
from `NEXT_PUBLIC_API_URL` in `.env`).
