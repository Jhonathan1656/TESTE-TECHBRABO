import { CircleAlert } from "lucide-react";
import { useId, useState } from "react";

import { describeError } from "../../shared/api/errors";
import type { ExtractedPlan, ExtractedPrice } from "../../shared/api/types";
import { Button } from "../../shared/components/Button";
import { Dialog } from "../../shared/components/Dialog";
import { formatChange, formatMoney, parseBrazilianMoney } from "../../shared/format/format";
import { t } from "../../shared/i18n/translate";
import { AGE_BAND_LABELS, formatPlainMoney } from "./reviewModel";
import type { BatchActions } from "./useBatchActions";

interface CellDialogProps {
  selection: { plan: ExtractedPlan; price: ExtractedPrice } | null;
  canEdit: boolean;
  actions: BatchActions;
  onClose: () => void;
}

export function CellDialog({ selection, canEdit, actions, onClose }: CellDialogProps) {
  if (!selection) {
    return <Dialog open={false} title="" onClose={onClose} />;
  }
  return (
    <CellDialogContent
      key={selection.price.id}
      selection={selection}
      canEdit={canEdit}
      actions={actions}
      onClose={onClose}
    />
  );
}

function CellDialogContent({ selection, canEdit, actions, onClose }: CellDialogProps & { selection: NonNullable<CellDialogProps["selection"]> }) {
  const { plan, price } = selection;
  const [value, setValue] = useState(formatPlainMoney(price.corrected_value ?? price.final_value));
  const parsed = parseBrazilianMoney(value);
  const invalid = value.trim() !== "" && parsed === null;
  const hintId = useId();
  const errorId = useId();
  const mutation = actions.correctPrice;

  const save = (corrected: string | null) =>
    mutation.mutate({ priceId: price.id, value: corrected }, { onSuccess: onClose });

  return (
    <Dialog
      open
      title={t("review.cellTitle", { plan: plan.label, band: AGE_BAND_LABELS[price.age_band - 1] })}
      submitLabel={t("review.cellSave")}
      submitDisabled={!canEdit || parsed === null}
      busy={mutation.isPending}
      error={mutation.isError ? describeError(mutation.error) : null}
      onSubmit={canEdit ? () => save(parsed) : undefined}
      onClose={onClose}
    >
      <dl className="definition-list">
        <dt>{t("review.cellRaw")}</dt>
        <dd>
          <code className="raw-value" translate="no">
            {price.raw_text}
          </code>
        </dd>
        <dt>{t("review.cellLocation")}</dt>
        <dd>{describeLocation(price)}</dd>
        <dt>{t("review.cellExtracted")}</dt>
        <dd className="numeric">{formatMoney(price.extracted_value)}</dd>
        <dt>{t("review.cellPrevious")}</dt>
        <dd className="numeric">{formatMoney(price.previous_value)}</dd>
        <dt>{t("review.cellChange")}</dt>
        <dd className="numeric">{formatChange(price.change)}</dd>
        {price.corrected_by && (
          <>
            <dt>{t("review.corrected")}</dt>
            <dd>{t("review.cellCorrectedBy", { name: price.corrected_by.display_name })}</dd>
          </>
        )}
      </dl>
      {canEdit && (
        <div className="field">
          <label className="label" htmlFor={`${hintId}-input`}>
            {t("review.cellCorrection")}
          </label>
          <input
            id={`${hintId}-input`}
            className="input numeric input-narrow"
            name="corrected_value"
            inputMode="decimal"
            autoComplete="off"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            aria-invalid={invalid || undefined}
            aria-describedby={invalid ? `${errorId} ${hintId}` : hintId}
            autoFocus
          />
          {invalid && (
            <span id={errorId} className="field-error">
              <CircleAlert size={14} aria-hidden="true" />
              {t("review.cellInvalid")}
            </span>
          )}
          <span id={hintId} className="hint">
            {t("review.cellCorrectionHint")}
          </span>
        </div>
      )}
      {canEdit && price.corrected_value && (
        <div>
          <Button size="sm" variant="ghost" disabled={mutation.isPending} onClick={() => save(null)}>
            {t("review.cellUndo")}
          </Button>
        </div>
      )}
    </Dialog>
  );
}

function describeLocation(price: ExtractedPrice): string {
  const { location } = price;
  const parts = [
    location.page ? t("review.cellLocationPage", { page: location.page }) : null,
    location.sheet ? t("review.cellLocationSheet", { sheet: location.sheet }) : null,
    location.cell ? t("review.cellLocationCell", { cell: location.cell }) : null,
    location.method === "llm" ? t("enums.extractionMethod.llm") : null,
  ].filter(Boolean);
  const labels = [location.band_text, location.plan_text].filter(Boolean).join(" × ");
  return [parts.join(", "), labels].filter(Boolean).join(" · ") || t("common.none");
}
