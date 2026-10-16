import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, FileCheck2, FileUp, UploadCloud } from "lucide-react";
import { type DragEvent, type FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { batchApi, sourceApi } from "../../shared/api/endpoints";
import { describeError, readErrorParam } from "../../shared/api/errors";
import type { Source } from "../../shared/api/types";
import { useAuth } from "../../shared/auth/AuthContext";
import { Button } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { PageHeader } from "../../shared/components/PageHeader";
import { ErrorState, LoadingState } from "../../shared/components/States";
import { formatFileSize } from "../../shared/format/format";
import { t, tEnum, tList } from "../../shared/i18n/translate";

const ACCEPTED_FILES = ".pdf,.xlsx,.csv";

export function UploadPage() {
  const sources = useQuery({ queryKey: ["sources"], queryFn: sourceApi.list });

  return (
    <>
      <PageHeader title={t("upload.title")} subtitle={t("upload.subtitle")} />
      {sources.isPending && <LoadingState lines={6} />}
      {sources.isError && <ErrorState error={sources.error} onRetry={() => void sources.refetch()} />}
      {sources.data && (
        <div className="upload-layout">
          <UploadForm sources={sources.data} />
          <Card title={t("upload.howTitle")}>
            <ol className="steps">
              {tList("upload.howSteps").map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </Card>
        </div>
      )}
    </>
  );
}

function UploadForm({ sources }: { sources: Source[] }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const [sourceId, setSourceId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveUntil, setEffectiveUntil] = useState("");
  const [region, setRegion] = useState("");

  const sourcesByOperator = useMemo(() => groupByOperator(sources), [sources]);

  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("file", file!);
      form.append("source", sourceId);
      if (effectiveFrom) form.append("effective_from", effectiveFrom);
      if (effectiveUntil) form.append("effective_until", effectiveUntil);
      if (region) form.append("region", region);
      return batchApi.upload(form);
    },
    onSuccess: (batch) => {
      void queryClient.invalidateQueries();
      navigate(`/batches/${batch.id}`);
    },
  });

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) {
      setFile(dropped);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    upload.mutate();
  };

  const duplicateBatch = readErrorParam(upload.error, "batch");

  return (
    <Card>
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="field span-2">
          <label className="label" htmlFor="upload-source">
            {t("upload.source")}
          </label>
          <select
            id="upload-source"
            className="select"
            name="source"
            value={sourceId}
            onChange={(event) => setSourceId(event.target.value)}
            required
          >
            <option value="">{t("upload.sourcePlaceholder")}</option>
            {sourcesByOperator.map(([operatorName, items]) => (
              <optgroup key={operatorName} label={operatorName}>
                {items.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name} · {tEnum("channel", source.channel)}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="field span-2">
          <span className="label" id="upload-file-label">
            {t("upload.file")}
          </span>
          {/* A native file input inside its label: click, keyboard (focus + Space) and drop all work without scripts. */}
          <label
            className="dropzone"
            data-dragging={dragging}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <span className="dropzone-icon" aria-hidden="true">
              {file ? <FileCheck2 size={20} /> : <UploadCloud size={20} />}
            </span>
            {file ? (
              <span className="dropzone-file" translate="no">
                {file.name} · {formatFileSize(file.size)}
              </span>
            ) : (
              <span className="dropzone-title">{t("upload.fileDrop")}</span>
            )}
            <span className="hint">{t("upload.fileHint")}</span>
            <input
              className="visually-hidden"
              type="file"
              name="file"
              accept={ACCEPTED_FILES}
              aria-labelledby="upload-file-label"
              aria-describedby="upload-file-status"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <span id="upload-file-status" className="visually-hidden" aria-live="polite">
            {file ? `${t("upload.fileSelected")}: ${file.name}` : t("upload.fileHint")}
          </span>
        </div>
        <div className="field">
          <label className="label" htmlFor="upload-effective-from">
            {t("upload.effectiveFrom")}
            <span className="label-optional">({t("common.optional")})</span>
          </label>
          <input
            id="upload-effective-from"
            className="input"
            type="date"
            name="effective_from"
            value={effectiveFrom}
            onChange={(event) => setEffectiveFrom(event.target.value)}
            aria-describedby="upload-detect-hint"
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="upload-effective-until">
            {t("upload.effectiveUntil")}
            <span className="label-optional">({t("common.optional")})</span>
          </label>
          <input
            id="upload-effective-until"
            className="input"
            type="date"
            name="effective_until"
            value={effectiveUntil}
            onChange={(event) => setEffectiveUntil(event.target.value)}
          />
        </div>
        <div className="field span-2">
          <label className="label" htmlFor="upload-region">
            {t("upload.region")}
            <span className="label-optional">({t("common.optional")})</span>
          </label>
          <input
            id="upload-region"
            className="input"
            name="region"
            autoComplete="off"
            value={region}
            maxLength={80}
            onChange={(event) => setRegion(event.target.value)}
            aria-describedby="upload-detect-hint"
          />
          <span id="upload-detect-hint" className="hint">
            {t("upload.optional")}
          </span>
        </div>
        {upload.isError && (
          <div className="form-error span-2" role="alert">
            <CircleAlert size={16} aria-hidden="true" />
            <span>
              {describeError(upload.error)}{" "}
              {duplicateBatch && <Link to={`/batches/${duplicateBatch}`}>{t("upload.duplicateLink")}</Link>}
            </span>
          </div>
        )}
        <div className="form-actions span-2">
          <Button
            type="submit"
            variant="primary"
            icon={<FileUp size={16} />}
            disabled={!file || !sourceId || upload.isPending || !hasRole("analyst")}
          >
            {upload.isPending ? t("upload.submitting") : t("upload.submit")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function groupByOperator(sources: Source[]): [string, Source[]][] {
  const groups = new Map<string, Source[]>();
  sources.forEach((source) => {
    const items = groups.get(source.operator.name) ?? [];
    items.push(source);
    groups.set(source.operator.name, items);
  });
  return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right, "pt-BR"));
}
