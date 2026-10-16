import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { monitoringApi } from "../../shared/api/endpoints";
import { describeError } from "../../shared/api/errors";
import type { PlanQuote } from "../../shared/api/types";
import { Dialog } from "../../shared/components/Dialog";
import { useToast } from "../../shared/components/toast";
import { parseBrazilianMoney } from "../../shared/format/format";
import { t } from "../../shared/i18n/translate";

interface BrokerReportDialogProps {
  quote: PlanQuote | null;
  onDate: string;
  onClose: () => void;
}

export function BrokerReportDialog({ quote, onDate, onClose }: BrokerReportDialogProps) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [value, setValue] = useState("");
  const [message, setMessage] = useState("");
  const [reporterName, setReporterName] = useState("");
  const [contact, setContact] = useState("");

  const report = useMutation({
    mutationFn: monitoringApi.reportDivergence,
    onSuccess: () => {
      notify(t("quote.reportSent"));
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });

  if (!quote) {
    return <Dialog open={false} title="" onClose={onClose} />;
  }
  const parsedValue = value ? parseBrazilianMoney(value) : null;
  const canSubmit = message.trim() && reporterName.trim() && (!value || parsedValue);

  return (
    <Dialog
      open
      title={t("quote.reportTitle")}
      description={`${quote.plan.name} · ${quote.table.region}. ${t("quote.reportHint")}`}
      submitLabel={t("quote.report")}
      submitDisabled={!canSubmit}
      busy={report.isPending}
      error={report.isError ? describeError(report.error) : null}
      onSubmit={() =>
        report.mutate({
          plan: quote.plan.id,
          region: quote.table.region,
          quoted_on: onDate,
          reported_value: parsedValue,
          message: message.trim(),
          reporter_name: reporterName.trim(),
          reporter_contact: contact.trim(),
        })
      }
      onClose={onClose}
    >
      <label className="field">
        <span className="label">{t("quote.reportMessage")}</span>
        <textarea
          className="textarea"
          name="message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          required
          autoFocus
        />
      </label>
      <label className="field">
        <span className="label">{t("quote.reportValue")}</span>
        <input
          className="input numeric input-narrow"
          name="reported_value"
          inputMode="decimal"
          autoComplete="off"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </label>
      <label className="field">
        <span className="label">{t("quote.reportName")}</span>
        <input
          className="input"
          name="reporter_name"
          autoComplete="name"
          value={reporterName}
          onChange={(event) => setReporterName(event.target.value)}
          required
        />
      </label>
      <label className="field">
        <span className="label">{t("quote.reportContact")}</span>
        <input
          className="input"
          name="reporter_contact"
          autoComplete="off"
          value={contact}
          onChange={(event) => setContact(event.target.value)}
        />
      </label>
    </Dialog>
  );
}
