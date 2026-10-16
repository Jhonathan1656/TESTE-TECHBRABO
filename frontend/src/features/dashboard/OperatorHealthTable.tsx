import type { OperatorHealth } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { Card } from "../../shared/components/Card";
import { TableScroll } from "../../shared/components/TableScroll";
import { freshnessTone } from "../../shared/components/tones";
import { formatIsoDate } from "../../shared/format/format";
import { describeDaysAgo, describeDaysUntil } from "../../shared/format/relative";
import { t, tEnum } from "../../shared/i18n/translate";

export function OperatorHealthTable({ operators }: { operators: OperatorHealth[] }) {
  return (
    <Card title={t("dashboard.operatorsTitle")} hint={t("dashboard.operatorsHint")} flush>
      <TableScroll label={t("dashboard.operatorsTitle")}>
        <table className="table">
          <thead>
            <tr>
              <th scope="col">{t("dashboard.columnOperator")}</th>
              <th scope="col">{t("dashboard.columnStatus")}</th>
              <th scope="col">{t("dashboard.columnLastCheck")}</th>
              <th scope="col">{t("dashboard.columnOldest")}</th>
              <th scope="col">{t("dashboard.columnNext")}</th>
              <th scope="col">{t("dashboard.columnPending")}</th>
            </tr>
          </thead>
          <tbody>
            {operators.map((item) => (
              <tr key={item.operator.id}>
                <th scope="row">
                  <div className="cell-title">{item.operator.name}</div>
                  <div className="cell-sub">
                    {tEnum("accessLevel", item.operator.access_level)} ·{" "}
                    <span className="numeric">
                      {item.priced_plans}/{item.active_plans}
                    </span>{" "}
                    {t("nav.plans").toLocaleLowerCase("pt-BR")}
                  </div>
                </th>
                <td>
                  <Badge tone={freshnessTone(item.status)} dot>
                    {tEnum("freshness", item.status)}
                  </Badge>
                </td>
                <td className="nowrap">{describeDaysAgo(mostRecentConfirmation(item))}</td>
                <td className="numeric">{formatIsoDate(item.oldest_effective_from)}</td>
                <td className="numeric">
                  {item.next_change_on ? (
                    <>
                      {formatIsoDate(item.next_change_on)}
                      <div className="cell-sub">{describeDaysUntil(item.next_change_on)}</div>
                    </>
                  ) : (
                    <span className="subtle">{t("common.none")}</span>
                  )}
                </td>
                <td>
                  {item.pending_batches > 0 ? (
                    <Badge tone="warning">{t("dashboard.pendingBatches", { count: item.pending_batches })}</Badge>
                  ) : (
                    <span className="subtle">{t("common.none")}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableScroll>
    </Card>
  );
}

function mostRecentConfirmation(item: OperatorHealth): number | null {
  const days = item.sources
    .map((source) => source.freshness.days_since_success)
    .filter((value): value is number => value !== null);
  return days.length ? Math.min(...days) : null;
}
