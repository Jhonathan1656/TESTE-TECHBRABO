import type { BatchDetail, ExtractedPlan, Severity, ValidationIssue } from "../../shared/api/types";

export const AGE_BAND_LABELS = ["0–18", "19–23", "24–28", "29–33", "34–38", "39–43", "44–48", "49–53", "54–58", "59+"];

const SEVERITY_RANK: Record<Severity, number> = { error: 3, warning: 2, info: 1 };
const plainMoneyFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export interface SeverityIndex {
  cells: Map<string, Severity>;
  plans: Map<string, Severity>;
}

export function buildCellKey(extractedPlanId: string, ageBand: number): string {
  return `${extractedPlanId}:${ageBand}`;
}

export function buildSeverityIndex(issues: ValidationIssue[]): SeverityIndex {
  const index: SeverityIndex = { cells: new Map(), plans: new Map() };
  issues
    .filter((issue) => issue.status === "open" && issue.severity !== "info" && issue.extracted_plan_id)
    .forEach((issue) => {
      const planId = issue.extracted_plan_id!;
      if (issue.age_band) {
        keepWorst(index.cells, buildCellKey(planId, issue.age_band), issue.severity);
      } else {
        keepWorst(index.plans, planId, issue.severity);
      }
    });
  return index;
}

export function findExtractedPlan(batch: BatchDetail, extractedPlanId: string | null): ExtractedPlan | undefined {
  return batch.plans.find((plan) => plan.id === extractedPlanId);
}

export function formatPlainMoney(value: string | null | undefined): string {
  return value ? plainMoneyFormatter.format(Number(value)) : "";
}

export function describeChangeDirection(change: string | null): "up" | "down" | "flat" {
  const value = Number(change ?? 0);
  if (value > 0.00005) {
    return "up";
  }
  return value < -0.00005 ? "down" : "flat";
}

function keepWorst(map: Map<string, Severity>, key: string, severity: Severity): void {
  const current = map.get(key);
  if (!current || SEVERITY_RANK[severity] > SEVERITY_RANK[current]) {
    map.set(key, severity);
  }
}
