import { ExternalLink, Pencil } from "lucide-react";
import type { ReactNode } from "react";

import { batchApi } from "../../shared/api/endpoints";
import type { BatchDetail } from "../../shared/api/types";
import { Badge } from "../../shared/components/Badge";
import { trustTone } from "../../shared/components/tones";
import { formatDateTime, formatFileSize, formatIsoDate } from "../../shared/format/format";
import { t, tEnum } from "../../shared/i18n/translate";

interface BatchMetaProps {
  batch: BatchDetail;
  canEditDates: boolean;
  onEditDates: () => void;
}

export function BatchMeta({ batch, canEditDates, onEditDates }: BatchMetaProps) {
  return (
    <dl className="meta-grid">
      <MetaItem label={t("review.document")}>
        <button
          type="button"
          className="link-button break-anywhere"
          translate="no"
          onClick={() => void batchApi.openDocument(batch.document.id)}
        >
          {batch.document.filename}
          <ExternalLink size={13} aria-hidden="true" />
        </button>
        <span className="cell-sub">
          {formatFileSize(batch.document.size_bytes)} ·{" "}
          <code translate="no" title={batch.document.sha256}>
            sha256 {batch.document.sha256.slice(0, 10)}…
          </code>
        </span>
      </MetaItem>
      <MetaItem label={t("review.source")}>
        <span>{batch.source.name}</span>
        <span className="row">
          <Badge tone="info">{tEnum("channel", batch.source.channel)}</Badge>
          <Badge tone={trustTone(batch.source.trust_level)}>{tEnum("trust", batch.source.trust_level)}</Badge>
        </span>
      </MetaItem>
      <MetaItem label={t("review.effective")}>
        <span className="numeric">{describeEffectivePeriod(batch)}</span>
        {canEditDates && (
          <button type="button" className="link-button small" onClick={onEditDates}>
            <Pencil size={12} aria-hidden="true" />
            {t("review.editDates")}
          </button>
        )}
      </MetaItem>
      <MetaItem label={t("review.region")}>{batch.region || t("review.regionMissing")}</MetaItem>
      <MetaItem label={t("review.extraction")}>{tEnum("extractionMethod", batch.extraction_method)}</MetaItem>
      <MetaItem label={t("review.received")}>
        <span className="numeric">{formatDateTime(batch.document.received_at)}</span>
        <span className="cell-sub">
          {batch.document.uploaded_by
            ? t("review.uploadedBy", { name: batch.document.uploaded_by.display_name })
            : tEnum("channel", batch.source.channel)}
        </span>
      </MetaItem>
    </dl>
  );
}

function MetaItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="meta-item">
      <dt className="meta-label">{label}</dt>
      <dd className="meta-value">{children}</dd>
    </div>
  );
}

function describeEffectivePeriod(batch: BatchDetail): string {
  if (!batch.effective_from) {
    return t("review.effectiveMissing");
  }
  if (batch.effective_until) {
    return t("review.effectiveRange", {
      from: formatIsoDate(batch.effective_from),
      until: formatIsoDate(batch.effective_until),
    });
  }
  return t("review.effectiveFrom", { date: formatIsoDate(batch.effective_from) });
}
