"use client";

import { animate, stagger } from "animejs";
import { useLayoutEffect, useRef, type HTMLAttributes } from "react";
import { prefersReducedMotion } from "@/lib/motion";

/** Fades and lifts its direct children in one after another when it first appears. */
export function Reveal({ children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;
    const animation = animate(Array.from(el.children), {
      opacity: [0, 1],
      translateY: [16, 0],
      delay: stagger(70),
      duration: 600,
      ease: "outCubic",
    });
    return () => {
      animation.pause();
      for (const child of Array.from(el.children) as HTMLElement[]) {
        child.style.opacity = "";
        child.style.transform = "";
      }
    };
  }, []);

  return (
    <div ref={ref} {...props}>
      {children}
    </div>
  );
}
