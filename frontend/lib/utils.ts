import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { CompanySlug } from './types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const COMPANY_SLUGS: CompanySlug[] = [
  'arcana',
  'brightpath',
  'coraltech',
  'kinanalytics',
  'novaspark',
  'pulsesight',
  'snaptrade',
  'streamlineops',
  'wiseitech',
];

export const COMPANY_DISPLAY_NAMES: Record<CompanySlug, string> = {
  arcana: 'Arcana Analytics',
  brightpath: 'BrightPath',
  coraltech: 'CoralTech',
  kinanalytics: 'KinAnalytics',
  novaspark: 'NovaSpark',
  pulsesight: 'PulseSight',
  snaptrade: 'SnapTrade',
  streamlineops: 'StreamlineOps',
  wiseitech: 'WiseiTech',
};

export function slugToDisplayName(slug: string): string {
  return COMPANY_DISPLAY_NAMES[slug as CompanySlug] ?? slug;
}

export function getSegmentColor(segment: string): string {
  if (!segment) return 'text-slate-400 bg-slate-800 border-slate-700';
  const s = segment.toLowerCase();
  if (s.includes('segment 1')) return 'text-emerald-300 bg-emerald-950 border-emerald-800';
  if (s.includes('segment 2')) return 'text-blue-300 bg-blue-950 border-blue-800';
  if (s.includes('segment 3')) return 'text-violet-300 bg-violet-950 border-violet-800';
  if (s.includes('segment 4')) return 'text-cyan-300 bg-cyan-950 border-cyan-800';
  if (s.includes('ambiguous')) return 'text-amber-300 bg-amber-950 border-amber-800';
  if (s.includes('disqualified')) return 'text-rose-300 bg-rose-950 border-rose-800';
  return 'text-slate-400 bg-slate-800 border-slate-700';
}

export function formatIcpSegment(segment: string): string {
  if (!segment) return '';
  const s = segment.toLowerCase();
  if (s.includes('segment 1')) return 'Segment 1 · Series A';
  if (s.includes('segment 2')) return 'Segment 2 · Post-Layoff';
  if (s.includes('segment 3')) return 'Segment 3 · New Leadership';
  if (s.includes('segment 4')) return 'Segment 4 · AI Gap';
  if (s.includes('ambiguous')) return 'Ambiguous';
  if (s.includes('disqualified')) return 'Disqualified';
  return segment;
}

export function getVelocityInfo(direction: string | undefined, deltaPct: number | null) {
  if (!direction || direction === 'unknown' || deltaPct === null) {
    return { label: 'Insufficient data', color: 'text-amber-400', arrow: '–' };
  }
  if (direction === 'accelerating' || deltaPct > 0) {
    return { label: `↑ ${Math.abs(deltaPct)}%`, color: 'text-emerald-400', arrow: '↑' };
  }
  if (direction === 'decelerating' || deltaPct < 0) {
    return { label: `↓ ${Math.abs(deltaPct)}%`, color: 'text-rose-400', arrow: '↓' };
  }
  return { label: direction, color: 'text-slate-400', arrow: '–' };
}

export function getMaturityColor(score: number): string {
  if (score === 0) return 'text-slate-400';
  if (score === 1) return 'text-amber-400';
  if (score === 2) return 'text-emerald-400';
  return 'text-emerald-300';
}

export function formatConfidence(val: number): string {
  return Math.round(val * 100) + '%';
}

export function getIntentColor(intent: string): string {
  switch (intent) {
    case 'INTERESTED': return 'text-emerald-300 bg-emerald-950 border-emerald-700';
    case 'SCHEDULE': return 'text-blue-300 bg-blue-950 border-blue-700';
    case 'QUESTION': return 'text-amber-300 bg-amber-950 border-amber-700';
    case 'NOT_INTERESTED': return 'text-rose-300 bg-rose-950 border-rose-700';
    case 'UNKNOWN': return 'text-slate-300 bg-slate-800 border-slate-600';
    default: return 'text-slate-300 bg-slate-800 border-slate-600';
  }
}

export function getNextStepColor(step: string): string {
  switch (step) {
    case 'SEND_CAL_LINK': return 'text-emerald-300 bg-emerald-950 border-emerald-700';
    case 'SEND_EMAIL': return 'text-blue-300 bg-blue-950 border-blue-700';
    case 'ASK_CLARIFICATION': return 'text-amber-300 bg-amber-950 border-amber-700';
    case 'STOP': return 'text-rose-300 bg-rose-950 border-rose-700';
    default: return 'text-slate-300 bg-slate-800 border-slate-600';
  }
}
