import { CalendarClock, FileText, MessageSquareWarning, RadioTower, ShieldAlert } from "lucide-react";
import { useId } from "react";
import { Link } from "react-router-dom";

import type { PlanQuote } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { Button } from "../../shared/components/Button";
import { freshnessTone, trustTone } from "../../shared/components/tones";
import { formatChange, formatIsoDate, formatMoney } from "../../shared/format/format";
import { describeActor, describeDaysAgo } from "../../shared/format/relative";
import { t, tEnum } from "../../shared/i18n/translate";

export function QuoteResultCard({ quote, onReport }: { quote: PlanQuote; onReport: () => void }) {
  const { plan, table, freshness } = quote;
  const titleId = useId();
  return (
    <article className="card quote-card" aria-labelledby={titleId}>
      <div className="quote-head">
        <div className="stack-sm">
          <h3 id={titleId} className="quote-plan">
            <Link to={`/plans/${plan.id}`} className="cell-title">
              {plan.name}
            </Link>
          </h3>
          <span className="muted">{plan.operator.name}</span>
          <div className="row">
            <Badge>{tEnum("contractType", plan.contract_type)}</Badge>
            <Badge>{tEnum("accommodation", plan.accommodation)}</Badge>
            {plan.has_coparticipation && <Badge tone="info">{t("plans.columnCoparticipation")}</Badge>}
          </div>
        </div>
        <div className="quote-total">
          <div className="meta-label">{t("quote.total")}</div>
          <div className="quote-total-value">{formatMoney(quote.total)}</div>
        </div>
      </div>
      <ul className="beneficiaries">
        {quote.beneficiaries.map((beneficiary, index) => (
          <li key={`${beneficiary.age}-${index}`} className="beneficiary">
            <span className="beneficiary-label">
              {t("quote.perBeneficiary", { age: beneficiary.age, band: beneficiary.band_label })}
            </span>
            <span className="beneficiary-value">{formatMoney(beneficiary.value)}</span>
          </li>
        ))}
      </ul>
      {quote.scheduled_change && (
        <p className="callout">
          <CalendarClock size={16} aria-hidden="true" />
          <span className="numeric">
            {t("quote.nextChange", {
              date: formatIsoDate(quote.scheduled_change.effective_from),
              total: formatMoney(quote.scheduled_change.total),
              change: formatChange(quote.scheduled_change.change),
            })}
          </span>
        </p>
      )}
      {quote.ans && quote.ans.status !== "active" && (
        <p className="callout tone-error">
          <ShieldAlert size={16} aria-hidden="true" />
          <span>{t("quote.ansSuspended", { status: quote.ans.status_label })}</span>
        </p>
      )}
      <div className="provenance">
        <span className="provenance-item">
          <FileText size={14} aria-hidden="true" />
          <span className="numeric">
            {t("quote.effectiveSince", { date: formatIsoDate(table.effective_from) })} ·{" "}
            {table.auto_published
              ? t("common.automatic")
              : t("quote.publishedBy", { by: describeActor(table.published_by?.display_name) })}
          </span>
        </span>
        <span className="provenance-item">
          <RadioTower size={14} aria-hidden="true" />
          {table.source.name}
          <Badge tone={trustTone(table.source.trust_level)}>{tEnum("trust", table.source.trust_level)}</Badge>
        </span>
        {freshness && (
          <span className="provenance-item">
            <Badge tone={freshnessTone(freshness.status)} dot>
              {tEnum("freshness", freshness.status)}
            </Badge>
            {freshness.days_since_success === null
              ? t("quote.sourceNeverChecked")
              : t("quote.sourceFreshness", { when: describeDaysAgo(freshness.days_since_success) })}
          </span>
        )}
        <span className="provenance-action">
          <Button size="sm" variant="ghost" icon={<MessageSquareWarning size={14} />} onClick={onReport}>
            {t("quote.report")}
          </Button>
        </span>
      </div>
    </article>
  );
}
