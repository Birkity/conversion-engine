export interface CompetitorSignal {
  name: string;
  funding: string;
  tech_stack: string[];
  ai_maturity_score: number;
}

export interface CompanySignals {
  company_name: string;
  industries: string[];
  headcount: string;
  description?: string;
  funding_info: string;
  layoffs: string;
  jobs_now: number;
  jobs_60_days: number;
  tech_stack: string[];
  ai_roles: string[];
  leadership_changes: string;
  recent_news: string;
  competitor_signals: CompetitorSignal[];
}

export interface HiringVelocity {
  direction: string;
  delta_pct: number | null;
  signal_strength: string;
  observation: string;
}

export interface BudgetUrgency {
  level: string;
  signal: string | null;
  runway_pressure: string | null;
}

export interface CostPressure {
  present: boolean;
  signal: string | null;
  icp_segment_implication: string | null;
}

export interface EngineeringMaturity {
  stack_sophistication: string;
  detected_stack: string[];
  bench_match_notes: string;
}

export interface AIMaturityRationale {
  ai_roles_found: string[];
  modern_ml_stack_signals: string[];
  executive_ai_signals: string;
  named_ai_leadership: boolean;
}

export interface BenchMatch {
  required_stacks: string[];
  bench_available: boolean;
}

export interface HonestyFlags {
  weak_hiring_velocity_signal: boolean;
  bench_gap_detected: boolean;
}

export interface HiringBrief {
  company: string;
  hiring_velocity: HiringVelocity;
  budget_urgency: BudgetUrgency;
  cost_pressure: CostPressure;
  engineering_maturity: EngineeringMaturity;
  ai_maturity_score: number;
  ai_maturity_rationale: AIMaturityRationale;
  confidence: number;
  icp_segment: string;
  recommended_pitch_angle: string;
  bench_match: BenchMatch;
  honesty_flags: HonestyFlags;
  tenacious_status?: string;
  disqualifiers?: string[];
}

export interface GapItem {
  practice: string;
  evidence_in_top_quartile: string;
  evidence_at_prospect: string;
  gap_insight: string;
  confidence: number;
}

export interface CompetitorGapBrief {
  sector: string;
  competitors_analyzed: number;
  prospect_ai_score: number;
  prospect_position_in_sector: string;
  gaps: GapItem[];
  overall_confidence: number;
  tenacious_status?: string;
  statistical_note?: string;
}

export interface ProspectInfo {
  name: string;
  role: string;
  email: string;
  phone?: string;
  company: string;
}

export interface LastEmail {
  subject: string;
  body: string;
  grounding_facts?: string[];
  icp_segment_used?: string;
  timestamp?: string;
  company: string;
  prospect_email: string;
}

export interface ProbeResult {
  id: number;
  category: string;
  reply: string;
  expected_intent: string;
  expected_next_step: string;
  actual_intent: string;
  actual_next_step: string;
  confidence: number;
  reasoning: string;
  grounding_facts_used: string[];
  passed: boolean;
  intent_ok: boolean;
  step_ok: boolean;
  elapsed_s: number;
  risk_explained: string;
}

export interface ProbeCase {
  id: number;
  category: string;
  reply: string;
  expected_intent: string;
  expected_next_step: string;
  risk_explained: string;
  trigger_rate_per_1000?: number;
  business_cost_per_event_usd?: number;
}

export interface Interpretation {
  intent: string;
  next_step: string;
  confidence: number;
  reasoning: string;
  grounding_facts_used: string[];
}

export interface Routing {
  actions: string[];
  errors: string[];
  cal_link: string | null;
}

export interface SMSStatus {
  attempted: boolean;
  delivered: boolean;
  routed_to_sink: boolean;
  at_status?: string;
  error?: string;
}

export interface ConversationTurn {
  turn: number;
  from: 'agent' | 'prospect';
  type?: string;
  subject?: string;
  body?: string;
  grounding_facts?: string[];
  icp_segment_used?: string;
  sink_mode?: boolean;
  reply_text?: string;
  channel?: string;
  expected_intent?: string;
  expected_next_step?: string;
  interpretation?: Interpretation;
  routing?: Routing;
  sms?: SMSStatus | null;
  tone_warnings?: string[];
  timestamp?: string;
}

export interface ScenarioLog {
  scenario_id: string;
  company: string;
  segment: string;
  description: string;
  conversation: ConversationTurn[];
  ran_at: string;
}

export interface AblationCondition {
  description: string;
  pass_at_1: number;
  passed: number;
  total: number;
  ci_95: [number, number];
}

export interface AblationResults {
  conditions: {
    day1_baseline: AblationCondition;
    act4_method: AblationCondition;
  };
  delta_a: {
    value: number;
    value_pp: string;
    z_statistic: number;
    p_value: number;
    significant: boolean;
    ci_95_delta: [number, number];
  };
}

export interface InvoiceSummary {
  period: string;
  openrouter: {
    weekly_spend_usd: number;
  };
  cost_per_qualified_lead_usd: {
    low: number;
    high: number;
  };
  total_weekly_usd: number;
}

export type CompanySlug =
  | 'arcana'
  | 'brightpath'
  | 'coraltech'
  | 'kinanalytics'
  | 'novaspark'
  | 'pulsesight'
  | 'snaptrade'
  | 'streamlineops'
  | 'wiseitech';

export type PipelineStatus = 'idle' | 'waiting_for_reply' | 'processing' | 'booked' | 'stopped';

export interface ConversationState {
  slug: string;
  company: string;
  prospect_email: string | null;
  status: PipelineStatus;
  turns: ConversationTurn[];
  started_at: string | null;
  last_updated: string | null;
  outcome: string | null;
}

export interface CompanyData {
  slug: string; // CompanySlug for builtins, arbitrary string for custom companies
  signals: CompanySignals | null;
  brief: HiringBrief | null;
  gap: CompetitorGapBrief | null;
  prospect: ProspectInfo | null;
  email: LastEmail | null;
  conversationState: ConversationState | null;
}
