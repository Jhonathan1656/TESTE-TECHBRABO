import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, ChevronDown, ChevronRight } from "lucide-react";
import { Fragment, useState } from "react";

import { sourceApi } from "../../shared/api/endpoints";
import { describeError } from "../../shared/api/errors";
import type { Source } from "../../shared/api/types";
import { useAuth } from "../../shared/auth/AuthContext";
import { Badge } from "../../shared/components/Badge";
import { Button } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { Dialog } from "../../shared/components/Dialog";
import { PageHeader } from "../../shared/components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { TableScroll } from "../../shared/components/TableScroll";
import { freshnessTone, trustTone } from "../../shared/components/tones";
import { formatDateTime } from "../../shared/format/format";
import { describeDaysAgo } from "../../shared/format/relative";
import { t, tEnum } from "../../shared/i18n/translate";

export function SourcesPage() {
  const sources = useQuery({ queryKey: ["sources"], queryFn: sourceApi.list });
  const [expanded, setExpanded] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<Source | null>(null);
  const { hasRole } = useAuth();

  return (
    <>
      <PageHeader title={t("sources.title")} subtitle={t("sources.subtitle")} />
      <Card flush>
        {sources.isPending && <LoadingState />}
        {sources.isError && <ErrorState error={sources.error} onRetry={() => void sources.refetch()} />}
        {sources.data && (
          <TableScroll label={t("sources.title")}>
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">{t("sources.columnSource")}</th>
                  <th scope="col">{t("sources.columnChannel")}</th>
                  <th scope="col">{t("sources.columnCadence")}</th>
                  <th scope="col">{t("sources.columnLastSuccess")}</th>
                  <th scope="col">{t("sources.columnStatus")}</th>
                  <th scope="col">
                    <span className="visually-hidden">{t("sources.columnActions")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sources.data.map((source) => (
                  <Fragment key={source.id}>
                    <tr>
                      <th scope="row">
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => setExpanded(expanded === source.id ? null : source.id)}
                          aria-expanded={expanded === source.id}
                          aria-controls={`checks-${source.id}`}
                        >
                          {expanded === source.id ? (
                            <ChevronDown size={14} aria-hidden="true" />
                          ) : (
                            <ChevronRight size={14} aria-hidden="true" />
                          )}
                          {source.name}
                        </button>
                        <div className="cell-sub">
                          {source.operator.name} · {source.contact}
                        </div>
                      </th>
                      <td>
                        <div className="row">
                          {tEnum("channel", source.channel)}
                          <Badge tone={trustTone(source.trust_level)}>{tEnum("trust", source.trust_level)}</Badge>
                        </div>
                      </td>
                      <td>
                        {t("sources.cadence", { days: source.expected_update_days })}
                        {source.auto_approve && <div className="cell-sub">{t("sources.autoApprove")}</div>}
                      </td>
                      <td className="nowrap">
                        {describeDaysAgo(source.freshness.days_since_success)}
                        <div className="cell-sub numeric">{formatDateTime(source.freshness.last_success_at)}</div>
                      </td>
                      <td>
                        <Badge tone={freshnessTone(source.freshness.status)} dot>
                          {tEnum("freshness", source.freshness.status)}
                        </Badge>
                      </td>
                      <td className="align-right">
                        {hasRole("analyst") && (
                          <Button size="sm" icon={<BadgeCheck size={14} />} onClick={() => setConfirming(source)}>
                            {t("sources.confirm")}
                          </Button>
                        )}
                      </td>
                    </tr>
                    {expanded === source.id && (
                      <tr id={`checks-${source.id}`} className="expanded-row">
                        <td colSpan={6}>
                          <SourceChecks sourceId={source.id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </TableScroll>
        )}
      </Card>
      <ConfirmSourceDialog key={confirming?.id ?? "confirm"} source={confirming} onClose={() => setConfirming(null)} />
    </>
  );
}

const VISIBLE_CHECKS = 8;

function SourceChecks({ sourceId }: { sourceId: string }) {
  const checks = useQuery({ queryKey: ["source-checks", sourceId], queryFn: () => sourceApi.checks(sourceId) });
  const [showAll, setShowAll] = useState(false);
  if (checks.isPending) {
    return <LoadingState lines={2} />;
  }
  if (checks.isError) {
    return <ErrorState error={checks.error} />;
  }
  if (checks.data.length === 0) {
    return <EmptyState>{t("sources.checksEmpty")}</EmptyState>;
  }
  return (
    <div className="source-checks">
      <h2 className="meta-label">{t("sources.checksTitle")}</h2>
      {(showAll ? checks.data : checks.data.slice(0, VISIBLE_CHECKS)).map((check) => (
        <div key={check.id} className="source-check">
          <time className="numeric subtle" dateTime={check.checked_at}>
            {formatDateTime(check.checked_at)}
          </time>
          <Badge tone={check.outcome === "failed" ? "error" : check.outcome === "new_material" ? "primary" : "success"}>
            {tEnum("checkOutcome", check.outcome)}
          </Badge>
          {check.document_filename && (
            <span className="break-anywhere" translate="no">
              {check.document_filename}
            </span>
          )}
          {check.note && <span className="muted">“{check.note}”</span>}
          {check.checked_by && <span className="subtle">{check.checked_by.display_name}</span>}
        </div>
      ))}
      {!showAll && checks.data.length > VISIBLE_CHECKS && (
        <div>
          <Button size="sm" variant="ghost" onClick={() => setShowAll(true)}>
            {t("sources.checksShowAll", { count: checks.data.length })}
          </Button>
        </div>
      )}
    </div>
  );
}

function ConfirmSourceDialog({ source, onClose }: { source: Source | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const confirm = useMutation({
    mutationFn: () => sourceApi.confirm(source!.id, note.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
      void queryClient.invalidateQueries({ queryKey: ["source-checks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });
  if (!source) {
    return <Dialog open={false} title="" onClose={onClose} />;
  }
  return (
    <Dialog
      open
      title={t("sources.confirmTitle")}
      description={`${source.name}. ${t("sources.confirmHint")}`}
      busy={confirm.isPending}
      error={confirm.isError ? describeError(confirm.error) : null}
      onSubmit={() => confirm.mutate()}
      onClose={onClose}
    >
      <label className="field">
        <span className="label">{t("sources.confirmNote")}</span>
        <textarea
          className="textarea"
          name="note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          autoFocus
        />
      </label>
    </Dialog>
  );
}
