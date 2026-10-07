"use client";

import { animate } from "animejs";
import { useLayoutEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/motion";

interface AnimatedNumberProps {
  value: number;
  /** Must be a stable reference (define it at module level) or the count restarts on every render. */
  format?: (value: number) => string;
  className?: string;
}

const defaultFormat = (value: number): string => String(Math.round(value));

/**
 * Counts from the previous value to the new one. The final text is always rendered first, so
 * server output, tests and reduced-motion users see the correct number without animation.
 */
export function AnimatedNumber({ value, format = defaultFormat, className }: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  // Only updated when an animation finishes, so React Strict Mode's double effect still animates.
  const shown = useRef(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion() || shown.current === value) {
      shown.current = value;
      el.textContent = format(value);
      return;
    }
    const state = { current: shown.current };
    const animation = animate(state, {
      current: value,
      duration: 900,
      ease: "outExpo",
      onUpdate: () => {
        el.textContent = format(state.current);
      },
      onComplete: () => {
        shown.current = value;
        el.textContent = format(value);
      },
    });
    return () => {
      animation.pause();
      el.textContent = format(value);
    };
  }, [value, format]);

  return (
    <span ref={ref} className={className}>
      {format(value)}
    </span>
  );
}
