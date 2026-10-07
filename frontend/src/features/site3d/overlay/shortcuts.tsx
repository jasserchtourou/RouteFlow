"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";

export interface ShortcutHandlers {
  search: () => void;
  panels: () => void;
  fullscreen: () => void;
  reset: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  rotateLeft: () => void;
  rotateRight: () => void;
  help: () => void;
  escape: () => void;
}

const KEYS: Record<string, keyof ShortcutHandlers> = {
  "/": "search",
  h: "panels",
  f: "fullscreen",
  r: "reset",
  "+": "zoomIn",
  "=": "zoomIn",
  "-": "zoomOut",
  "[": "rotateLeft",
  "]": "rotateRight",
  "?": "help",
  Escape: "escape",
};

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName);
}

/** Single-key shortcuts for the site view; ignored while typing or with modifier keys held. */
export function useSiteShortcuts(handlers: ShortcutHandlers): void {
  const ref = useRef(handlers);
  useEffect(() => {
    ref.current = handlers;
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const action = KEYS[event.key] ?? KEYS[event.key.toLowerCase()];
      if (!action) return;
      // Escape must work everywhere (to leave the search box); the rest only outside inputs.
      if (action !== "escape" && isTyping(event.target)) return;
      event.preventDefault();
      ref.current[action]();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}

const SHORTCUTS: [string, string][] = [
  ["/", "Search the site"],
  ["H", "Hide or show all panels"],
  ["F", "Full screen"],
  ["R", "Reset the view"],
  ["+  /  -", "Zoom in / out"],
  ["[  /  ]", "Rotate left / right"],
  ["Esc", "Clear the selection"],
  ["?", "This list"],
];

export function ShortcutsDialog({ onClose }: { onClose: () => void }) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => close.current?.focus(), []);

  return (
    <div
      className="pointer-events-auto absolute inset-0 z-30 grid place-items-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
        className="w-full max-w-sm rounded-2xl border border-border bg-surface p-5 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "Escape") onClose();
        }}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">Keyboard shortcuts</h2>
          <button
            ref={close}
            type="button"
            aria-label="Close shortcuts"
            onClick={onClose}
            className="grid size-8 place-items-center rounded-lg text-muted hover:bg-surface-hover"
          >
            <X aria-hidden className="size-4" />
          </button>
        </div>
        <dl className="divide-y divide-border">
          {SHORTCUTS.map(([keys, action]) => (
            <div key={keys} className="flex items-center justify-between py-2 text-sm">
              <dt className="text-muted">{action}</dt>
              <dd>
                <kbd className="rounded border border-border bg-background px-2 py-0.5 font-mono text-xs">
                  {keys}
                </kbd>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
