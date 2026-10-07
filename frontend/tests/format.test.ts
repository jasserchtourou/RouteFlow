import { formatAgo, formatDuration, formatPercent, formatSigned } from "@/lib/format";

describe("formatAgo", () => {
  it.each([
    [0, "just now"],
    [5, "5 min ago"],
    [120, "2 h ago"],
    [60 * 24 * 3, "3 d ago"],
  ])("%s min -> %s", (minutes, expected) => {
    expect(formatAgo(minutes)).toBe(expected);
  });
});

describe("formatDuration", () => {
  it.each([
    [45, "45 min"],
    [120, "2 h"],
    [125, "2 h 05 min"],
  ])("%s min -> %s", (minutes, expected) => {
    expect(formatDuration(minutes)).toBe(expected);
  });
});

describe("number formats", () => {
  it("formats percents and signed changes", () => {
    expect(formatPercent(94.24)).toBe("94.2%");
    expect(formatPercent(72.4, 0)).toBe("72%");
    expect(formatSigned(1.3)).toBe("+1.3");
    expect(formatSigned(-0.4)).toBe("-0.4");
    expect(formatSigned(0)).toBe("0.0");
  });
});
