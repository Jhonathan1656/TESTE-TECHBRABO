import type { BatchDetail, ExtractedPlan, ExtractedPrice, ValidationIssue } from "../../shared/api/types";

export function buildPrice(overrides: Partial<ExtractedPrice> = {}): ExtractedPrice {
  return {
    id: `price-${overrides.age_band ?? 1}`,
    age_band: 1,
    band_label: "0–18",
    raw_text: "R$ 233,22",
    extracted_value: "233.22",
    corrected_value: null,
    final_value: "233.22",
    previous_value: "212.40",
    change: "0.0980",
    location: { page: 1, cell: "L3C2", band_text: "00 a 18 anos", plan_text: "Essencial Enfermaria" },
    corrected_by: null,
    corrected_at: null,
    ...overrides,
  };
}

export function buildExtractedPlan(overrides: Partial<ExtractedPlan> = {}): ExtractedPlan {
  return {
    id: "plan-a",
    label: "Essencial Enfermaria",
    position: 0,
    plan: null,
    match_method: "alias",
    match_score: 1,
    suggestions: [],
    is_excluded: false,
    prices: [buildPrice()],
    ...overrides,
  };
}

export function buildIssue(overrides: Partial<ValidationIssue> = {}): ValidationIssue {
  return {
    id: "issue-1",
    rule_code: "consistency.non_uniform_adjustment",
    severity: "warning",
    status: "open",
    message: "Mensagem",
    extracted_plan_id: "plan-a",
    age_band: 1,
    params: {},
    acknowledged_by: null,
    acknowledged_at: null,
    acknowledgement_note: "",
    resolved_at: null,
    ...overrides,
  };
}

export function buildBatch(overrides: Partial<BatchDetail> = {}): BatchDetail {
  return {
    id: "batch-1",
    status: "pending_review",
    region: "São Paulo – Capital",
    effective_from: "2026-11-01",
    effective_until: null,
    extraction_method: "grid",
    created_at: "2026-10-16T10:00:00-03:00",
    reviewed_at: null,
    reviewed_by: null,
    review_note: "",
    auto_published: false,
    failure_code: "",
    failure_message: null,
    operator: { id: "op-1", name: "Operadora Teste", ans_registration: "900011", is_fictional: true },
    source: { id: "src-1", name: "Portal", channel: "operator_portal", trust_level: 3 },
    document: {
      id: "doc-1",
      filename: "tabela.pdf",
      file_format: "pdf",
      size_bytes: 3000,
      sha256: "abc123abc123abc123",
      received_at: "2026-10-16T10:00:00-03:00",
      uploaded_by: null,
    },
    counts: { plans: 1, open_errors: 0, open_warnings: 1 },
    plans: [buildExtractedPlan()],
    issues: [],
    summary: {
      plans: 1,
      excluded_plans: 0,
      prices: 1,
      compared_prices: 1,
      changed_prices: 1,
      corrected_prices: 0,
      median_change: "0.0980",
      open_errors: 0,
      open_warnings: 0,
      acknowledged: 0,
      infos: 0,
    },
    can_publish: true,
    plan_candidates: [],
    timeline: [],
    ...overrides,
  };
}
