import { NAV_ITEMS, isActivePath } from "@/lib/nav";

describe("isActivePath", () => {
  it("matches the exact path and nested paths", () => {
    expect(isActivePath("/orders", "/orders")).toBe(true);
    expect(isActivePath("/orders/ORD-1", "/orders")).toBe(true);
  });

  it("does not match a path that merely shares a prefix", () => {
    expect(isActivePath("/orders-archive", "/orders")).toBe(false);
    expect(isActivePath("/routes", "/orders")).toBe(false);
  });
});

describe("NAV_ITEMS", () => {
  it("has unique hrefs and covers the planned routes", () => {
    const hrefs = NAV_ITEMS.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
    expect(hrefs).toEqual([
      "/dashboard",
      "/orders",
      "/shipments",
      "/warehouses",
      "/routes",
      "/tracking",
      "/events",
    ]);
  });
});
