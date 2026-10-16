import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Download, Send } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { demoApi } from "../../shared/api/endpoints";
import { describeError } from "../../shared/api/errors";
import type { DemoDelivery } from "../../shared/api/types";
import { useAuth } from "../../shared/auth/AuthContext";
import { Badge } from "../../shared/components/Badge";
import { Button, ButtonLink } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { useToast } from "../../shared/components/toast";
import { batchStatusTone } from "../../shared/components/tones";
import { t, tEnum } from "../../shared/i18n/translate";

export function DemoDeliveries() {
  const deliveries = useQuery({ queryKey: ["demo-deliveries"], queryFn: demoApi.deliveries, retry: false });

  if (!deliveries.data) {
    return null;
  }
  return (
    <Card title={t("dashboard.demoTitle")} hint={t("dashboard.demoSubtitle")} flush>
      <ul className="delivery-grid">
        {deliveries.data.map((delivery) => (
          <DeliveryItem key={delivery.key} delivery={delivery} />
        ))}
      </ul>
    </Card>
  );
}

function DeliveryItem({ delivery }: { delivery: DemoDelivery }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const { notify } = useToast();

  const collect = useMutation({
    mutationFn: () => demoApi.collect(delivery.key),
    onSuccess: (outcome) => {
      notify(tEnum("collection", outcome.status));
      void queryClient.invalidateQueries();
      if (outcome.status === "received" && outcome.batch) {
        navigate(`/batches/${outcome.batch.id}`);
      }
    },
    onError: (error) => notify(describeError(error), "error"),
  });
  const download = useMutation({
    mutationFn: () => demoApi.download(delivery.key, delivery.filename || `${delivery.key}.bin`),
    onError: (error) => notify(describeError(error), "error"),
  });

  return (
    <li className="delivery">
      <span className="delivery-title">{delivery.title}</span>
      <div className="row">
        <Badge tone="info">{tEnum("channel", delivery.channel)}</Badge>
        {delivery.latest_batch && (
          <Badge tone={batchStatusTone(delivery.latest_batch.status)} dot>
            {tEnum("batchStatus", delivery.latest_batch.status)}
          </Badge>
        )}
      </div>
      <p className="delivery-description">{delivery.description}</p>
      <div className="delivery-footer">
        <span className="subtle small">{delivery.operator_name}</span>
        <div className="row">
          {delivery.layout !== "resend" && (
            <Button
              size="sm"
              variant="ghost"
              icon={<Download size={14} />}
              disabled={download.isPending}
              onClick={() => download.mutate()}
            >
              {t("dashboard.demoDownload")}
            </Button>
          )}
          {delivery.latest_batch ? (
            <ButtonLink size="sm" to={`/batches/${delivery.latest_batch.id}`} icon={<ArrowRight size={14} />}>
              {t("dashboard.demoOpenBatch")}
            </ButtonLink>
          ) : (
            hasRole("analyst") && (
              <Button
                size="sm"
                variant="primary"
                icon={<Send size={14} />}
                disabled={collect.isPending}
                onClick={() => collect.mutate()}
              >
                {collect.isPending ? t("common.working") : t("dashboard.demoCollect")}
              </Button>
            )
          )}
        </div>
      </div>
    </li>
  );
}
