import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { ShipmentsView } from "@/features/ops/shipments-view";

export const metadata: Metadata = { title: "Shipments" };

export default function ShipmentsPage() {
  return (
    <>
      <PageHeader
        title="Shipments"
        description="Every shipment with its status, delay and open exceptions. Click a row for the tracking history."
      />
      {/* useSearchParams (filters live in the URL) needs a Suspense boundary. */}
      <Suspense
        fallback={<div aria-busy="true" className="h-64 animate-pulse rounded-xl bg-surface" />}
      >
        <ShipmentsView />
      </Suspense>
    </>
  );
}
