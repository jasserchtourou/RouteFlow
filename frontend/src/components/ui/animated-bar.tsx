"use client";

import { animate } from "animejs";
import { useLayoutEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";

/** A bar whose fill grows from its previous width to `pct` (0-100). */
export function AnimatedBar({ pct, className }: { pct: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const shown = useRef(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion() || shown.current === pct) {
      shown.current = pct;
      el.style.width = `${pct}%`;
      return;
    }
    const animation = animate(el, {
      width: [`${shown.current}%`, `${pct}%`],
      duration: 900,
      ease: "outExpo",
      onComplete: () => {
        shown.current = pct;
      },
    });
    return () => {
      animation.pause();
      el.style.width = `${pct}%`;
    };
  }, [pct]);

  return (
    <div ref={ref} className={cn("h-full rounded-full", className)} style={{ width: `${pct}%` }} />
  );
}
