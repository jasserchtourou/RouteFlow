import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { EventsView } from "@/features/ops/events-view";

export const metadata: Metadata = { title: "Events" };

export default function EventsPage() {
  return (
    <>
      <PageHeader
        title="Events"
        description="Every tracking event across the network, newest first, updated live."
      />
      {/* useSearchParams (filters live in the URL) needs a Suspense boundary. */}
      <Suspense
        fallback={<div aria-busy="true" className="h-64 animate-pulse rounded-xl bg-surface" />}
      >
        <EventsView />
      </Suspense>
    </>
  );
}
