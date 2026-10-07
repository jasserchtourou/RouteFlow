import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const TONES: Record<Tone, string> = {
  neutral: "bg-surface-hover text-muted",
  info: "bg-accent/15 text-accent",
  success: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-danger/15 text-danger",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

/** Status pill. Always carries text, so meaning never depends on colour alone. */
export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
