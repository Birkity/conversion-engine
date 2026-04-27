import fs from 'fs';
import path from 'path';
import type {
  CompanySignals,
  HiringBrief,
  CompetitorGapBrief,
  ProspectInfo,
  LastEmail,
  ProbeResult,
  ProbeCase,
  ScenarioLog,
  AblationResults,
  InvoiceSummary,
  CompanySlug,
  CompanyData,
  ConversationState,
} from './types';
import { COMPANY_SLUGS } from './utils';

const ROOT = path.join(process.cwd(), '..');

function readJson<T>(relPath: string): T | null {
  const abs = path.join(ROOT, relPath);
  try {
    const raw = fs.readFileSync(abs, 'utf8');
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function getSignals(slug: CompanySlug): CompanySignals | null {
  return readJson<CompanySignals>(`traces/${slug}/signals.json`);
}

export function getHiringBrief(slug: CompanySlug): HiringBrief | null {
  return readJson<HiringBrief>(`traces/${slug}/hiring_signal_brief.json`);
}

export function getCompetitorGap(slug: CompanySlug): CompetitorGapBrief | null {
  return readJson<CompetitorGapBrief>(`traces/${slug}/competitor_gap_brief.json`);
}

export function getProspectInfo(slug: CompanySlug): ProspectInfo | null {
  return readJson<ProspectInfo>(`traces/${slug}/prospect_info.json`);
}

export function getLastEmail(slug: CompanySlug): LastEmail | null {
  return readJson<LastEmail>(`artifacts/${slug}/last_email.json`);
}

export function getConversationState(slug: CompanySlug): ConversationState | null {
  return readJson<ConversationState>(`artifacts/${slug}/conversation_state.json`);
}

export function getAllCompanyData(): CompanyData[] {
  return COMPANY_SLUGS.map((slug) => ({
    slug,
    signals: getSignals(slug),
    brief: getHiringBrief(slug),
    gap: getCompetitorGap(slug),
    prospect: getProspectInfo(slug),
    email: getLastEmail(slug),
    conversationState: getConversationState(slug),
  }));
}

export function getProbeResults(): ProbeResult[] {
  return readJson<ProbeResult[]>('probes/probe_results.json') ?? [];
}

export function getProbeCases(): ProbeCase[] {
  return readJson<ProbeCase[]>('probes/probe_cases.json') ?? [];
}

export function getDemoLog(): ScenarioLog[] {
  return readJson<ScenarioLog[]>('demo/demo_log.json') ?? [];
}

export function getAblationResults(): AblationResults | null {
  return readJson<AblationResults>('ablation_results.json');
}

export function getInvoiceSummary(): InvoiceSummary | null {
  return readJson<InvoiceSummary>('invoice_summary.json');
}
