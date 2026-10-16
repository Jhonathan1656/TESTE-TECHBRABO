import { useQuery } from "@tanstack/react-query";
import { Search, SearchX } from "lucide-react";
import { useDeferredValue, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { catalogApi } from "../../shared/api/endpoints";
import type { Plan } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { Card } from "../../shared/components/Card";
import { PageHeader } from "../../shared/components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { TableScroll } from "../../shared/components/TableScroll";
import { t, tEnum } from "../../shared/i18n/translate";

export function PlanListPage() {
  // Search and filter live in the URL (?q=…&inactive=1), so a filtered list can be bookmarked or shared.
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get("q") ?? "";
  const includeInactive = searchParams.get("inactive") === "1";
  const deferredSearch = useDeferredValue(search);

  const plans = useQuery({
    queryKey: ["plans", includeInactive],
    queryFn: () => catalogApi.plans(includeInactive),
  });
  const filtered = useMemo(() => filterPlans(plans.data ?? [], deferredSearch), [plans.data, deferredSearch]);

  const updateParam = (name: string, value: string | null) =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) {
          next.set(name, value);
        } else {
          next.delete(name);
        }
        return next;
      },
      { replace: true },
    );

  return (
    <>
      <PageHeader title={t("plans.title")} subtitle={t("plans.subtitle")} />
      <div className="toolbar">
        <div className="row">
          <div className="input-search">
            <Search size={16} aria-hidden="true" />
            <input
              className="input"
              type="search"
              name="q"
              autoComplete="off"
              spellCheck={false}
              placeholder={t("plans.searchPlaceholder")}
              aria-label={t("plans.search")}
              value={search}
              onChange={(event) => updateParam("q", event.target.value)}
            />
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              name="inactive"
              checked={includeInactive}
              onChange={(event) => updateParam("inactive", event.target.checked ? "1" : null)}
            />
            {t("plans.showInactive")}
          </label>
        </div>
        {plans.data && (
          <span className="subtle small" aria-live="polite">
            {t("plans.count", { count: filtered.length })}
          </span>
        )}
      </div>
      <Card flush>
        {plans.isPending && <LoadingState />}
        {plans.isError && <ErrorState error={plans.error} onRetry={() => void plans.refetch()} />}
        {plans.data && filtered.length === 0 && <EmptyState icon={<SearchX size={20} />}>{t("plans.empty")}</EmptyState>}
        {filtered.length > 0 && <PlanTable plans={filtered} />}
      </Card>
    </>
  );
}

function PlanTable({ plans }: { plans: Plan[] }) {
  const navigate = useNavigate();
  return (
    <TableScroll label={t("plans.title")}>
      <table className="table">
        <thead>
          <tr>
            <th scope="col">{t("plans.columnPlan")}</th>
            <th scope="col">{t("plans.columnOperator")}</th>
            <th scope="col">{t("plans.columnAnsCode")}</th>
            <th scope="col">{t("plans.columnContract")}</th>
            <th scope="col">{t("plans.columnAccommodation")}</th>
            <th scope="col">{t("plans.columnCoparticipation")}</th>
            <th scope="col">{t("plans.columnStatus")}</th>
          </tr>
        </thead>
        <tbody>
          {plans.map((plan) => (
            // Row click is a pointer shortcut; the plan name is the keyboard-reachable link.
            <tr key={plan.id} className="clickable" onClick={() => navigate(`/plans/${plan.id}`)}>
              <th scope="row">
                <Link to={`/plans/${plan.id}`} className="cell-title" onClick={(event) => event.stopPropagation()}>
                  {plan.name}
                </Link>
                <div className="cell-sub">{tEnum("coverageArea", plan.coverage_area)}</div>
              </th>
              <td>{plan.operator.name}</td>
              <td className="numeric nowrap">
                {plan.ans_code ? <code translate="no">{plan.ans_code}</code> : t("common.none")}
              </td>
              <td>{tEnum("contractType", plan.contract_type)}</td>
              <td>{tEnum("accommodation", plan.accommodation)}</td>
              <td>{plan.has_coparticipation ? t("common.yes") : t("common.no")}</td>
              <td>
                <Badge tone={plan.is_active ? "success" : "neutral"} dot>
                  {plan.is_active ? t("plans.active") : t("plans.inactive")}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableScroll>
  );
}

function filterPlans(plans: Plan[], search: string): Plan[] {
  const term = search.trim().toLocaleLowerCase("pt-BR");
  if (!term) {
    return plans;
  }
  return plans.filter((plan) =>
    `${plan.name} ${plan.operator.name} ${plan.ans_code}`.toLocaleLowerCase("pt-BR").includes(term),
  );
}
