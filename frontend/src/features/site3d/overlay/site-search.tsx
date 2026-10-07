"use client";

import { Search } from "lucide-react";
import { useId, useMemo, useRef, useState, type KeyboardEvent, type Ref } from "react";
import { humanize } from "@/features/tracking/mappers";
import { cn } from "@/lib/utils";
import type { Selection, SiteScene } from "../model";

interface Result {
  selection: Selection;
  kind: string;
  label: string;
  hint: string;
  /** Lower-case text the query is matched against. */
  haystack: string;
}

const MAX_RESULTS = 8;

/** Everything in the scene that can be found by typing. */
export function searchIndex(scene: SiteScene): Result[] {
  const docks = scene.docks.map<Result>((d) => ({
    selection: { kind: "dock", id: d.id },
    kind: "Dock",
    label: d.code,
    hint: humanize(d.state),
    haystack: `${d.code} dock ${d.state}`.toLowerCase(),
  }));
  const trucks = scene.visits.map<Result>((v) => ({
    selection: { kind: "truck", id: v.id },
    kind: "Truck",
    label: v.truckCode,
    hint: `${v.carrier} · ${humanize(v.state)}`,
    haystack:
      `${v.truckCode} ${v.carrier} ${v.dockCode} ${v.shipment?.number ?? ""} ${v.shipment?.destination ?? ""} truck`.toLowerCase(),
  }));
  const forklifts = scene.equipment.map<Result>((e) => ({
    selection: { kind: "forklift", id: e.id },
    kind: humanize(e.type),
    label: e.code,
    hint: humanize(e.status),
    haystack: `${e.code} ${e.type} forklift ${e.status}`.toLowerCase(),
  }));
  const pallets = scene.pallets.map<Result>((p) => ({
    selection: { kind: "pallet", id: p.id },
    kind: "Pallet",
    label: p.id,
    hint: p.name,
    haystack: `${p.id} ${p.sku} ${p.name} pallet`.toLowerCase(),
  }));
  return [...docks, ...trucks, ...forklifts, ...pallets];
}

export function filterResults(index: Result[], query: string): Result[] {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return [];
  return index.filter((r) => terms.every((t) => r.haystack.includes(t))).slice(0, MAX_RESULTS);
}

/** Accessible combobox (WAI-ARIA 1.2 pattern): type, arrow keys, Enter selects, Esc clears. */
export function SiteSearch({
  scene,
  onSelect,
  inputRef,
}: {
  scene: SiteScene;
  onSelect: (selection: Selection) => void;
  inputRef: Ref<HTMLInputElement>;
}) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);
  const listId = useId();
  const index = useMemo(() => searchIndex(scene), [scene]);
  const results = useMemo(() => filterResults(index, query), [index, query]);
  const wrapper = useRef<HTMLDivElement>(null);
  const showList = open && query.trim() !== "";

  const choose = (result: Result) => {
    onSelect(result.selection);
    setQuery("");
    setOpen(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((a) => Math.min(a + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (event.key === "Enter" && results[active]) {
      event.preventDefault();
      choose(results[active]);
    } else if (event.key === "Escape") {
      setQuery("");
      setOpen(false);
      event.currentTarget.blur();
    }
  };

  return (
    <div
      ref={wrapper}
      className="pointer-events-auto relative w-full sm:w-72"
      onBlur={(event) => {
        if (!wrapper.current?.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <Search
        aria-hidden
        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
      />
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-label="Search site"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && results[active] ? `${listId}-${active}` : undefined}
        placeholder="Search trucks, docks, forklifts, pallets…"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="h-11 w-full rounded-xl border border-border bg-surface/90 pl-9 pr-9 text-sm shadow-xl backdrop-blur-md placeholder:text-muted"
      />
      <kbd
        aria-hidden
        className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-border px-1.5 text-[10px] text-muted sm:block"
      >
        /
      </kbd>
      {showList && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Search results"
          className="absolute left-0 right-0 top-full z-20 mt-1.5 overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
        >
          {results.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-muted">Nothing matches “{query}”.</li>
          ) : (
            results.map((result, i) => (
              <li
                key={`${result.selection.kind}-${result.selection.id}`}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(result)}
                onMouseEnter={() => setActive(i)}
                className={cn(
                  "flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm",
                  i === active && "bg-accent/15",
                )}
              >
                <span className="min-w-0">
                  <span className="font-medium">{result.label}</span>
                  <span className="ml-2 text-xs text-muted">{result.hint}</span>
                </span>
                <span className="shrink-0 text-[11px] uppercase tracking-wide text-muted">
                  {result.kind}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
