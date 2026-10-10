"use client";

import dynamic from "next/dynamic";
import { RefreshCw, WifiOff } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { useMediaQuery } from "@/hooks/use-media-query";
import { useStoredState } from "@/hooks/use-stored-state";
import { ApiError } from "@/lib/api";
import { prefersReducedMotion } from "@/lib/motion";
import { ForkliftFleet } from "./fleet";
import type { Selection } from "./model";
import { DetailPanel } from "./overlay/detail-panel";
import { KpiPanel } from "./overlay/kpi-strip";
import { OpsList } from "./overlay/ops-list";
import { ShipmentTracker } from "./overlay/shipment-tracker";
import { ShortcutsDialog, useSiteShortcuts } from "./overlay/shortcuts";
import { BackLink, LiveBadge, SiteSwitcher } from "./overlay/site-header";
import { SiteSearch } from "./overlay/site-search";
import { QUARTER_TURN, Toolbar } from "./overlay/toolbar";
import type { Interaction } from "./scene/interaction";
import { PALETTES, type ThemeName } from "./scene/palette";
import type { CameraApi } from "./scene/site-canvas";
import { selectionExists, selectionPoint, trackedVisit } from "./selection";
import { useScene } from "./use-scene";

// three.js needs WebGL and `window`: the canvas is only ever loaded in the browser.
const SiteCanvas = dynamic(() => import("./scene/site-canvas"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-surface" />,
});

// The top bar and a strip on the right (operations list) are kept clear; the left panels sit
// over the empty corner of the yard.
const WIDE_INSETS = { left: 0, right: 200, top: 76, bottom: 12 };
const NARROW_INSETS = { left: 0, right: 0, top: 0, bottom: 0 };

const isTheme = (value: unknown): value is ThemeName => value === "night" || value === "day";

export function SiteView({ warehouseId }: { warehouseId: string }) {
  const { scene, getNow, isPending, isError, error, refetch } = useScene(warehouseId);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [hovered, setHovered] = useState<Selection | null>(null);
  const [theme, setTheme] = useStoredState<ThemeName>("site3d:theme", "night");
  const [panelsHidden, setPanelsHidden] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const wide = useMediaQuery("(min-width: 1024px)");
  // On short windows the side panels would hide most of the scene: start them collapsed.
  const tall = useMediaQuery("(min-height: 820px)");
  const apiRef = useRef<CameraApi>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  // Forklift traffic lives outside React state: it changes every frame.
  const [fleet] = useState(() => new ForkliftFleet());

  // A shareable link can pick the look: .../3d?theme=day
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("theme");
    if (isTheme(requested)) setTheme(requested);
    // Only on first load: afterwards the toolbar owns the setting.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const sync = () => setFullscreen(document.fullscreenElement === frameRef.current);
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void frameRef.current?.requestFullscreen?.();
  }, []);

  // Reduced motion: positions only change when new data arrives, nothing glides in between.
  const frozenNow = scene?.generatedMs ?? 0;
  const sceneNow = useMemo(
    () => (prefersReducedMotion() ? () => frozenNow : getNow),
    [frozenNow, getNow],
  );

  const interaction = useMemo<Interaction>(
    () => ({
      selection,
      hovered,
      hover: setHovered,
      select: (next) => {
        setSelection(next);
        if (next && scene) {
          const point = selectionPoint(scene, next, sceneNow(), fleet);
          if (point) apiRef.current?.focus(point.x, point.z);
        }
      },
    }),
    [selection, hovered, scene, sceneNow, fleet],
  );

  useSiteShortcuts({
    search: () => searchRef.current?.focus(),
    panels: () => setPanelsHidden((hidden) => !hidden),
    fullscreen: toggleFullscreen,
    reset: () => apiRef.current?.reset(),
    zoomIn: () => apiRef.current?.zoomIn(),
    zoomOut: () => apiRef.current?.zoomOut(),
    rotateLeft: () => apiRef.current?.rotate(-QUARTER_TURN),
    rotateRight: () => apiRef.current?.rotate(QUARTER_TURN),
    help: () => setHelpOpen((open) => !open),
    escape: () => (helpOpen ? setHelpOpen(false) : setSelection(null)),
  });

  if (isPending) {
    return (
      <div
        aria-busy="true"
        aria-label="Loading site"
        className="h-[60vh] animate-pulse rounded-xl bg-surface"
      />
    );
  }
  if (!scene) {
    const message = error instanceof ApiError ? error.message : "Could not load this site.";
    return (
      <Card role="alert" className="flex flex-col items-center gap-3 py-12 text-center">
        <WifiOff aria-hidden className="size-8 text-danger" />
        <p className="font-medium">Site view unavailable</p>
        <p className="max-w-md text-sm text-muted">{message}</p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-2 inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:opacity-90"
        >
          <RefreshCw aria-hidden className="size-4" />
          Try again
        </button>
      </Card>
    );
  }

  const palette = PALETTES[theme];
  const insets = wide ? WIDE_INSETS : NARROW_INSETS;
  const shown = selection && selectionExists(scene, selection) ? selection : null;
  const visit = trackedVisit(scene, shown);

  return (
    <div
      ref={frameRef}
      className="relative isolate overflow-hidden rounded-xl border border-border bg-background lg:h-[calc(100dvh-7rem)] lg:min-h-[36rem]"
    >
      {/* The canvas fills the frame on wide screens; on narrow ones panels stack below it. */}
      <div className="h-[55vh] min-h-80 lg:absolute lg:inset-0 lg:h-auto">
        <SiteCanvas
          scene={scene}
          fleet={fleet}
          getNow={sceneNow}
          palette={palette}
          interaction={interaction}
          apiRef={apiRef}
          insets={insets}
        />
      </div>

      <div className="pointer-events-none flex flex-col gap-3 p-3 lg:absolute lg:inset-0">
        {/* Top bar */}
        <div className="flex flex-wrap items-start gap-2">
          <BackLink />
          <SiteSwitcher scene={scene} />
          <SiteSearch scene={scene} onSelect={interaction.select} inputRef={searchRef} />
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <LiveBadge scene={scene} stale={isError} />
            <Toolbar
              apiRef={apiRef}
              theme={theme}
              onTheme={setTheme}
              panelsHidden={panelsHidden}
              onPanelsHidden={setPanelsHidden}
              fullscreen={fullscreen}
              onFullscreen={toggleFullscreen}
              onHelp={() => setHelpOpen(true)}
            />
          </div>
        </div>

        {/* Side panels: columns on wide screens, a stack on narrow ones */}
        {!panelsHidden && (
          <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row lg:justify-between">
            <div className="pointer-events-auto flex min-h-0 flex-col gap-3 lg:w-80 lg:justify-between">
              <KpiPanel scene={scene} defaultOpen={tall} />
              <ShipmentTracker visit={visit} defaultOpen={tall} />
            </div>
            <div className="pointer-events-auto flex min-h-0 flex-col gap-3 lg:w-[26rem] lg:justify-between">
              {shown ? (
                <DetailPanel scene={scene} selection={shown} onClose={() => setSelection(null)} />
              ) : (
                <span />
              )}
              <OpsList
                scene={scene}
                nowMs={sceneNow()}
                selection={shown}
                onSelect={interaction.select}
              />
            </div>
          </div>
        )}
      </div>

      {helpOpen && <ShortcutsDialog onClose={() => setHelpOpen(false)} />}
    </div>
  );
}
