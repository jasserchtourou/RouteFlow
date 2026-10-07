import { Snowflake } from "lucide-react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatDuration } from "@/lib/format";
import type { ShipmentRow, ShipmentStatus } from "./types";

const STATUS_LABEL: Record<ShipmentStatus, string> = {
  CREATED: "Created",
  PICKED: "Picked",
  PACKED: "Packed",
  LOADED: "Loaded",
  IN_TRANSIT: "In transit",
  OUT_FOR_DELIVERY: "Out for delivery",
  DELIVERED: "Delivered",
};

function statusTone(row: ShipmentRow): Tone {
  if (row.delayMinutes > 0) return "danger";
  return row.status === "DELIVERED" ? "success" : "info";
}

export function ShipmentsTable({ rows }: { rows: ShipmentRow[] }) {
  return (
    <Card className="overflow-hidden p-0">
      <h2 className="px-5 pt-5 pb-3 text-base font-semibold">Shipments</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <thead className="text-xs text-muted">
            <tr className="border-y border-border">
              <th scope="col" className="px-5 py-2 font-medium">
                Shipment
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Route
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Status
              </th>
              <th scope="col" className="px-5 py-2 text-right font-medium">
                ETA
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.shipmentNumber} className="border-b border-border last:border-0">
                <td className="px-5 py-3 font-mono">
                  {row.shipmentNumber}
                  {row.coldChain && (
                    <Snowflake
                      aria-label="Cold chain"
                      className="ml-2 inline size-3.5 text-accent"
                    />
                  )}
                </td>
                <td className="px-3 py-3">
                  {row.origin} → {row.destination}
                </td>
                <td className="px-3 py-3">
                  <Badge tone={statusTone(row)}>{STATUS_LABEL[row.status]}</Badge>
                  {row.delayMinutes > 0 && (
                    <span className="ml-2 text-xs text-danger">
                      +{formatDuration(row.delayMinutes)} late
                    </span>
                  )}
                </td>
                <td className="px-5 py-3 text-right tabular-nums">
                  {row.etaMinutes < 0 ? "overdue" : `in ${formatDuration(row.etaMinutes)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
