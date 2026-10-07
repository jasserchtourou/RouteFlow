"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api";
import type { Page } from "@/features/dashboard/api-types";
import type { SiteScene } from "../model";

interface SiteOption {
  id: string;
  code: string;
  name: string;
}

export function SiteSwitcher({ scene }: { scene: SiteScene }) {
  const router = useRouter();
  const { data } = useQuery({
    queryKey: ["site-options"],
    queryFn: ({ signal }) => apiGet<Page<SiteOption>>("/warehouses", { limit: 100 }, signal),
    staleTime: 60_000,
  });
  const options = data?.items ?? [];

  return (
    <label className="pointer-events-auto flex min-w-0 items-center gap-3 rounded-xl border border-border bg-surface/90 px-3 py-1.5 shadow-xl backdrop-blur-md">
      <span className="grid size-8 shrink-0 place-items-center rounded-md bg-accent/15 text-xs font-bold text-accent">
        {scene.warehouse.code.replace("WH-", "")}
      </span>
      <span className="min-w-0">
        <span className="sr-only">Site</span>
        <select
          value={scene.warehouse.id}
          onChange={(event) => router.push(`/warehouses/${event.target.value}/3d`)}
          className="block max-w-56 truncate bg-transparent text-sm font-medium outline-none"
        >
          {options.length === 0 && (
            <option value={scene.warehouse.id}>{scene.warehouse.name}</option>
          )}
          {options.map((o) => (
            <option key={o.id} value={o.id} className="bg-surface">
              {o.code} · {o.name}
            </option>
          ))}
        </select>
        <span className="block text-xs text-muted">
          {Math.round(scene.warehouse.utilizationPct)}% full · {scene.kpis.docksOccupied}/
          {scene.kpis.docksTotal} docked
        </span>
      </span>
    </label>
  );
}

export function BackLink() {
  return (
    <Link
      href="/warehouses"
      aria-label="Back to warehouses"
      title="Back to warehouses"
      className="pointer-events-auto grid size-11 place-items-center rounded-xl border border-border bg-surface/90 text-muted shadow-xl backdrop-blur-md hover:text-foreground"
    >
      <ArrowLeft aria-hidden className="size-4" />
    </Link>
  );
}

export function LiveBadge({ scene, stale }: { scene: SiteScene; stale: boolean }) {
  return (
    <span
      className="pointer-events-auto flex h-11 items-center gap-2 rounded-xl border border-border bg-surface/90 px-3 text-xs shadow-xl backdrop-blur-md"
      aria-live="polite"
    >
      <span className="relative flex size-2">
        {!stale && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
        )}
        <span
          className={`relative inline-flex size-2 rounded-full ${stale ? "bg-warning" : "bg-success"}`}
        />
      </span>
      {stale
        ? "Connection lost, retrying…"
        : `Live ${new Date(scene.generatedMs).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}`}
    </span>
  );
}
