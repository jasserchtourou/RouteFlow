import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        // A faint top-lit gradient and inner highlight give panels some depth, like a game HUD.
        "rounded-xl border border-border bg-surface bg-linear-to-b from-surface-hover/50 to-surface p-5 shadow-[inset_0_1px_0_rgb(255_255_255/0.04),0_8px_24px_-12px_rgb(0_0_0/0.5)]",
        className,
      )}
      {...props}
    />
  );
}
