export type Uuid = string;
export type IsoDate = string;
export type IsoDateTime = string;
export type Money = string;

export type Role = "analyst" | "reviewer";

export interface UserSummary {
  username: string;
  display_name: string;
}

export interface CurrentUser extends UserSummary {
  roles: Role[];
}

export interface AuthSession {
  token: string;
  user: CurrentUser;
}

export type AccessLevel = "automated" | "manual_channel" | "contact_dependent" | "no_access";

export interface OperatorSummary {
  id: Uuid;
  name: string;
  ans_registration: string;
  is_fictional: boolean;
}

export interface Operator extends OperatorSummary {
  cnpj: string;
  modality: string;
  access_level: AccessLevel;
}

export interface PlanSummary {
  id: Uuid;
  name: string;
  product_line: string;
  ans_code: string;
  contract_type: string;
  accommodation: string;
  coverage_area: string;
  segmentation: string;
  has_coparticipation: boolean;
  is_active: boolean;
}

export interface Plan extends PlanSummary {
  operator: OperatorSummary;
}

export type FreshnessStatus = "fresh" | "due" | "overdue" | "never_checked";

export interface Freshness {
  status: FreshnessStatus;
  last_success_at: IsoDateTime | null;
  last_new_material_at: IsoDateTime | null;
  last_failure_at: IsoDateTime | null;
  days_since_success: number | null;
}

export type SourceChannel =
  | "operator_portal"
  | "email_inbox"
  | "partner"
  | "broker"
  | "manual_upload";

export interface SourceSummary {
  id: Uuid;
  name: string;
  channel: SourceChannel;
  trust_level: number;
}

export interface Source extends SourceSummary {
  expected_update_days: number;
  tolerance_days: number;
  contact: string;
  auto_approve: boolean;
  operator: OperatorSummary;
  freshness: Freshness;
}

export interface SourceCheck {
  id: Uuid;
  checked_at: IsoDateTime;
  outcome: "new_material" | "unchanged" | "failed";
  note: string;
  checked_by: UserSummary | null;
  document_id: Uuid | null;
  document_filename: string | null;
}

export type BatchStatus = "pending_review" | "published" | "rejected" | "failed";
export type ExtractionMethod = "grid" | "llm" | "none";
export type Severity = "error" | "warning" | "info";
export type IssueStatus = "open" | "acknowledged" | "resolved";
export type MatchMethod = "alias" | "similarity" | "manual" | "unmatched";

export interface DocumentSummary {
  id: Uuid;
  filename: string;
  file_format: string;
  size_bytes: number;
  sha256: string;
  received_at: IsoDateTime;
  uploaded_by: UserSummary | null;
}

export interface BatchSummary {
  id: Uuid;
  status: BatchStatus;
  region: string;
  effective_from: IsoDate | null;
  effective_until: IsoDate | null;
  extraction_method: ExtractionMethod;
  created_at: IsoDateTime;
  reviewed_at: IsoDateTime | null;
  reviewed_by: UserSummary | null;
  review_note: string;
  auto_published: boolean;
  failure_code: string;
  failure_message: string | null;
  operator: OperatorSummary;
  source: SourceSummary;
  document: DocumentSummary;
  counts: { plans: number; open_errors: number; open_warnings: number };
}

export interface CellLocation {
  page?: number;
  sheet?: string;
  cell?: string;
  band_text?: string;
  plan_text?: string;
  method?: string;
}

export interface ExtractedPrice {
  id: Uuid;
  age_band: number;
  band_label: string;
  raw_text: string;
  extracted_value: Money | null;
  corrected_value: Money | null;
  final_value: Money | null;
  previous_value: Money | null;
  change: string | null;
  location: CellLocation;
  corrected_by: UserSummary | null;
  corrected_at: IsoDateTime | null;
}

export interface ExtractedPlan {
  id: Uuid;
  label: string;
  position: number;
  plan: PlanSummary | null;
  match_method: MatchMethod;
  match_score: number | null;
  suggestions: string[];
  is_excluded: boolean;
  prices: ExtractedPrice[];
}

export interface ValidationIssue {
  id: Uuid;
  rule_code: string;
  severity: Severity;
  status: IssueStatus;
  message: string;
  extracted_plan_id: Uuid | null;
  age_band: number | null;
  params: Record<string, unknown>;
  acknowledged_by: UserSummary | null;
  acknowledged_at: IsoDateTime | null;
  acknowledgement_note: string;
  resolved_at: IsoDateTime | null;
}

