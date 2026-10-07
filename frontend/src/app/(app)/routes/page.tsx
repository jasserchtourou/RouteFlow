import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { RoutesView } from "@/features/ops/routes-view";

export const metadata: Metadata = { title: "Routes" };

export default function RoutesPage() {
  return (
    <>
      <PageHeader
        title="Routes"
        description="Routes with a computed risk score. Switch to the ranked view to see what to investigate first."
      />
      {/* useSearchParams (filters live in the URL) needs a Suspense boundary. */}
      <Suspense
        fallback={<div aria-busy="true" className="h-64 animate-pulse rounded-xl bg-surface" />}
      >
        <RoutesView />
      </Suspense>
    </>
  );
}
