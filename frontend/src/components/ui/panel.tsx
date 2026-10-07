"use client";

import { ChevronDown, type LucideIcon } from "lucide-react";
import { useId, type ReactNode } from "react";
import { useStoredState } from "@/hooks/use-stored-state";
import { cn } from "@/lib/utils";

interface PanelProps {
  /** Key under which the open/closed state is remembered. */
  id: string;
  /** Accessible name of the region (defaults to the title). */
  label?: string;
  title: string;
  icon?: LucideIcon;
  /** One-line digest shown in the header while the panel is collapsed. */
  summary?: ReactNode;
  defaultOpen?: boolean;
  /** Extra header controls (e.g. a close button). */
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
}

/**
 * A collapsible card. The header is a real button (`aria-expanded`, `aria-controls`); the body
 * animates its height with a CSS grid transition (no measuring, respects reduced motion via the
 * global rule) and is `inert` while closed so hidden controls cannot be tabbed to.
 */
export function Panel({
  id,
  label,
  title,
  icon: Icon,
  summary,
  defaultOpen = true,
  actions,
  className,
  bodyClassName = "px-3 pb-3",
  children,
}: PanelProps) {
  const [open, setOpen] = useStoredState(`panel:${id}`, defaultOpen);
  const bodyId = useId();

  return (
    <section
      aria-label={label ?? title}
      className={cn(
        "rounded-xl border border-border bg-surface/90 shadow-xl backdrop-blur-md",
        className,
      )}
    >
      <header className="flex items-center gap-1 pr-2">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={() => setOpen(!open)}
          className="group flex min-w-0 flex-1 items-center gap-2 rounded-xl px-3 py-2.5 text-left"
        >
          {Icon && <Icon aria-hidden className="size-4 shrink-0 text-accent" />}
          <h2 className="shrink-0 text-sm font-semibold">{title}</h2>
          {!open && summary && (
            <span className="min-w-0 truncate text-xs text-muted">{summary}</span>
          )}
          <ChevronDown
            aria-hidden
            className={cn(
              "ml-auto size-4 shrink-0 text-muted transition-transform duration-200 group-hover:text-foreground",
              !open && "-rotate-90",
            )}
          />
          <span className="sr-only">{open ? "Collapse" : "Expand"}</span>
        </button>
        {actions}
      </header>
      <div
        id={bodyId}
        className={cn(
          "grid transition-[grid-template-rows] duration-200 ease-out",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="min-h-0 overflow-hidden" inert={!open}>
          <div className={bodyClassName}>{children}</div>
        </div>
      </div>
    </section>
  );
}
