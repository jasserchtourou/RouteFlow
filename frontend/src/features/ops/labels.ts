import type { Tone } from "@/components/ui/badge";

export const ORDER_STATUSES = [
  "PENDING",
  "CONFIRMED",
  "PROCESSING",
  "SHIPPED",
  "DELIVERED",
  "CANCELLED",
];
export const ORDER_PRIORITIES = ["LOW", "NORMAL", "HIGH", "URGENT"];
export const SHIPMENT_STATUSES = [
  "CREATED",
  "PICKED",
  "PACKED",
  "LOADED",
  "IN_TRANSIT",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
];
export const ROUTE_STATUSES = ["PLANNED", "ACTIVE", "DELAYED", "COMPLETED", "CANCELLED"];
export const RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
export const EVENT_TYPES = [
  "CREATED",
  "PICKED",
  "PACKED",
  "LOADED",
  "DEPARTED",
  "CHECKPOINT",
  "ARRIVED_HUB",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
  "DELAY_REPORTED",
  "TEMPERATURE_ALERT",
];

/** "OUT_FOR_DELIVERY" -> "Out for delivery". */
export function label(value: string): string {
  const text = value.toLowerCase().replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const options = (values: readonly string[]) =>
  values.map((v) => ({ value: v, label: label(v) }));

export function orderStatusTone(status: string): Tone {
  if (status === "DELIVERED") return "success";
  if (status === "CANCELLED") return "neutral";
  if (status === "PENDING") return "warning";
  return "info";
}

export function priorityTone(priority: string): Tone {
  if (priority === "URGENT") return "danger";
  if (priority === "HIGH") return "warning";
  return "neutral";
}

export function shipmentTone(status: string, delayed: boolean): Tone {
  if (status === "DELIVERED") return "success";
  return delayed ? "danger" : "info";
}

export function severityTone(severity: string): Tone {
  if (severity === "CRITICAL" || severity === "HIGH") return "danger";
  if (severity === "MEDIUM") return "warning";
  return "neutral";
}

export function routeStatusTone(status: string): Tone {
  if (status === "DELAYED") return "danger";
  if (status === "ACTIVE") return "info";
  if (status === "COMPLETED") return "success";
  return "neutral";
}

export function riskTone(level: string): Tone {
  if (level === "CRITICAL" || level === "HIGH") return "danger";
  if (level === "MEDIUM") return "warning";
  return "success";
}

export function eventTone(type: string): Tone {
  if (type === "TEMPERATURE_ALERT") return "danger";
  if (type === "DELAY_REPORTED") return "warning";
  if (type === "DELIVERED") return "success";
  return "info";
}

/** One-line digest of an event's details, e.g. "+95 min" or "11.2 °C". */
export function eventDetail(details: Record<string, unknown>): string | null {
  const delay = details.delay_minutes;
  if (typeof delay === "number") return `+${delay} min`;
  const temperature = details.temperature_c;
  if (typeof temperature === "number") return `${temperature} °C`;
  return null;
}
