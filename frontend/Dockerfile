# syntax=docker/dockerfile:1
# Three stages: install dependencies, build the app, run only the standalone server.

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_* values are inlined into the browser bundle at build time, so the address of the
# API (as the BROWSER sees it, not as another container sees it) must be given here.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -S -g 1001 routeflow && adduser -S -u 1001 -G routeflow routeflow
COPY --from=build --chown=routeflow:routeflow /app/public ./public
COPY --from=build --chown=routeflow:routeflow /app/.next/standalone ./
COPY --from=build --chown=routeflow:routeflow /app/.next/static ./.next/static
USER routeflow

EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD node -e "fetch('http://127.0.0.1:3000/dashboard').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"
CMD ["node", "server.js"]
