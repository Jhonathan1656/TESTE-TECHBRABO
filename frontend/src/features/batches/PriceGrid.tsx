import { Ban, Link2, PencilLine, Undo2 } from "lucide-react";
import { useEffect, useRef } from "react";

import type { BatchDetail, ExtractedPlan, ExtractedPrice, Severity } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { Button } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { TableScroll } from "../../shared/components/TableScroll";
import { severityTone } from "../../shared/components/tones";
import { formatChange, formatMoney } from "../../shared/format/format";
import { t, tEnum } from "../../shared/i18n/translate";
import { SeverityIcon } from "../dashboard/AlertList";
import { AGE_BAND_LABELS, buildCellKey, describeChangeDirection, type SeverityIndex } from "./reviewModel";

interface PriceGridProps {
  batch: BatchDetail;
  severity: SeverityIndex;
  highlightedCell: string | null;
  canEdit: boolean;
  onSelectCell: (plan: ExtractedPlan, price: ExtractedPrice) => void;
  onMapPlan: (plan: ExtractedPlan) => void;
  onToggleExclusion: (plan: ExtractedPlan) => void;
}

export function PriceGrid(props: PriceGridProps) {
  const { batch } = props;
  return (
    <Card title={t("review.gridTitle")} hint={t("review.gridHint")} flush>
      <TableScroll label={t("review.gridTitle")}>
        <table className="price-grid">
          <thead>
            <tr>
              <th scope="col" className="band-cell">
                {t("review.bandColumn")}
              </th>
              {batch.plans.map((plan) => (
                <PlanHeader key={plan.id} plan={plan} {...props} />
              ))}
            </tr>
          </thead>
          <tbody>
            {AGE_BAND_LABELS.map((label, index) => {
              const band = index + 1;
              return (
                <tr key={label}>
                  <th scope="row" className="band-cell numeric">
                    {label}
                  </th>
                  {batch.plans.map((plan) => (
                    <PriceCell key={plan.id} plan={plan} band={band} {...props} />
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableScroll>
    </Card>
  );
}

function PlanHeader({ plan, canEdit, severity, onMapPlan, onToggleExclusion }: PriceGridProps & { plan: ExtractedPlan }) {
  const planSeverity = plan.is_excluded ? undefined : severity.plans.get(plan.id);
  return (
    <th scope="col" className={plan.is_excluded ? "plan-excluded" : undefined}>
      <div className="plan-head">
        <span className="plan-head-label">{plan.label}</span>
        <span className="plan-head-match">{describeMatch(plan)}</span>
        {planSeverity && <SeverityBadge severity={planSeverity} />}
        {canEdit && (
          <div className="plan-head-actions">
            {!plan.is_excluded && (
              <Button
                size="sm"
                variant="ghost"
                icon={<Link2 size={14} />}
                aria-label={`${t("review.mapPlan")} ${plan.label}`}
                onClick={() => onMapPlan(plan)}
              >
                {t("review.mapPlan")}
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              icon={plan.is_excluded ? <Undo2 size={14} /> : <Ban size={14} />}
              aria-label={`${plan.is_excluded ? t("review.include") : t("review.exclude")} ${plan.label}`}
              onClick={() => onToggleExclusion(plan)}
            >
              {plan.is_excluded ? t("review.include") : t("review.exclude")}
            </Button>
          </div>
        )}
      </div>
    </th>
  );
}

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span>
      <Badge tone={severityTone(severity)} icon={<SeverityIcon severity={severity} size={12} />}>
        {tEnum("severity", severity)}
      </Badge>
    </span>
  );
}

function describeMatch(plan: ExtractedPlan): string {
  if (plan.is_excluded) {
    return t("review.excluded");
  }
  if (!plan.plan) {
    return t("review.planNotMatched");
  }
  const method = tEnum("matchMethod", plan.match_method);
  return plan.plan.name === plan.label ? method : `→ ${plan.plan.name} · ${method}`;
}

function PriceCell({
  plan,
  band,
  severity,
  highlightedCell,
  onSelectCell,
}: PriceGridProps & { plan: ExtractedPlan; band: number }) {
  const ref = useRef<HTMLTableCellElement>(null);
  const price = plan.prices.find((item) => item.age_band === band);
  const key = buildCellKey(plan.id, band);
  const isHighlighted = highlightedCell === key;

  useEffect(() => {
    if (isHighlighted) {
      const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      ref.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center", inline: "center" });
      ref.current?.querySelector("button")?.focus({ preventScroll: true });
    }
  }, [isHighlighted]);

  if (!price) {
    return (
      <td className="price-empty">
        <span aria-hidden="true">{t("common.none")}</span>
        <span className="visually-hidden">{t("review.cellMissing")}</span>
      </td>
    );
  }
  const tone = plan.is_excluded ? undefined : severity.cells.get(key);
  const classes = ["price-cell", tone ? `tone-${tone}` : "", isHighlighted ? "highlight" : "", plan.is_excluded ? "excluded" : ""]
    .filter(Boolean)
    .join(" ");
  const direction = describeChangeDirection(price.change);
  const value = price.final_value ? formatMoney(price.final_value) : price.raw_text;

  return (
    <td ref={ref} className={classes}>
      <button type="button" onClick={() => onSelectCell(plan, price)} aria-label={describeCell(plan, band, price, value, tone)}>
        <span className="price-value">{value}</span>
        {price.previous_value ? (
          <span className="price-previous" title={t("review.previous", { value: formatMoney(price.previous_value) })}>
            <s>{formatMoney(price.previous_value)}</s>
            <span className={`change-chip ${direction}`}>{formatChange(price.change)}</span>
          </span>
        ) : (
          <span className="price-previous">{t("review.noPrevious")}</span>
        )}
        {price.corrected_value && (
          <span className="corrected-mark">
            <PencilLine size={11} aria-hidden="true" />
            {t("review.corrected")}
          </span>
        )}
      </button>
    </td>
  );
}

/** The visible cell is a compact visual summary; the accessible name spells out every part of it. */
function describeCell(
  plan: ExtractedPlan,
  band: number,
  price: ExtractedPrice,
  value: string,
  tone: Severity | undefined,
): string {
  return [
    t("review.cellLabel", { plan: plan.label, band: AGE_BAND_LABELS[band - 1], value }),
    price.previous_value
      ? t("review.cellLabelPrevious", { value: formatMoney(price.previous_value), change: formatChange(price.change) })
      : t("review.noPrevious"),
    price.corrected_value ? t("review.corrected") : null,
    tone ? tEnum("severity", tone) : null,
  ]
    .filter(Boolean)
    .join(". ");
}
