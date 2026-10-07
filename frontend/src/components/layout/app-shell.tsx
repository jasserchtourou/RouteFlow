"use client";

import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { useStoredState } from "@/hooks/use-stored-state";
import { cn } from "@/lib/utils";
import { Topbar } from "@/components/layout/topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  // Remember the path the drawer was opened on: navigating elsewhere closes it without an effect.
  const [openedOn, setOpenedOn] = useState<string | null>(null);
  const drawerOpen = openedOn === pathname;
  const closeDrawer = () => setOpenedOn(null);
  const [collapsed, setCollapsed] = useStoredState("sidebar:collapsed", false);

  return (
    <div className="flex h-dvh">
      <aside
        className={cn(
          "hidden shrink-0 border-r border-border bg-surface transition-[width] duration-200 lg:block",
          collapsed ? "w-[4.5rem]" : "w-60",
        )}
      >
        <Sidebar collapsed={collapsed} />
      </aside>

      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation"
        >
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/60"
            onClick={closeDrawer}
          />
          <aside className="relative h-full w-64 border-r border-border bg-surface">
            <Sidebar onNavigate={closeDrawer} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onMenu={() => setOpenedOn(pathname)}
          sidebarCollapsed={collapsed}
          onToggleSidebar={() => setCollapsed(!collapsed)}
        />
        <main id="main" className="flex-1 overflow-y-auto p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
