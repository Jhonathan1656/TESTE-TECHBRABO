import type { BatchReviewSummary } from "../../shared/api/types";
import { formatChange } from "../../shared/format/format";
import { t } from "../../shared/i18n/translate";

interface SummaryCell {
  label: string;
  value: string;
  tone?: "error" | "warning";
}

export function ReviewSummary({ summary }: { summary: BatchReviewSummary }) {
  const cells: SummaryCell[] = [
    { label: t("review.summaryPlans"), value: String(summary.plans) },
    { label: t("review.summaryPrices"), value: String(summary.prices) },
    { label: t("review.summaryChanged"), value: `${summary.changed_prices}/${summary.compared_prices}` },
    { label: t("review.summaryMedian"), value: formatChange(summary.median_change) },
    { label: t("review.summaryCorrected"), value: String(summary.corrected_prices) },
    {
      label: t("review.summaryErrors"),
      value: String(summary.open_errors),
      tone: summary.open_errors ? "error" : undefined,
    },
    {
      label: t("review.summaryWarnings"),
      value: String(summary.open_warnings),
      tone: summary.open_warnings ? "warning" : undefined,
    },
  ];
  return (
    <dl className="summary-grid">
      {cells.map((cell) => (
        <div key={cell.label} className="summary-cell">
          <dt className="meta-label">{cell.label}</dt>
          <dd className={cell.tone ? `summary-value tone-${cell.tone}` : "summary-value"}>{cell.value}</dd>
        </div>
      ))}
    </dl>
  );
}
