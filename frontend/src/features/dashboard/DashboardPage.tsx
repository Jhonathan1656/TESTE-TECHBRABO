import { useQuery } from "@tanstack/react-query";
import { BellRing, ClipboardCheck, Inbox, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { monitoringApi } from "../../shared/api/endpoints";
import type { Dashboard } from "../../shared/api/types";
import { PageHeader } from "../../shared/components/PageHeader";
import { ErrorState, LoadingState } from "../../shared/components/States";
import { t } from "../../shared/i18n/translate";
import { ActivityFeed } from "./ActivityFeed";
import { ALERTS_SECTION_ID, AlertList } from "./AlertList";
import { DemoDeliveries } from "./DemoDeliveries";
import { OperatorHealthTable } from "./OperatorHealthTable";

export function DashboardPage() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: monitoringApi.dashboard });

  return (
    <>
      <PageHeader title={t("dashboard.title")} subtitle={t("dashboard.subtitle")} />
      {dashboard.isPending && <LoadingState lines={8} />}
      {dashboard.isError && <ErrorState error={dashboard.error} onRetry={() => void dashboard.refetch()} />}
      {dashboard.data && <DashboardContent data={dashboard.data} />}
    </>
  );
}

function DashboardContent({ data }: { data: Dashboard }) {
  const blocking = data.open_errors + data.open_warnings;
  const confirmedShare = data.priced_plans ? Math.round((data.confirmed_plans / data.priced_plans) * 100) : 0;
  const hasErrorAlerts = data.alerts.some((alert) => alert.severity === "error");

  return (
    <>
      <ul className="stat-grid list" aria-label={t("dashboard.summaryLabel")}>
        <StatTile
          href="/batches"
          icon={<Inbox size={16} />}
          label={t("dashboard.kpiPending")}
          value={String(data.pending_batches)}
          hint={t("dashboard.kpiPendingHint")}
          tone={data.pending_batches ? "warning" : "success"}
        />
        <StatTile
          href="/batches"
          icon={<TriangleAlert size={16} />}
          label={t("dashboard.kpiBlocking")}
          value={String(blocking)}
          hint={t("dashboard.kpiBlockingHint", { errors: data.open_errors, warnings: data.open_warnings })}
          tone={data.open_errors ? "error" : blocking ? "warning" : "success"}
        />
        <StatTile
          href="/sources"
          icon={<ClipboardCheck size={16} />}
          label={t("dashboard.kpiConfirmed")}
          value={`${confirmedShare}%`}
          hint={t("dashboard.kpiConfirmedHint", { confirmed: data.confirmed_plans, priced: data.priced_plans })}
          tone={confirmedShare >= 90 ? "success" : "warning"}
        />
        <StatTile
          href={`#${ALERTS_SECTION_ID}`}
          icon={<BellRing size={16} />}
          label={t("dashboard.kpiAlerts")}
          value={String(data.alerts.length)}
          hint={t("dashboard.kpiAlertsHint")}
          tone={hasErrorAlerts ? "error" : data.alerts.length ? "warning" : "success"}
        />
      </ul>
      <DemoDeliveries />
      <OperatorHealthTable operators={data.operators} />
      <div className="dashboard-columns">
        <AlertList alerts={data.alerts} />
        <ActivityFeed events={data.recent_events} />
      </div>
    </>
  );
}

interface StatTileProps {
  /** A route ("/batches") or an in-page anchor ("#alerts"). */
  href: string;
  icon: ReactNode;
  label: string;
  value: string;
  hint: string;
  tone: "success" | "warning" | "error";
}

/** The number stays in ink; the tinted icon and the hint text carry the status, so color is never alone. */
function StatTile({ href, icon, label, value, hint, tone }: StatTileProps) {
  const content = (
    <>
      <span className="stat-label">
        <span className={`stat-icon tone-${tone}`} aria-hidden="true">
          {icon}
        </span>
        {label}
      </span>
      <span className="stat-value">{value}</span>
      <span className="stat-hint">{hint}</span>
    </>
  );
  return (
    <li>
      {href.startsWith("#") ? (
        <a className="stat" href={href}>
          {content}
        </a>
      ) : (
        <Link className="stat" to={href}>
          {content}
        </Link>
      )}
    </li>
  );
}
