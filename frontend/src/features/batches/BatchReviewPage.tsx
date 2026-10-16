import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, Sparkles, TriangleAlert, XCircle } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { batchApi } from "../../shared/api/endpoints";
import { describeError } from "../../shared/api/errors";
import type { BatchDetail, ExtractedPlan, ExtractedPrice, ValidationIssue } from "../../shared/api/types";
import { useAuth } from "../../shared/auth/AuthContext";
import { Badge } from "../../shared/components/Badge";
import { Button } from "../../shared/components/Button";
import { PageHeader } from "../../shared/components/PageHeader";
import { ErrorState, LoadingState } from "../../shared/components/States";
import { useToast } from "../../shared/components/toast";
import { batchStatusTone } from "../../shared/components/tones";
import { formatDateTime } from "../../shared/format/format";
import { describeActor } from "../../shared/format/relative";
import { t, tEnum } from "../../shared/i18n/translate";
import { ActivityFeed } from "../dashboard/ActivityFeed";
import { BatchMeta } from "./BatchMeta";
import { CellDialog } from "./CellDialog";
import { IssuePanel } from "./IssuePanel";
import { PriceGrid } from "./PriceGrid";
import { AcknowledgeDialog, DatesDialog, DecisionDialog, MappingDialog } from "./ReviewDialogs";
import { ReviewSummary } from "./ReviewSummary";
import { buildSeverityIndex } from "./reviewModel";
import { batchQueryKey, useBatchActions } from "./useBatchActions";

const PUBLISH_BLOCKED_ID = "publish-blocked";

export function BatchReviewPage() {
  const { batchId = "" } = useParams();
  const batch = useQuery({ queryKey: batchQueryKey(batchId), queryFn: () => batchApi.get(batchId) });

  if (batch.isPending) {
    return <LoadingState lines={10} />;
  }
  if (batch.isError) {
    return <ErrorState error={batch.error} onRetry={() => void batch.refetch()} />;
  }
  return <BatchReview batch={batch.data} />;
}

