import { useMutation, useQueryClient } from "@tanstack/react-query";

import { batchApi } from "../../shared/api/endpoints";
import type { BatchDetail, EffectiveDatesInput, Uuid } from "../../shared/api/types";

export function batchQueryKey(batchId: Uuid) {
  return ["batch", batchId] as const;
}

export function useBatchActions(batchId: Uuid) {
  const queryClient = useQueryClient();

  const applyDetail = (detail: BatchDetail) => {
    queryClient.setQueryData(batchQueryKey(detail.id), detail);
    void queryClient.invalidateQueries({ queryKey: ["batches"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["demo-deliveries"] });
  };

  return {
    correctPrice: useMutation({
      mutationFn: ({ priceId, value }: { priceId: Uuid; value: string | null }) =>
        batchApi.correctPrice(batchId, priceId, value),
      onSuccess: applyDetail,
    }),
    mapPlan: useMutation({
      mutationFn: ({ extractedPlanId, planId }: { extractedPlanId: Uuid; planId: Uuid }) =>
        batchApi.mapPlan(batchId, extractedPlanId, planId),
      onSuccess: applyDetail,
    }),
    setExclusion: useMutation({
      mutationFn: ({ extractedPlanId, excluded }: { extractedPlanId: Uuid; excluded: boolean }) =>
        batchApi.setExclusion(batchId, extractedPlanId, excluded),
      onSuccess: applyDetail,
    }),
    acknowledge: useMutation({
      mutationFn: ({ issueId, note }: { issueId: Uuid; note: string }) =>
        batchApi.acknowledgeIssue(batchId, issueId, note),
      onSuccess: applyDetail,
    }),
    updateDates: useMutation({
      mutationFn: (dates: EffectiveDatesInput) => batchApi.updateEffectiveDates(batchId, dates),
      onSuccess: applyDetail,
    }),
    publish: useMutation({
      mutationFn: (note: string) => batchApi.publish(batchId, note),
      onSuccess: (detail) => {
        applyDetail(detail);
        void queryClient.invalidateQueries({ queryKey: ["plans"] });
        void queryClient.invalidateQueries({ queryKey: ["plan-pricing"] });
      },
    }),
    reject: useMutation({
      mutationFn: (reason: string) => batchApi.reject(batchId, reason),
      onSuccess: applyDetail,
    }),
    reprocess: useMutation({
      mutationFn: () => batchApi.reprocess(batchId),
      onSuccess: applyDetail,
    }),
  };
}

export type BatchActions = ReturnType<typeof useBatchActions>;
