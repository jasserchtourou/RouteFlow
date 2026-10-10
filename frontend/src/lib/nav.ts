import {
  Boxes,
  LayoutDashboard,
  Map,
  PackageSearch,
  Route,
  ScrollText,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/orders", label: "Orders", icon: Boxes },
  { href: "/shipments", label: "Shipments", icon: PackageSearch },
  { href: "/warehouses", label: "Warehouses", icon: Warehouse },
  { href: "/routes", label: "Routes", icon: Route },
  { href: "/tracking", label: "Tracking", icon: Map },
  { href: "/events", label: "Events", icon: ScrollText },
];

/** A nav item is active on its own path and on any nested path (/orders/ORD-1). */
export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
