import { useState } from "react";

import { describeError } from "../../shared/api/errors";
import type { BatchDetail, ExtractedPlan, ValidationIssue } from "../../shared/api/types";
import { Dialog } from "../../shared/components/Dialog";
import { t } from "../../shared/i18n/translate";
import type { BatchActions } from "./useBatchActions";

interface MappingDialogProps {
  batch: BatchDetail;
  plan: ExtractedPlan | null;
  actions: BatchActions;
  onClose: () => void;
}

export function MappingDialog({ batch, plan, actions, onClose }: MappingDialogProps) {
  const [planId, setPlanId] = useState(plan?.plan?.id ?? "");
  const mutation = actions.mapPlan;
  if (!plan) {
    return <Dialog open={false} title="" onClose={onClose} />;
  }
  return (
    <Dialog
      open
      title={t("review.mappingTitle", { label: plan.label })}
      description={t("review.mappingHint")}
      submitDisabled={!planId}
      busy={mutation.isPending}
      error={mutation.isError ? describeError(mutation.error) : null}
      onSubmit={() => mutation.mutate({ extractedPlanId: plan.id, planId }, { onSuccess: onClose })}
      onClose={onClose}
    >
      <label className="field">
        <span className="label">{t("review.mappingField")}</span>
        <select
          className="select"
          name="plan"
          value={planId}
          onChange={(event) => setPlanId(event.target.value)}
          required
          autoFocus
        >
          <option value="" />
          {batch.plan_candidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.name}
            </option>
          ))}
        </select>
        {plan.suggestions.length > 0 && (
          <span className="hint">{t("review.mappingSuggestions", { names: plan.suggestions.join(", ") })}</span>
        )}
      </label>
    </Dialog>
  );
}

interface AcknowledgeDialogProps {
  issue: ValidationIssue | null;
  actions: BatchActions;
  onClose: () => void;
}

export function AcknowledgeDialog({ issue, actions, onClose }: AcknowledgeDialogProps) {
  const [note, setNote] = useState("");
  const mutation = actions.acknowledge;
  if (!issue) {
    return <Dialog open={false} title="" onClose={onClose} />;
  }
  return (
    <Dialog
      open
      title={t("review.acknowledgeTitle")}
      description={issue.message}
      submitDisabled={note.trim().length === 0}
      busy={mutation.isPending}
      error={mutation.isError ? describeError(mutation.error) : null}
      onSubmit={() => mutation.mutate({ issueId: issue.id, note: note.trim() }, { onSuccess: onClose })}
      onClose={onClose}
    >
      <label className="field">
        <span className="label">{t("review.acknowledgeNote")}</span>
        <textarea
          className="textarea"
          name="note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          required
          autoFocus
        />
        <span className="hint">{t("review.acknowledgeHint")}</span>
      </label>
    </Dialog>
  );
}

interface DatesDialogProps {
  batch: BatchDetail;
  open: boolean;
  actions: BatchActions;
  onClose: () => void;
}

export function DatesDialog({ batch, open, actions, onClose }: DatesDialogProps) {
  const [effectiveFrom, setEffectiveFrom] = useState(batch.effective_from ?? "");
  const [effectiveUntil, setEffectiveUntil] = useState(batch.effective_until ?? "");
  const [region, setRegion] = useState(batch.region);
  const mutation = actions.updateDates;
  return (
    <Dialog
      open={open}
      title={t("review.datesTitle")}
      busy={mutation.isPending}
      error={mutation.isError ? describeError(mutation.error) : null}
      onSubmit={() =>
        mutation.mutate(
          { effective_from: effectiveFrom || null, effective_until: effectiveUntil || null, region },
          { onSuccess: onClose },
        )
      }
      onClose={onClose}
    >
      <label className="field">
        <span className="label">{t("review.datesFrom")}</span>
        <input
          className="input input-narrow"
          type="date"
          name="effective_from"
          value={effectiveFrom}
          onChange={(event) => setEffectiveFrom(event.target.value)}
        />
      </label>
      <label className="field">
        <span className="label">{t("review.datesUntil")}</span>
        <input
          className="input input-narrow"
          type="date"
          name="effective_until"
          value={effectiveUntil}
          onChange={(event) => setEffectiveUntil(event.target.value)}
        />
      </label>
      <label className="field">
        <span className="label">{t("review.datesRegion")}</span>
        <input
          className="input"
          name="region"
          autoComplete="off"
          value={region}
          maxLength={80}
          onChange={(event) => setRegion(event.target.value)}
        />
      </label>
    </Dialog>
  );
}

interface DecisionDialogProps {
  mode: "publish" | "reject" | null;
  actions: BatchActions;
  onClose: () => void;
}

export function DecisionDialog({ mode, actions, onClose }: DecisionDialogProps) {
  const [text, setText] = useState("");
  const isPublish = mode === "publish";
  const mutation = isPublish ? actions.publish : actions.reject;
  if (!mode) {
    return <Dialog open={false} title="" onClose={onClose} />;
  }
  return (
    <Dialog
      open
      title={isPublish ? t("review.publishTitle") : t("review.rejectTitle")}
      description={isPublish ? t("review.publishDescription") : undefined}
      submitLabel={isPublish ? t("review.publish") : t("review.reject")}
      submitVariant={isPublish ? "primary" : "destructive"}
      submitDisabled={!isPublish && text.trim().length === 0}
      busy={mutation.isPending}
      error={mutation.isError ? describeError(mutation.error) : null}
      onSubmit={() => mutation.mutate(text.trim(), { onSuccess: onClose })}
      onClose={onClose}
    >
      <label className="field">
        <span className="label">{isPublish ? t("review.publishNote") : t("review.rejectReason")}</span>
        <textarea
          className="textarea"
          name={isPublish ? "note" : "reason"}
          value={text}
          onChange={(event) => setText(event.target.value)}
          required={!isPublish}
          autoFocus
        />
      </label>
    </Dialog>
  );
}
