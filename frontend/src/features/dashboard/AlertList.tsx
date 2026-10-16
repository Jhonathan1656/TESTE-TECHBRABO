import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, Info, ListChecks, RadioTower, RefreshCw, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { catalogApi, monitoringApi } from "../../shared/api/endpoints";
import { describeError } from "../../shared/api/errors";
import type { Alert, Severity } from "../../shared/api/types";
import { useAuth } from "../../shared/auth/AuthContext";
import { Button } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { Dialog } from "../../shared/components/Dialog";
import { EmptyState } from "../../shared/components/States";
import { useToast } from "../../shared/components/toast";
import { formatDateTime } from "../../shared/format/format";
import { t, tEnum } from "../../shared/i18n/translate";

export const ALERTS_SECTION_ID = "alerts";

const SOURCE_ALERTS = new Set(["source_overdue", "source_never_checked", "source_check_failed", "stale_price_table"]);

export function AlertList({ alerts }: { alerts: Alert[] }) {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const { notify } = useToast();
  const [deactivating, setDeactivating] = useState<Alert | null>(null);

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  const onError = (error: unknown) => notify(describeError(error), "error");

  const runChecks = useMutation({
    mutationFn: monitoringApi.runChecks,
    onSuccess: () => {
      notify(t("dashboard.checksDone"));
      refresh();
    },
    onError,
  });
  const resolve = useMutation({ mutationFn: monitoringApi.resolveAlert, onSuccess: refresh, onError });
  const deactivate = useMutation({
    mutationFn: async (planId: string) => {
      await catalogApi.deactivatePlan(planId);
      await monitoringApi.runChecks();
    },
    onSuccess: () => {
      setDeactivating(null);
      refresh();
    },
  });

  return (
    <Card
      id={ALERTS_SECTION_ID}
      title={t("dashboard.alertsTitle")}
      flush
      actions={
        hasRole("analyst") && (
          <Button
            size="sm"
            icon={<RefreshCw size={14} />}
            disabled={runChecks.isPending}
            onClick={() => runChecks.mutate()}
          >
            {runChecks.isPending ? t("common.working") : t("dashboard.runChecks")}
          </Button>
        )
      }
    >
      {alerts.length === 0 ? (
        <EmptyState icon={<CircleCheck size={20} />}>{t("dashboard.alertsEmpty")}</EmptyState>
      ) : (
        <ul className="list">
          {alerts.map((alert) => (
            <li key={alert.id} className="list-item">
              <SeverityIcon severity={alert.severity} />
              <div className="list-item-body">
                <span>{alert.message}</span>
                <span className="list-item-meta">
                  {tEnum("severity", alert.severity)} · <span className="numeric">{formatDateTime(alert.opened_at)}</span>
                </span>
                <div className="list-item-actions">
                  {SOURCE_ALERTS.has(alert.kind) && (
                    <Link className="icon-text small" to="/sources">
                      <RadioTower size={14} aria-hidden="true" />
                      {t("nav.sources")}
                    </Link>
                  )}
                  {alert.plan_id && (
                    <Link className="icon-text small" to={`/plans/${alert.plan_id}`}>
                      <ListChecks size={14} aria-hidden="true" />
                      {t("nav.plans")}
                    </Link>
                  )}
                  {alert.kind === "plan_not_active_at_ans" && alert.plan_is_active && hasRole("reviewer") && (
                    <Button size="sm" variant="danger" onClick={() => setDeactivating(alert)}>
                      {t("dashboard.deactivatePlan")}
                    </Button>
                  )}
                  {alert.kind === "broker_report" && hasRole("analyst") && (
                    <Button size="sm" disabled={resolve.isPending} onClick={() => resolve.mutate(alert.id)}>
                      {t("dashboard.resolveAlert")}
                    </Button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      <Dialog
        open={deactivating !== null}
        title={t("dashboard.deactivateTitle")}
        description={t("dashboard.deactivateDescription")}
        submitLabel={t("dashboard.deactivatePlan")}
        submitVariant="destructive"
        busy={deactivate.isPending}
        error={deactivate.isError ? describeError(deactivate.error) : null}
        onSubmit={() => deactivating?.plan_id && deactivate.mutate(deactivating.plan_id)}
        onClose={() => {
          deactivate.reset();
          setDeactivating(null);
        }}
      >
        {deactivating && <p className="callout tone-error">{deactivating.message}</p>}
      </Dialog>
    </Card>
  );
}

const SEVERITY_ICONS = { error: CircleAlert, warning: TriangleAlert, info: Info } as const;

/** Decorative: every place that shows it also prints the severity or the message in text. */
export function SeverityIcon({ severity, size = 18 }: { severity: Severity; size?: number }) {
  const Icon = SEVERITY_ICONS[severity];
  return <Icon size={size} className={`severity-icon tone-${severity}`} aria-hidden="true" />;
}
