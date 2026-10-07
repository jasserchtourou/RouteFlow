import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { WarehouseList } from "@/features/warehouses/warehouse-list";

export const metadata: Metadata = { title: "Warehouses" };

export default function WarehousesPage() {
  return (
    <>
      <PageHeader
        title="Warehouses"
        description="Capacity, stock and dock activity per site. Open the 3D view to watch trucks and forklifts live."
      />
      <WarehouseList />
    </>
  );
}
