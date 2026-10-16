import { useQuery } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { batchApi } from "../../shared/api/endpoints";
import type { BatchStatus, BatchSummary } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { ButtonLink } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { PageHeader } from "../../shared/components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { TableScroll } from "../../shared/components/TableScroll";
import { batchStatusTone } from "../../shared/components/tones";
import { formatDateTime, formatIsoDate } from "../../shared/format/format";
import { t, tEnum } from "../../shared/i18n/translate";

type StatusFilter = BatchStatus | "all";

const DEFAULT_FILTER: StatusFilter = "pending_review";
const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "pending_review", label: t("batches.tabPending") },
  { key: "published", label: t("batches.tabPublished") },
  { key: "failed", label: t("batches.tabFailed") },
  { key: "rejected", label: t("batches.tabRejected") },
  { key: "all", label: t("batches.tabAll") },
];

/** The filter lives in the URL (?status=published), so it survives reloads and can be shared. */
function readFilter(value: string | null): StatusFilter {
  return FILTERS.find((filter) => filter.key === value)?.key ?? DEFAULT_FILTER;
}

export function BatchListPage() {
  const [searchParams] = useSearchParams();
  const filter = readFilter(searchParams.get("status"));
  const status = filter === "all" ? undefined : filter;
  const batches = useQuery({ queryKey: ["batches", status ?? "all"], queryFn: () => batchApi.list(status) });

  return (
    <>
      <PageHeader
        title={t("batches.title")}
        subtitle={t("batches.subtitle")}
        actions={
          <ButtonLink to="/upload" variant="primary" icon={<FileUp size={16} />}>
            {t("batches.newUpload")}
          </ButtonLink>
        }
      />
      <nav aria-label={t("batches.filterLabel")}>
        <ul className="segmented">
          {FILTERS.map((item) => (
            <li key={item.key}>
              <Link
                to={item.key === DEFAULT_FILTER ? "/batches" : `/batches?status=${item.key}`}
                aria-current={filter === item.key ? "true" : undefined}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <Card flush>
        {batches.isPending && <LoadingState />}
        {batches.isError && <ErrorState error={batches.error} onRetry={() => void batches.refetch()} />}
        {batches.data && batches.data.length === 0 && <EmptyState>{t("batches.empty")}</EmptyState>}
        {batches.data && batches.data.length > 0 && <BatchTable batches={batches.data} />}
      </Card>
    </>
  );
}

function BatchTable({ batches }: { batches: BatchSummary[] }) {
  const navigate = useNavigate();
  return (
    <TableScroll label={t("batches.title")}>
      <table className="table">
        <thead>
          <tr>
            <th scope="col">{t("batches.columnOperator")}</th>
            <th scope="col">{t("batches.columnDocument")}</th>
            <th scope="col">{t("batches.columnChannel")}</th>
            <th scope="col">{t("batches.columnEffective")}</th>
            <th scope="col">{t("batches.columnMethod")}</th>
            <th scope="col">{t("batches.columnIssues")}</th>
            <th scope="col">{t("batches.columnReceived")}</th>
          </tr>
        </thead>
        <tbody>
          {batches.map((batch) => (
            // The row click is a pointer shortcut; keyboard and screen-reader users follow the link in the first cell.
            <tr key={batch.id} className="clickable" onClick={() => navigate(`/batches/${batch.id}`)}>
              <th scope="row">
                <Link to={`/batches/${batch.id}`} className="cell-title" onClick={(event) => event.stopPropagation()}>
                  {batch.operator.name}
                </Link>
                <div className="cell-sub">
                  <Badge tone={batchStatusTone(batch.status)} dot>
                    {tEnum("batchStatus", batch.status)}
                  </Badge>
                </div>
              </th>
              <td>
                <div className="break-anywhere" translate="no">
                  {batch.document.filename}
                </div>
                <div className="cell-sub">{batch.region || t("review.regionMissing")}</div>
              </td>
              <td>{tEnum("channel", batch.source.channel)}</td>
              <td className="numeric nowrap">{formatIsoDate(batch.effective_from)}</td>
              <td>{tEnum("extractionMethod", batch.extraction_method)}</td>
              <td>
                <IssueCounts batch={batch} />
              </td>
              <td className="subtle small numeric nowrap">{formatDateTime(batch.document.received_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableScroll>
  );
}

function IssueCounts({ batch }: { batch: BatchSummary }) {
  if (batch.status === "failed") {
    return <Badge tone="error">{tEnum("batchStatus", "failed")}</Badge>;
  }
  if (!batch.counts.open_errors && !batch.counts.open_warnings) {
    return <span className="subtle small">{t("batches.noIssues")}</span>;
  }
  return (
    <div className="row">
      {batch.counts.open_errors > 0 && (
        <Badge tone="error">{t("batches.errorsCount", { count: batch.counts.open_errors })}</Badge>
      )}
      {batch.counts.open_warnings > 0 && (
        <Badge tone="warning">{t("batches.warningsCount", { count: batch.counts.open_warnings })}</Badge>
      )}
    </div>
  );
}
