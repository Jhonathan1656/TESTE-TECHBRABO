import type { BatchStatus, FreshnessStatus, Severity, TableState } from "../api/types";

export type Tone = "neutral" | "success" | "warning" | "error" | "info" | "primary";

const FRESHNESS_TONES: Record<FreshnessStatus, Tone> = {
  fresh: "success",
  due: "warning",
  overdue: "error",
  never_checked: "neutral",
};

const BATCH_TONES: Record<BatchStatus, Tone> = {
  pending_review: "warning",
  published: "success",
  rejected: "neutral",
  failed: "error",
};

const SEVERITY_TONES: Record<Severity, Tone> = {
  error: "error",
  warning: "warning",
  info: "info",
};

const TABLE_STATE_TONES: Record<TableState, Tone> = {
  current: "success",
  scheduled: "info",
  expired: "neutral",
  superseded: "neutral",
};

export const freshnessTone = (status: FreshnessStatus): Tone => FRESHNESS_TONES[status];
export const batchStatusTone = (status: BatchStatus): Tone => BATCH_TONES[status];
export const severityTone = (severity: Severity): Tone => SEVERITY_TONES[severity];
export const tableStateTone = (state: TableState): Tone => TABLE_STATE_TONES[state];

export function trustTone(level: number): Tone {
  if (level >= 3) {
    return "primary";
  }
  return level === 2 ? "info" : "neutral";
}
