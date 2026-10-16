import { downloadFile, openFileInNewTab, request } from "./http";
import type {
  Alert,
  AuthSession,
  BatchDetail,
  BatchStatus,
  BatchSummary,
  BrokerReportInput,
  CollectionOutcome,
  CurrentUser,
  Dashboard,
  DemoDelivery,
  EffectiveDatesInput,
  Operator,
  Plan,
  PlanPricing,
  PlanQuote,
  QuoteRequest,
  Source,
  SourceCheck,
  Uuid,
} from "./types";

export const authApi = {
  login: (username: string, password: string) =>
    request<AuthSession>("/auth/login", { method: "POST", json: { username, password } }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<CurrentUser>("/auth/me"),
};

export const monitoringApi = {
  dashboard: () => request<Dashboard>("/dashboard"),
  runChecks: () => request<unknown>("/monitoring/runs", { method: "POST" }),
  resolveAlert: (alertId: Uuid) =>
    request<Alert>(`/alerts/${alertId}/resolution`, { method: "POST" }),
  reportDivergence: (input: BrokerReportInput) =>
    request<unknown>("/broker-reports", { method: "POST", json: input }),
};

const batchPath = (batchId: Uuid) => `/batches/${batchId}`;

export const batchApi = {
  list: (status?: BatchStatus) => request<BatchSummary[]>("/batches", { query: { status } }),
  get: (batchId: Uuid) => request<BatchDetail>(batchPath(batchId)),
  upload: (form: FormData) =>
    request<BatchDetail>("/documents", { method: "POST", formData: form }),
  correctPrice: (batchId: Uuid, priceId: Uuid, correctedValue: string | null) =>
    request<BatchDetail>(`${batchPath(batchId)}/prices/${priceId}`, {
      method: "PATCH",
      json: { corrected_value: correctedValue },
    }),
  mapPlan: (batchId: Uuid, extractedPlanId: Uuid, planId: Uuid) =>
    request<BatchDetail>(`${batchPath(batchId)}/plans/${extractedPlanId}/mapping`, {
      method: "POST",
      json: { plan: planId },
    }),
  setExclusion: (batchId: Uuid, extractedPlanId: Uuid, excluded: boolean) =>
    request<BatchDetail>(`${batchPath(batchId)}/plans/${extractedPlanId}/exclusion`, {
      method: "POST",
      json: { excluded },
    }),
  acknowledgeIssue: (batchId: Uuid, issueId: Uuid, note: string) =>
    request<BatchDetail>(`${batchPath(batchId)}/issues/${issueId}/acknowledgement`, {
      method: "POST",
      json: { note },
    }),
  updateEffectiveDates: (batchId: Uuid, dates: EffectiveDatesInput) =>
    request<BatchDetail>(`${batchPath(batchId)}/effective-dates`, { method: "PUT", json: dates }),
  publish: (batchId: Uuid, note: string) =>
    request<BatchDetail>(`${batchPath(batchId)}/publication`, { method: "POST", json: { note } }),
  reject: (batchId: Uuid, reason: string) =>
    request<BatchDetail>(`${batchPath(batchId)}/rejection`, { method: "POST", json: { reason } }),
  reprocess: (batchId: Uuid) =>
    request<BatchDetail>(`${batchPath(batchId)}/reprocessing`, { method: "POST" }),
  openDocument: (documentId: Uuid) => openFileInNewTab(`/documents/${documentId}/file`),
  downloadDocument: (documentId: Uuid, filename: string) =>
    downloadFile(`/documents/${documentId}/file`, filename),
};

export const sourceApi = {
  list: () => request<Source[]>("/sources"),
  checks: (sourceId: Uuid) => request<SourceCheck[]>(`/sources/${sourceId}/checks`),
  confirm: (sourceId: Uuid, note: string) =>
    request<Source>(`/sources/${sourceId}/confirmations`, { method: "POST", json: { note } }),
};

export const catalogApi = {
  operators: () => request<Operator[]>("/operators"),
  plans: (includeInactive = false) =>
    request<Plan[]>("/plans", { query: { include_inactive: includeInactive } }),
  deactivatePlan: (planId: Uuid) =>
    request<Plan>(`/plans/${planId}/deactivation`, { method: "POST" }),
};

export const pricingApi = {
  regions: () => request<string[]>("/regions"),
  quote: (input: QuoteRequest) => request<PlanQuote[]>("/quotes", { method: "POST", json: input }),
  planPricing: (planId: Uuid) => request<PlanPricing>(`/plans/${planId}/pricing`),
};

export const demoApi = {
  deliveries: () => request<DemoDelivery[]>("/demo/deliveries"),
  collect: (key: string) =>
    request<CollectionOutcome>(`/demo/deliveries/${key}/collection`, { method: "POST" }),
  download: (key: string, filename: string) =>
    downloadFile(`/demo/deliveries/${key}/file`, filename),
};
