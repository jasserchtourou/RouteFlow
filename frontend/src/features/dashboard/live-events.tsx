"use client";

import { animate, stagger } from "animejs";
import { useEffect, useRef } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatAgo } from "@/lib/format";
import { prefersReducedMotion } from "@/lib/motion";
import type { LiveEvent } from "./types";

const SEVERITY_TONE: Record<LiveEvent["severity"], Tone> = {
  CRITICAL: "danger",
  HIGH: "danger",
  MEDIUM: "warning",
  LOW: "neutral",
  INFO: "info",
};

export function LiveEvents({ events }: { events: LiveEvent[] }) {
  const listRef = useRef<HTMLUListElement>(null);
  const seen = useRef(new Set<string>());

  // Slide in only the events that were not on screen before, so a refresh does not replay them.
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const fresh = Array.from(list.querySelectorAll<HTMLElement>("[data-event-id]")).filter(
      (el) => !seen.current.has(el.dataset.eventId ?? ""),
    );
    for (const event of events) seen.current.add(event.id);
    if (fresh.length === 0 || prefersReducedMotion()) return;
    const animation = animate(fresh, {
      opacity: [0, 1],
      translateX: [-18, 0],
      delay: stagger(80),
      duration: 500,
      ease: "outCubic",
    });
    return () => {
      animation.pause();
      for (const el of fresh) {
        el.style.opacity = "";
        el.style.transform = "";
      }
    };
  }, [events]);

  return (
    <Card className="flex flex-col">
      <h2 className="mb-4 text-base font-semibold">Live events</h2>
      {events.length === 0 ? (
        <p className="text-sm text-muted">No active exceptions. Everything is on track.</p>
      ) : (
        <ul ref={listRef} className="flex flex-col divide-y divide-border">
          {events.map((event) => (
            <li
              key={event.id}
              data-event-id={event.id}
              className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{event.title}</span>
                <Badge tone={SEVERITY_TONE[event.severity]}>
                  {event.severity === "INFO" ? "Info" : event.severity.toLowerCase()}
                </Badge>
              </div>
              <p className="text-sm text-muted">{event.detail}</p>
              <p className="text-xs text-muted">
                <span className="font-mono">{event.shipmentNumber}</span> ·{" "}
                {formatAgo(event.minutesAgo)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
