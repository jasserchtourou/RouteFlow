/** "5 min ago", "2 h ago", "3 d ago". */
export function formatAgo(minutes: number): string {
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${Math.round(minutes)} min ago`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)} h ago`;
  return `${Math.round(minutes / (60 * 24))} d ago`;
}

/** "07 Oct, 14:30" in the user's time zone. */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Duration as "45 min" or "2 h 05 min". */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m === 0 ? `${h} h` : `${h} h ${String(m).padStart(2, "0")} min`;
}

export function formatPercent(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

/** Signed change: "+1.3" / "-0.4" / "0.0". */
export function formatSigned(value: number, digits = 1): string {
  const text = value.toFixed(digits);
  return value > 0 ? `+${text}` : text;
}
