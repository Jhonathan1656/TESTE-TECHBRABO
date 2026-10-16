import { useMutation, useQuery } from "@tanstack/react-query";
import { Calculator, CircleAlert, SearchX } from "lucide-react";
import { type FormEvent, useRef, useState } from "react";

import { catalogApi, pricingApi } from "../../shared/api/endpoints";
import { describeError } from "../../shared/api/errors";
import type { PlanQuote } from "../../shared/api/types";
import { Button } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { PageHeader } from "../../shared/components/PageHeader";
import { EmptyState, LoadingState } from "../../shared/components/States";
import { parseAges, todayIsoDate } from "../../shared/format/format";
import { t } from "../../shared/i18n/translate";
import { BrokerReportDialog } from "./BrokerReportDialog";
import { QuoteResultCard } from "./QuoteResultCard";

export function QuotePage() {
  const regions = useQuery({ queryKey: ["regions"], queryFn: pricingApi.regions });
  const operators = useQuery({ queryKey: ["operators"], queryFn: catalogApi.operators });
  const [region, setRegion] = useState("");
  const [agesText, setAgesText] = useState("34, 32, 5");
  const [onDate, setOnDate] = useState(todayIsoDate());
  const [operatorId, setOperatorId] = useState("");
  const [knownAt, setKnownAt] = useState("");
  const [reported, setReported] = useState<PlanQuote | null>(null);
  const [agesError, setAgesError] = useState<string | null>(null);
  const agesRef = useRef<HTMLInputElement>(null);

  const selectedRegion = region || regions.data?.[0] || "";
  const quote = useMutation({ mutationFn: pricingApi.quote });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const ages = parseAges(agesText);
    if (!ages) {
      setAgesError(t("quote.invalidAges"));
      agesRef.current?.focus();
      return;
    }
    setAgesError(null);
    quote.mutate({
      ages,
      on_date: onDate,
      region: selectedRegion,
      operator: operatorId || null,
      known_at: knownAt ? new Date(knownAt).toISOString() : null,
    });
  };

  return (
    <>
      <PageHeader title={t("quote.title")} subtitle={t("quote.subtitle")} />
      <Card>
        <form className="form-grid" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label className="label" htmlFor="quote-region">
              {t("quote.region")}
            </label>
            <select
              id="quote-region"
              className="select"
              name="region"
              value={selectedRegion}
              onChange={(event) => setRegion(event.target.value)}
            >
              {(regions.data ?? []).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="quote-operator">
              {t("quote.operator")}
            </label>
            <select
              id="quote-operator"
              className="select"
              name="operator"
              value={operatorId}
              onChange={(event) => setOperatorId(event.target.value)}
            >
              <option value="">{t("quote.allOperators")}</option>
              {(operators.data ?? []).map((operator) => (
                <option key={operator.id} value={operator.id}>
                  {operator.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="quote-ages">
              {t("quote.ages")}
            </label>
            <input
              ref={agesRef}
              id="quote-ages"
              className="input numeric"
              name="ages"
              inputMode="numeric"
              autoComplete="off"
              value={agesText}
              onChange={(event) => setAgesText(event.target.value)}
              aria-invalid={agesError ? true : undefined}
              aria-describedby={agesError ? "quote-ages-error quote-ages-hint" : "quote-ages-hint"}
            />
            {agesError && (
              <span id="quote-ages-error" className="field-error">
                <CircleAlert size={14} aria-hidden="true" />
                {agesError}
              </span>
            )}
            <span id="quote-ages-hint" className="hint">
              {t("quote.agesHint")}
            </span>
          </div>
          <div className="field">
            <label className="label" htmlFor="quote-date">
              {t("quote.onDate")}
            </label>
            <input
              id="quote-date"
              className="input"
              type="date"
              name="on_date"
              value={onDate}
              onChange={(event) => setOnDate(event.target.value)}
              required
            />
          </div>
          <div className="field span-2">
            <label className="label" htmlFor="quote-known-at">
              {t("quote.knownAt")}
              <span className="label-optional">({t("common.optional")})</span>
            </label>
            <input
              id="quote-known-at"
              className="input input-narrow"
              type="datetime-local"
              name="known_at"
              value={knownAt}
              onChange={(event) => setKnownAt(event.target.value)}
              aria-describedby="quote-known-at-hint"
            />
            <span id="quote-known-at-hint" className="hint">
              {t("quote.knownAtHint")}
            </span>
          </div>
          {quote.isError && (
            <div className="form-error span-2" role="alert">
              <CircleAlert size={16} aria-hidden="true" />
              <span>{describeError(quote.error)}</span>
            </div>
          )}
          <div className="form-actions span-2">
            <Button type="submit" variant="primary" icon={<Calculator size={16} />} disabled={!selectedRegion || quote.isPending}>
              {quote.isPending ? t("common.working") : t("quote.submit")}
            </Button>
          </div>
        </form>
      </Card>
      {quote.isPending && <LoadingState lines={5} />}
      {quote.data && quote.data.length === 0 && (
        <Card>
          <EmptyState icon={<SearchX size={20} />}>{t("quote.empty")}</EmptyState>
        </Card>
      )}
      {quote.data && quote.data.length > 0 && (
        <section className="quote-results" aria-labelledby="quote-results-title">
          <h2 id="quote-results-title" className="quote-results-title" aria-live="polite">
            {t("quote.resultsTitle", { count: quote.data.length })}
          </h2>
          {quote.data.map((item) => (
            <QuoteResultCard key={item.table.id} quote={item} onReport={() => setReported(item)} />
          ))}
        </section>
      )}
      <BrokerReportDialog
        key={reported?.table.id ?? "report"}
        quote={reported}
        onDate={onDate}
        onClose={() => setReported(null)}
      />
    </>
  );
}
