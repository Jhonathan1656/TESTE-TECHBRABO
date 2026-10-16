import { ChevronRight, CircleCheck, Crosshair } from "lucide-react";
import { useId } from "react";

import type { BatchDetail, ExtractedPlan, ValidationIssue } from "../../shared/api/types";
import { Button } from "../../shared/components/Button";
import { t, tEnum } from "../../shared/i18n/translate";
import { SeverityIcon } from "../dashboard/AlertList";
import { buildCellKey, findExtractedPlan } from "./reviewModel";

interface IssuePanelProps {
  batch: BatchDetail;
  canEdit: boolean;
  onShowCell: (cellKey: string) => void;
  onAcknowledge: (issue: ValidationIssue) => void;
  onMapPlan: (plan: ExtractedPlan) => void;
  onConfirmMapping: (plan: ExtractedPlan) => void;
  onExcludePlan: (plan: ExtractedPlan) => void;
}

export function IssuePanel(props: IssuePanelProps) {
  const { batch } = props;
  const titleId = useId();
  const open = batch.issues.filter((issue) => issue.status === "open" && issue.severity !== "info");
  const infos = batch.issues.filter((issue) => issue.status === "open" && issue.severity === "info");
  const acknowledged = batch.issues.filter((issue) => issue.status === "acknowledged");
  const resolved = batch.issues.filter((issue) => issue.status === "resolved");

  return (
    <section className="card issues-panel" aria-labelledby={titleId}>
      <header className="card-header">
        <h2 id={titleId} className="card-title">
          {t("review.issuesTitle")}
        </h2>
      </header>
      <div className="card-body flush">
        {open.length === 0 && batch.status === "pending_review" && (
          <p className="callout tone-success issue-empty">
            <CircleCheck size={16} aria-hidden="true" />
            <span>{t("review.issuesEmpty")}</span>
          </p>
        )}
        <IssueGroup title={t("review.issuesOpen")} issues={open} {...props} />
        <IssueGroup title={t("review.issuesInfo")} issues={infos} muted {...props} />
        <IssueGroup title={t("review.issuesAcknowledged")} issues={acknowledged} muted {...props} />
        {resolved.length > 0 && (
          <details className="issue-group">
            <summary className="issue-group-title">
              <ChevronRight size={14} aria-hidden="true" />
              {t("review.issuesResolved")} ({resolved.length})
            </summary>
            <ul className="list">
              {resolved.map((issue) => (
                <IssueItem key={issue.id} issue={issue} muted {...props} />
              ))}
            </ul>
          </details>
        )}
      </div>
    </section>
  );
}

function IssueGroup({
  title,
  issues,
  muted = false,
  ...props
}: IssuePanelProps & { title: string; issues: ValidationIssue[]; muted?: boolean }) {
  const titleId = useId();
  if (issues.length === 0) {
    return null;
  }
  return (
    <div>
      <h3 id={titleId} className="issue-group-title">
        {title} ({issues.length})
      </h3>
      <ul className="list" aria-labelledby={titleId}>
        {issues.map((issue) => (
          <IssueItem key={issue.id} issue={issue} muted={muted} {...props} />
        ))}
      </ul>
    </div>
  );
}

function IssueItem({
  issue,
  muted,
  batch,
  canEdit,
  onShowCell,
  onAcknowledge,
  onMapPlan,
  onConfirmMapping,
  onExcludePlan,
}: IssuePanelProps & { issue: ValidationIssue; muted: boolean }) {
  const plan = findExtractedPlan(batch, issue.extracted_plan_id);
  const editable = canEdit && issue.status === "open";

  return (
    <li className={muted ? "issue issue-muted" : "issue"}>
      <SeverityIcon severity={issue.severity} />
      <div className="list-item-body">
        <span className="visually-hidden">{tEnum("severity", issue.severity)}: </span>
        <span className="issue-message">{issue.message}</span>
        {issue.status === "acknowledged" && issue.acknowledged_by && (
          <span className="list-item-meta">
            {t("review.acknowledgedBy", {
              name: issue.acknowledged_by.display_name,
              note: issue.acknowledgement_note,
            })}
          </span>
        )}
        <div className="list-item-actions">
          {plan && issue.age_band && (
            <Button
              size="sm"
              variant="ghost"
              icon={<Crosshair size={14} />}
              onClick={() => onShowCell(buildCellKey(plan.id, issue.age_band!))}
            >
              {t("review.showCell")}
            </Button>
          )}
          {editable && plan && issue.rule_code === "catalog.unmatched_plan" && (
            <Button size="sm" onClick={() => onMapPlan(plan)}>
              {t("review.mapPlan")}
            </Button>
          )}
          {editable && plan && issue.rule_code === "catalog.similarity_match" && (
            <Button size="sm" variant="primary" onClick={() => onConfirmMapping(plan)}>
              {t("review.confirmMapping")}
            </Button>
          )}
          {editable && plan && issue.rule_code === "ans.plan_not_active" && (
            <Button size="sm" variant="danger" onClick={() => onExcludePlan(plan)}>
              {t("review.excludePlan")}
            </Button>
          )}
          {editable && issue.severity === "warning" && (
            <Button size="sm" onClick={() => onAcknowledge(issue)}>
              {t("review.acknowledge")}
            </Button>
          )}
        </div>
      </div>
    </li>
  );
}
