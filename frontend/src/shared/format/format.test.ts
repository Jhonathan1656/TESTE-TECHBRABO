import { daysBetween, formatChange, formatIsoDate, formatMoney, parseAges, parseBrazilianMoney } from "./format";

describe("formatMoney", () => {
  it("formats decimal strings as Brazilian currency", () => {
    expect(formatMoney("1234.5")).toBe("R$ 1.234,50");
  });

  it("renders a dash for missing values", () => {
    expect(formatMoney(null)).toBe("—");
  });
});

describe("formatChange", () => {
  it("adds an explicit plus sign to increases", () => {
    expect(formatChange("0.098")).toBe("+9,8%");
  });

  it("keeps the minus sign of decreases", () => {
    expect(formatChange("-0.0351")).toBe("-3,51%");
  });
});

describe("formatIsoDate", () => {
  it("does not shift dates across time zones", () => {
    expect(formatIsoDate("2026-11-01")).toBe("01/11/2026");
  });
});

describe("daysBetween", () => {
  it("counts calendar days between ISO dates", () => {
    expect(daysBetween("2026-10-16", "2026-11-01")).toBe(16);
  });
});

describe("parseAges", () => {
  it("accepts commas, semicolons and spaces", () => {
    expect(parseAges("34, 32;5 61")).toEqual([34, 32, 5, 61]);
  });

  it("rejects invalid ages", () => {
    expect(parseAges("34, abc")).toBeNull();
    expect(parseAges("130")).toBeNull();
    expect(parseAges("  ")).toBeNull();
  });
});

describe("parseBrazilianMoney", () => {
  it("converts Brazilian notation to a decimal string", () => {
    expect(parseBrazilianMoney("R$ 1.234,56")).toBe("1234.56");
    expect(parseBrazilianMoney("878,13")).toBe("878.13");
    expect(parseBrazilianMoney("950")).toBe("950.00");
  });

  it("rejects ambiguous text", () => {
    expect(parseBrazilianMoney("12,3,4")).toBeNull();
    expect(parseBrazilianMoney("abc")).toBeNull();
  });
});
