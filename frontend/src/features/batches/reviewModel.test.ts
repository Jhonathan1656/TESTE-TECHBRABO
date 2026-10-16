import { buildCellKey, buildSeverityIndex, describeChangeDirection, formatPlainMoney } from "./reviewModel";
import { buildIssue } from "./reviewFixtures";

describe("buildSeverityIndex", () => {
  it("keeps the worst open severity per cell and per plan", () => {
    const index = buildSeverityIndex([
      buildIssue({ id: "1", severity: "warning" }),
      buildIssue({ id: "2", severity: "error" }),
      buildIssue({ id: "3", severity: "warning", age_band: null }),
    ]);

    expect(index.cells.get(buildCellKey("plan-a", 1))).toBe("error");
    expect(index.plans.get("plan-a")).toBe("warning");
  });

  it("ignores acknowledged, resolved and informational issues", () => {
    const index = buildSeverityIndex([
      buildIssue({ id: "1", status: "acknowledged" }),
      buildIssue({ id: "2", status: "resolved", severity: "error" }),
      buildIssue({ id: "3", severity: "info" }),
    ]);

    expect(index.cells.size).toBe(0);
  });
});

describe("review formatting helpers", () => {
  it("formats values for the correction input", () => {
    expect(formatPlainMoney("1234.5")).toBe("1.234,50");
    expect(formatPlainMoney(null)).toBe("");
  });

  it("classifies the change direction", () => {
    expect(describeChangeDirection("0.098")).toBe("up");
    expect(describeChangeDirection("-0.01")).toBe("down");
    expect(describeChangeDirection(null)).toBe("flat");
  });
});
