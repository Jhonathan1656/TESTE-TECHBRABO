import { useQuery } from "@tanstack/react-query";
import { ArrowRight, History } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { pricingApi } from "../../shared/api/endpoints";
import type { AnsReference, PlanPricing, PriceTableVersion } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { Card } from "../../shared/components/Card";
import { PageHeader } from "../../shared/components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { tableStateTone } from "../../shared/components/tones";
import { formatDateTime, formatIsoDate, formatMoney } from "../../shared/format/format";
import { describeActor } from "../../shared/format/relative";
import { t, tEnum } from "../../shared/i18n/translate";

export function PlanDetailPage() {
  const { planId = "" } = useParams();
  const pricing = useQuery({ queryKey: ["plan-pricing", planId], queryFn: () => pricingApi.planPricing(planId) });

  if (pricing.isPending) {
    return <LoadingState lines={8} />;
  }
  if (pricing.isError) {
    return <ErrorState error={pricing.error} onRetry={() => void pricing.refetch()} />;
  }
  return <PlanDetail data={pricing.data} />;
}

function PlanDetail({ data }: { data: PlanPricing }) {
  const { plan } = data;
  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: t("planDetail.breadcrumb"), to: "/plans" }]}
        title={plan.name}
        status={
          <Badge tone={plan.is_active ? "success" : "neutral"} dot>
            {plan.is_active ? t("plans.active") : t("plans.inactive")}
          </Badge>
        }
        subtitle={[
          plan.operator.name,
          tEnum("contractType", plan.contract_type),
          tEnum("accommodation", plan.accommodation),
          tEnum("coverageArea", plan.coverage_area),
        ].join(" · ")}
      />
      <AnsCard ans={data.ans} ansCode={plan.ans_code} />
      <Card title={t("planDetail.historyTitle")} hint={t("planDetail.historyHint")} flush>
        {data.versions.length === 0 ? (
          <EmptyState icon={<History size={20} />}>{t("planDetail.empty")}</EmptyState>
        ) : (
          <ol className="list">
            {sortVersions(data.versions).map((version) => (
              <VersionItem key={version.id} version={version} />
            ))}
          </ol>
        )}
      </Card>
    </>
  );
}

function AnsCard({ ans, ansCode }: { ans: AnsReference | null; ansCode: string }) {
  return (
    <Card title={t("planDetail.ansTitle")} hint={<code translate="no">{ansCode}</code>}>
      {ans ? (
        <dl className="definition-list">
          <dt>{t("planDetail.ansStatus")}</dt>
          <dd>
            <Badge tone={ans.status === "active" ? "success" : "error"} dot>
              {ans.status_label}
            </Badge>{" "}
            {ans.status_date && (
              <span className="subtle small numeric">
                {t("planDetail.ansSince", { date: formatIsoDate(ans.status_date) })}
              </span>
            )}
          </dd>
          <dt>{t("planDetail.ansNote")}</dt>
          <dd>
            {ans.note_code
              ? t("planDetail.ansNoteValue", { code: ans.note_code, date: formatIsoDate(ans.note_registered_at) })
              : t("common.none")}
          </dd>
        </dl>
      ) : (
        <p className="muted">{t("planDetail.ansMissing")}</p>
      )}
    </Card>
  );
}

function VersionItem({ version }: { version: PriceTableVersion }) {
  const validity = version.effective_until
    ? `${formatIsoDate(version.effective_from)} – ${formatIsoDate(version.effective_until)}`
    : `${formatIsoDate(version.effective_from)} – …`;
  return (
    <li className={version.state === "superseded" ? "version version-superseded" : "version"}>
      <div className="row-between">
        <div className="row">
          <Badge tone={tableStateTone(version.state)} dot>
            {tEnum("tableState", version.state)}
          </Badge>
          <strong className="numeric">
            {t("planDetail.validity")}: {validity}
          </strong>
          <span className="subtle small">{version.region}</span>
        </div>
        <Link className="icon-text small" to={`/batches/${version.batch_id}`}>
          {t("planDetail.openBatch")}
          <ArrowRight size={13} aria-hidden="true" />
        </Link>
      </div>
      <p className="version-meta">
        <span className="numeric">{t("planDetail.recorded", { date: formatDateTime(version.recorded_at) })}</span>
        {version.superseded_at && (
          <span className="numeric">{t("planDetail.supersededAt", { date: formatDateTime(version.superseded_at) })}</span>
        )}
        {version.derived_from_id && <span>{t("planDetail.derived")}</span>}
        <span>
          {version.auto_published
            ? t("planDetail.autoPublished")
            : t("planDetail.publishedBy", { by: describeActor(version.published_by?.display_name) })}
        </span>
        <span className="break-anywhere">
          {t("planDetail.documentLabel")}: <span translate="no">{version.document.filename}</span>
        </span>
        <span>
          {t("planDetail.sourceLabel")}: {version.source.name}
        </span>
      </p>
      <dl className="band-values">
        {version.entries.map((entry) => (
          <div key={entry.age_band} className="band-value">
            <dt>{entry.band_label}</dt>
            <dd>{formatMoney(entry.value)}</dd>
          </div>
        ))}
      </dl>
    </li>
  );
}

const STATE_ORDER: Record<PriceTableVersion["state"], number> = {
  scheduled: 0,
  current: 1,
  expired: 2,
  superseded: 3,
};

function sortVersions(versions: PriceTableVersion[]): PriceTableVersion[] {
  return [...versions].sort(
    (left, right) =>
      STATE_ORDER[left.state] - STATE_ORDER[right.state] ||
      right.effective_from.localeCompare(left.effective_from) ||
      right.recorded_at.localeCompare(left.recorded_at),
  );
}
