import { toDashboardData, toFlow, toShipmentRow } from "@/features/dashboard/mappers";
import { EXCEPTIONS, NOW, OVERVIEW, SHIPMENTS } from "./fixtures/api";

describe("toDashboardData", () => {
  const data = toDashboardData(OVERVIEW, SHIPMENTS, EXCEPTIONS, NOW);

  it("maps KPIs, preferring the rate for today", () => {
    expect(data.kpis).toMatchObject({
      activeShipments: 42,
      delayedShipments: 6,
      onTimeRate: 91.3,
      onTimeChangePts: 1.3,
      criticalExceptions: 1,
      vehiclesOperational: 17,
    });
  });

  it("falls back to the 7-day rate before the first delivery of the day", () => {
    const quiet = {
      ...OVERVIEW,
      delivery_performance: {
        ...OVERVIEW.delivery_performance,
        today: { delivered: 0, on_time: 0, on_time_rate: null },
      },
    };
    expect(toDashboardData(quiet, SHIPMENTS, EXCEPTIONS, NOW).kpis.onTimeRate).toBe(94);
  });

  it("sorts warehouses by utilization, fullest first, with rounded percentages", () => {
    expect(data.warehouses.map((w) => [w.name, w.utilizationPct])).toEqual([
      ["Garbsen DC", 96],
      ["Hannover Central", 78],
    ]);
  });

  it("turns exceptions into events with titles and ages", () => {
    expect(data.events[0]).toMatchObject({
      title: "Temperature deviation",
      severity: "CRITICAL",
      minutesAgo: 4,
    });
  });
});

describe("toFlow", () => {
  it("counts pre-dispatch shipments as the warehouse stage", () => {
    const flow = toFlow(OVERVIEW);
    expect(flow.map((s) => s.count)).toEqual([58, 19, 42, 12, 23]);
  });
});

describe("toShipmentRow", () => {
  it("computes minutes to ETA (negative once overdue) and the cold-chain flag", () => {
    const [late, onTime] = SHIPMENTS.items.map((s) => toShipmentRow(s, NOW));
    expect(late).toMatchObject({ etaMinutes: -35, delayMinutes: 35, coldChain: true });
    expect(onTime).toMatchObject({ etaMinutes: 160, delayMinutes: 0, coldChain: false });
  });
});