function BatchReview({ batch }: { batch: BatchDetail }) {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const { notify } = useToast();
  const actions = useBatchActions(batch.id);
  const severity = useMemo(() => buildSeverityIndex(batch.issues), [batch.issues]);

  const [selectedCell, setSelectedCell] = useState<{ plan: ExtractedPlan; price: ExtractedPrice } | null>(null);
  const [mappingPlan, setMappingPlan] = useState<ExtractedPlan | null>(null);
  const [acknowledgedIssue, setAcknowledgedIssue] = useState<ValidationIssue | null>(null);
  const [datesOpen, setDatesOpen] = useState(false);
  const [decision, setDecision] = useState<"publish" | "reject" | null>(null);
  const [highlightedCell, setHighlightedCell] = useState<string | null>(null);

  const isPending = batch.status === "pending_review";
  const canEdit = isPending && hasRole("analyst");
  const canDecide = isPending && hasRole("reviewer");
  const notifyError = (error: unknown) => notify(describeError(error), "error");

  const toggleExclusion = (plan: ExtractedPlan) =>
    actions.setExclusion.mutate({ extractedPlanId: plan.id, excluded: !plan.is_excluded }, { onError: notifyError });
  const confirmMapping = (plan: ExtractedPlan) =>
    plan.plan &&
    actions.mapPlan.mutate({ extractedPlanId: plan.id, planId: plan.plan.id }, { onError: notifyError });
  const reprocess = () =>
    actions.reprocess.mutate(undefined, {
      onSuccess: (detail) => navigate(`/batches/${detail.id}`),
      onError: notifyError,
    });

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: t("review.breadcrumb"), to: "/batches" }]}
        title={t("review.title", { operator: batch.operator.name })}
        status={
          <Badge tone={batchStatusTone(batch.status)} dot>
            {tEnum("batchStatus", batch.status)}
          </Badge>
        }
        actions={
          canDecide && (
            <>
              <Button variant="danger" icon={<XCircle size={16} />} onClick={() => setDecision("reject")}>
                {t("review.reject")}
              </Button>
              <Button
                variant="primary"
                icon={<CheckCircle2 size={16} />}
                disabled={!batch.can_publish}
                aria-describedby={batch.can_publish ? undefined : PUBLISH_BLOCKED_ID}
                onClick={() => setDecision("publish")}
              >
                {t("review.publish")}
              </Button>
            </>
          )
        }
      />
      {canDecide && !batch.can_publish && (
        <p id={PUBLISH_BLOCKED_ID} className="callout tone-warning">
          <TriangleAlert size={16} aria-hidden="true" />
          <span>{t("review.publishBlocked")}</span>
        </p>
      )}
      <BatchMeta batch={batch} canEditDates={canEdit} onEditDates={() => setDatesOpen(true)} />
      <StatusBanner
        batch={batch}
        canReprocess={hasRole("analyst")}
        reprocessing={actions.reprocess.isPending}
        onReprocess={reprocess}
      />
      {batch.status !== "failed" && (
        <>
          <ReviewSummary summary={batch.summary} />
          <div className="review-layout">
            <PriceGrid
              batch={batch}
              severity={severity}
              highlightedCell={highlightedCell}
              canEdit={canEdit}
              onSelectCell={(plan, price) => setSelectedCell({ plan, price })}
              onMapPlan={setMappingPlan}
              onToggleExclusion={toggleExclusion}
            />
            <IssuePanel
              batch={batch}
              canEdit={canEdit}
              onShowCell={setHighlightedCell}
              onAcknowledge={setAcknowledgedIssue}
              onMapPlan={setMappingPlan}
              onConfirmMapping={confirmMapping}
              onExcludePlan={toggleExclusion}
            />
          </div>
        </>
      )}
      <ActivityFeed events={[...batch.timeline].reverse()} title={t("review.timelineTitle")} />

      <CellDialog
        selection={selectedCell}
        canEdit={canEdit}
        actions={actions}
        onClose={() => {
          actions.correctPrice.reset();
          setSelectedCell(null);
        }}
      />
      <MappingDialog
        key={mappingPlan?.id ?? "mapping"}
        batch={batch}
        plan={mappingPlan}
        actions={actions}
        onClose={() => {
          actions.mapPlan.reset();
          setMappingPlan(null);
        }}
      />
      <AcknowledgeDialog
        key={acknowledgedIssue?.id ?? "acknowledge"}
        issue={acknowledgedIssue}
        actions={actions}
        onClose={() => {
          actions.acknowledge.reset();
          setAcknowledgedIssue(null);
        }}
      />
      <DatesDialog
        key={datesOpen ? "dates-open" : "dates-closed"}
        batch={batch}
        open={datesOpen}
        actions={actions}
        onClose={() => {
          actions.updateDates.reset();
          setDatesOpen(false);
        }}
      />
      <DecisionDialog
        key={decision ?? "decision"}
        mode={decision}
        actions={actions}
        onClose={() => {
          actions.publish.reset();
          actions.reject.reset();
          setDecision(null);
        }}
      />
    </>
  );
}

interface StatusBannerProps {
  batch: BatchDetail;
  canReprocess: boolean;
  reprocessing: boolean;
  onReprocess: () => void;
}

function StatusBanner({ batch, canReprocess, reprocessing, onReprocess }: StatusBannerProps) {
  if (batch.status === "failed") {
    return (
      <div className="callout tone-error" role="status">
        <XCircle size={18} aria-hidden="true" />
        <div className="stack">
          <div className="stack-sm">
            <span className="callout-title">{t("review.failedTitle")}</span>
            <span>{batch.failure_message}</span>
            <span className="small muted">{t("review.failedHint")}</span>
          </div>
          {canReprocess && (
            <div>
              <Button size="sm" icon={<RefreshCw size={14} />} disabled={reprocessing} onClick={onReprocess}>
                {reprocessing ? t("common.working") : t("review.reprocess")}
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }
  if (batch.status === "published") {
    return (
      <div className="callout tone-success">
        <CheckCircle2 size={18} aria-hidden="true" />
        <span>
          {t("review.publishedBanner", {
            date: formatDateTime(batch.reviewed_at),
            by: batch.auto_published ? t("common.automatic") : describeActor(batch.reviewed_by?.display_name),
          })}
          {batch.review_note ? ` “${batch.review_note}”` : ""}
        </span>
      </div>
    );
  }
  if (batch.status === "rejected") {
    return (
      <div className="callout tone-warning">
        <XCircle size={18} aria-hidden="true" />
        <span>
          {t("review.rejectedBanner", {
            date: formatDateTime(batch.reviewed_at),
            by: describeActor(batch.reviewed_by?.display_name),
            reason: batch.review_note,
          })}
        </span>
      </div>
    );
  }
  if (batch.extraction_method === "llm") {
    return (
      <div className="callout">
        <Sparkles size={18} aria-hidden="true" />
        <span>{t("review.aiNotice")}</span>
      </div>
    );
  }
  return null;
}
