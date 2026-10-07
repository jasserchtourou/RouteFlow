import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { TrackingView } from "@/features/tracking/tracking-view";

export const metadata: Metadata = { title: "Tracking" };

export default function TrackingPage() {
  return (
    <>
      <PageHeader
        title="Tracking"
        description="Live fleet positions and warehouse status across the network."
      />
      <TrackingView />
    </>
  );
}
