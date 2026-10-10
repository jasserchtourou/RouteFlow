"use client";

import { Bell, Menu, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";

export function Topbar({
  onMenu,
  sidebarCollapsed,
  onToggleSidebar,
}: {
  onMenu: () => void;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="relative z-10 flex h-14 items-center gap-3 border-b border-border bg-surface/80 px-4 backdrop-blur-md">
      <button
        type="button"
        onClick={onMenu}
        aria-label="Open navigation"
        className="grid size-10 place-items-center rounded-lg text-muted hover:bg-surface-hover lg:hidden"
      >
        <Menu aria-hidden className="size-5" />
      </button>
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-pressed={sidebarCollapsed}
        title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="hidden size-10 place-items-center rounded-lg text-muted hover:bg-surface-hover hover:text-foreground lg:grid"
      >
        {sidebarCollapsed ? (
          <PanelLeftOpen aria-hidden className="size-5" />
        ) : (
          <PanelLeftClose aria-hidden className="size-5" />
        )}
      </button>
      <label className="relative max-w-md flex-1">
        <span className="sr-only">Search orders, shipments, routes</span>
        <Search
          aria-hidden
          className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
        />
        <input
          type="search"
          disabled
          placeholder="Search orders, shipments, routes…"
          className="h-9 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm placeholder:text-muted disabled:cursor-not-allowed"
        />
      </label>
      <div className="ml-auto flex items-center gap-3">
        <button
          type="button"
          aria-label="Notifications"
          className="grid size-10 place-items-center rounded-lg text-muted hover:bg-surface-hover"
        >
          <Bell aria-hidden className="size-5" />
        </button>
      </div>
    </header>
  );
}
