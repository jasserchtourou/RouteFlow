"use client";

import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

/**
 * A slide-over detail panel. It is not modal: the list stays usable behind it on wide screens
 * (click another row to switch), Esc or the close button dismiss it, and focus moves into it
 * when it opens so keyboard and screen-reader users land on the content.
 */
export function Drawer({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButton.current?.focus();
  }, [title]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <button
        type="button"
        aria-label="Close details"
        tabIndex={-1}
        onClick={onClose}
        className="fixed inset-0 z-30 bg-black/40 lg:hidden"
      />
      <aside
        aria-label={`${title} details`}
        className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-border bg-surface shadow-2xl"
      >
        <header className="flex items-start justify-between gap-3 border-b border-border p-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold">{title}</h2>
            {subtitle && <p className="truncate text-sm text-muted">{subtitle}</p>}
          </div>
          <button
            ref={closeButton}
            type="button"
            aria-label="Close details panel"
            onClick={onClose}
            className="grid size-9 shrink-0 place-items-center rounded-lg text-muted hover:bg-surface-hover hover:text-foreground"
          >
            <X aria-hidden className="size-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </aside>
    </>
  );
}

/** A label/value list used inside drawers. */
export function Facts({ items }: { items: readonly [string, ReactNode][] }) {
  return (
    <dl className="divide-y divide-border/60">
      {items.map(([label, value]) => (
        <div key={label} className="flex items-start justify-between gap-4 py-2 text-sm">
          <dt className="shrink-0 text-muted">{label}</dt>
          <dd className="text-right font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DrawerSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      {children}
    </section>
  );
}
