import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { OrdersView } from "@/features/ops/orders-view";

export const metadata: Metadata = { title: "Orders" };

export default function OrdersPage() {
  return (
    <>
      <PageHeader
        title="Orders"
        description="Customer orders and their fulfilment status. Click a row for its shipments."
      />
      {/* useSearchParams (filters live in the URL) needs a Suspense boundary. */}
      <Suspense
        fallback={<div aria-busy="true" className="h-64 animate-pulse rounded-xl bg-surface" />}
      >
        <OrdersView />
      </Suspense>
    </>
  );
}
