import type { Metadata } from "next";
import { SiteView } from "@/features/site3d/site-view";

export const metadata: Metadata = { title: "Site view" };

export default async function SiteViewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SiteView warehouseId={id} />;
}
