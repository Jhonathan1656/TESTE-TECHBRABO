import { History } from "lucide-react";

import type { AuditEvent } from "../../shared/api/types";
import { Card } from "../../shared/components/Card";
import { EmptyState } from "../../shared/components/States";
import { formatDateTime, formatMoney } from "../../shared/format/format";
import { t, tEnum } from "../../shared/i18n/translate";
import { AGE_BAND_LABELS } from "../batches/reviewModel";

export function ActivityFeed({ events, title = t("dashboard.activityTitle") }: { events: AuditEvent[]; title?: string }) {
  return (
    <Card title={title} flush>
      {events.length === 0 ? (
        <EmptyState icon={<History size={20} />}>{t("dashboard.activityEmpty")}</EmptyState>
      ) : (
        <ol className="timeline">
          {events.map((event, index) => (
            <li key={`${event.occurred_at}-${event.action}-${index}`} className="timeline-item">
              <time className="timeline-time" dateTime={event.occurred_at}>
                {formatDateTime(event.occurred_at)}
              </time>
              <div>
                <span className="timeline-title">{tEnum("auditAction", event.action)}</span>
                <span className="timeline-actor">
                  {" · "}
                  {event.actor?.display_name ?? t("common.system")}
                  {event.operator_name ? ` · ${event.operator_name}` : ""}
                </span>
                <EventDetail event={event} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function EventDetail({ event }: { event: AuditEvent }) {
  const payload = event.payload as Record<string, string | number | null | undefined>;
  const correction =
    payload.from || payload.to ? `${formatMoney(payload.from)} → ${formatMoney(payload.to)}` : null;
  const detail = [
    payload.filename,
    payload.label,
    payload.plan,
    payload.age_band ? AGE_BAND_LABELS[Number(payload.age_band) - 1] : null,
    correction,
    payload.dataset ? tEnum("ansDataset", payload.dataset) : null,
    payload.outcome ? tEnum("checkOutcome", payload.outcome) : null,
    payload.note ? `“${payload.note}”` : null,
    payload.reason ? `“${payload.reason}”` : null,
  ]
    .filter((value) => typeof value === "string" && value.length > 0)
    .join(" · ");
  return detail ? <div className="cell-sub break-anywhere numeric">{detail}</div> : null;
}
