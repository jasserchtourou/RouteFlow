import { humanize, toFleetMapData, toMapVehicle } from "@/features/tracking/mappers";
import { VEHICLES, WAREHOUSES } from "./fixtures/fleet";

describe("humanize", () => {
  it("turns enum values into readable labels", () => {
    expect(humanize("REFRIGERATED_TRUCK")).toBe("Refrigerated truck");
    expect(humanize("IN_TRANSIT")).toBe("In transit");
  });
});

describe("toMapVehicle", () => {
  it("skips vehicles without a position and unknown statuses", () => {
    expect(toMapVehicle(VEHICLES[2])).toBeNull();
    expect(toMapVehicle({ ...VEHICLES[0], status: "TELEPORTING" })).toBeNull();
  });
});

describe("toFleetMapData", () => {
  const data = toFleetMapData(VEHICLES, WAREHOUSES);

  it("drops undrawable vehicles but reports how many", () => {
    expect(data.vehicles).toHaveLength(2);
    expect(data.withoutPosition).toBe(1);
  });

  it("lists in-transit vehicles first", () => {
    expect(data.vehicles.map((v) => v.registration)).toEqual(["B-RF 1074", "B-RF 1259"]);
  });

  it("maps warehouses with rounded utilization", () => {
    expect(data.warehouses[0]).toMatchObject({ code: "WH-GAR", utilizationPct: 96, lat: 52.42 });
  });
});