export interface AuditEvent {
  occurred_at: IsoDateTime;
  action: string;
  actor: UserSummary | null;
  operator_name: string | null;
  target_type: string;
  target_id: Uuid | null;
  payload: Record<string, unknown>;
}

export interface BatchReviewSummary {
  plans: number;
  excluded_plans: number;
  prices: number;
  compared_prices: number;
  changed_prices: number;
  corrected_prices: number;
  median_change: string | null;
  open_errors: number;
  open_warnings: number;
  acknowledged: number;
  infos: number;
}

export interface BatchDetail extends BatchSummary {
  plans: ExtractedPlan[];
  issues: ValidationIssue[];
  summary: BatchReviewSummary;
  can_publish: boolean;
  plan_candidates: PlanSummary[];
  timeline: AuditEvent[];
}

export interface AnsReference {
  status: string;
  status_label: string;
  status_date: IsoDate | null;
  note_code: number | null;
  note_registered_at: IsoDate | null;
}

export interface PriceEntry {
  age_band: number;
  band_label: string;
  value: Money;
  was_corrected: boolean;
  location: CellLocation;
}

export interface PriceTableProvenance {
  id: Uuid;
  region: string;
  effective_from: IsoDate;
  effective_until: IsoDate | null;
  recorded_at: IsoDateTime;
  superseded_at: IsoDateTime | null;
  batch_id: Uuid;
  auto_published: boolean;
  published_by: UserSummary | null;
  published_at: IsoDateTime | null;
  extraction_method: ExtractionMethod;
  document: DocumentSummary;
  source: SourceSummary;
}

export type TableState = "current" | "scheduled" | "expired" | "superseded";

export interface PriceTableVersion extends PriceTableProvenance {
  state: TableState;
  derived_from_id: Uuid | null;
  superseded_by_batch_id: Uuid | null;
  entries: PriceEntry[];
}

export interface PlanPricing {
  plan: Plan;
  ans: AnsReference | null;
  versions: PriceTableVersion[];
}

export interface QuoteRequest {
  ages: number[];
  on_date: IsoDate;
  region: string;
  operator?: Uuid | null;
  known_at?: IsoDateTime | null;
}

export interface BeneficiaryPrice {
  age: number;
  age_band: number;
  band_label: string;
  value: Money;
}

export interface ScheduledChange {
  effective_from: IsoDate;
  total: Money;
  change: string;
  table_id: Uuid;
}

export interface PlanQuote {
  plan: Plan;
  total: Money;
  beneficiaries: BeneficiaryPrice[];
  table: PriceTableProvenance;
  freshness: Freshness | null;
  ans: AnsReference | null;
  scheduled_change: ScheduledChange | null;
}

export interface Alert {
  id: Uuid;
  kind: string;
  severity: Severity;
  status: "open" | "resolved";
  message: string;
  operator_id: Uuid | null;
  operator_name: string | null;
  source_id: Uuid | null;
  plan_id: Uuid | null;
  plan_is_active: boolean | null;
  opened_at: IsoDateTime;
  last_seen_at: IsoDateTime;
}

export interface OperatorHealth {
  operator: Operator;
  status: FreshnessStatus;
  sources: Source[];
  active_plans: number;
  priced_plans: number;
  oldest_effective_from: IsoDate | null;
  next_change_on: IsoDate | null;
  open_alerts: number;
  pending_batches: number;
}

export interface Dashboard {
  generated_at: IsoDateTime;
  pending_batches: number;
  open_errors: number;
  open_warnings: number;
  active_plans: number;
  priced_plans: number;
  confirmed_plans: number;
  operators: OperatorHealth[];
  alerts: Alert[];
  recent_events: AuditEvent[];
}

export interface BatchReference {
  id: Uuid;
  status: BatchStatus;
}

export interface DemoDelivery {
  key: string;
  title: string;
  description: string;
  operator_name: string;
  channel: SourceChannel;
  layout: string;
  filename: string;
  latest_batch: BatchReference | null;
}

export interface CollectionOutcome {
  filename: string;
  status: "received" | "unchanged" | "unidentified";
  batch: BatchReference | null;
  source_name: string | null;
}

export interface BrokerReportInput {
  plan: Uuid;
  region: string;
  quoted_on: IsoDate;
  reported_value: Money | null;
  message: string;
  reporter_name: string;
  reporter_contact: string;
}

export interface EffectiveDatesInput {
  effective_from: IsoDate | null;
  effective_until: IsoDate | null;
  region: string;
}
