"use client";

import { animate, stagger } from "animejs";
import { ChevronRight } from "lucide-react";
import { Fragment, useEffect, useRef } from "react";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Card } from "@/components/ui/card";
import { prefersReducedMotion } from "@/lib/motion";
import type { FlowStage } from "./types";

export function LogisticsFlow({ stages }: { stages: FlowStage[] }) {
  const listRef = useRef<HTMLOListElement>(null);

  // A wave of motion travels left to right along the arrows: work moving through the pipeline.
  useEffect(() => {
    const list = listRef.current;
    if (!list || prefersReducedMotion()) return;
    const arrows = list.querySelectorAll("[data-flow-arrow]");
    const animation = animate(arrows, {
      opacity: [0.25, 1],
      translateX: [-4, 4],
      duration: 700,
      delay: stagger(250),
      loop: true,
      alternate: true,
      ease: "inOutSine",
    });
    return () => {
      animation.pause();
    };
  }, []);

  return (
    <Card>
      <h2 className="mb-4 text-base font-semibold">Logistics flow</h2>
      <ol ref={listRef} className="flex flex-col gap-2 sm:flex-row sm:items-center">
        {stages.map((stage, i) => (
          <Fragment key={stage.key}>
            <li className="flex-1 rounded-lg border border-border bg-background px-4 py-3">
              <p className="text-xs text-muted">{stage.label}</p>
              <p className="text-2xl font-semibold tabular-nums">
                <AnimatedNumber value={stage.count} />
              </p>
              <p className="text-xs text-muted">{stage.caption}</p>
            </li>
            {i < stages.length - 1 && (
              <ChevronRight
                data-flow-arrow
                aria-hidden
                className="hidden size-4 shrink-0 text-accent sm:block"
              />
            )}
          </Fragment>
        ))}
      </ol>
    </Card>
  );
}
