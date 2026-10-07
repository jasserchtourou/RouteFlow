import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { DashboardView } from "@/features/dashboard/dashboard-view";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Network overview: orders, shipments, fleet and warehouse health."
      />
      <DashboardView />
    </>
  );
}
