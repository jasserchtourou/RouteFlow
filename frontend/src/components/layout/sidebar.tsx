"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Truck } from "lucide-react";
import { NAV_ITEMS, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function Sidebar({
  onNavigate,
  collapsed = false,
}: {
  onNavigate?: () => void;
  /** Icons only (desktop). Labels stay available to screen readers and as tooltips. */
  collapsed?: boolean;
}) {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className={cn("flex h-full flex-col gap-1 p-3", collapsed && "items-center px-2")}
    >
      <Link
        href="/dashboard"
        title="RouteFlow"
        className={cn("mb-4 flex items-center gap-2 px-3 py-2", collapsed && "px-0")}
        onClick={onNavigate}
      >
        <span className="grid size-8 place-items-center rounded-lg bg-linear-to-br from-accent to-[#2f5bd8] text-accent-fg shadow-[0_0_16px_-4px_var(--accent)]">
          <Truck aria-hidden className="size-4" />
        </span>
        <span className={cn("text-lg font-semibold tracking-tight", collapsed && "sr-only")}>
          RouteFlow
        </span>
      </Link>
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = isActivePath(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              collapsed && "justify-center px-0 size-11",
              active
                ? "bg-accent/15 text-accent shadow-[inset_3px_0_0_var(--accent),0_0_18px_-6px_var(--accent)]"
                : "text-muted hover:bg-surface-hover hover:text-foreground",
            )}
          >
            <Icon aria-hidden className="size-4" />
            <span className={cn(collapsed && "sr-only")}>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
