import type { HiringBrief } from '@/lib/types';
import { getSegmentColor, getVelocityInfo, cn } from '@/lib/utils';
import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

interface Props {
  brief: HiringBrief | null;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-slate-800 last:border-0">
      <div className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide bg-slate-800/30">
        {title}
      </div>
      <div className="px-4 py-3">{children}</div>
    </div>
  );
}

function KV({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex gap-2 mb-1.5 last:mb-0">
      <span className="text-xs text-slate-500 w-32 flex-shrink-0">{label}</span>
      <span className={cn('text-xs', highlight ? 'text-emerald-300' : 'text-slate-300')}>{value}</span>
    </div>
  );
}

export default function HiringBriefAccordion({ brief }: Props) {
  if (!brief) return null;

  const velocity = getVelocityInfo(
    brief.hiring_velocity?.direction,
    brief.hiring_velocity?.delta_pct ?? null
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-300">Hiring Signal Brief</h3>
          <div className="flex items-center gap-2">
            <span className={cn('inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium', getSegmentColor(brief.icp_segment))}>
              {brief.icp_segment}
            </span>
            <span className="text-xs text-slate-500">
              {Math.round((brief.confidence ?? 0) * 100)}% confident
            </span>
          </div>
        </div>
        {brief.recommended_pitch_angle && (
          <p className="text-xs text-slate-400 mt-1.5 italic">&ldquo;{brief.recommended_pitch_angle}&rdquo;</p>
        )}
      </div>

      <Section title="Hiring Velocity">
        <KV label="Direction" value={velocity.label} />
        <KV label="Signal strength" value={brief.hiring_velocity?.signal_strength ?? '–'} />
        <KV label="Observation" value={brief.hiring_velocity?.observation ?? '–'} />
      </Section>

      <Section title="Budget & Cost">
        <KV label="Budget urgency" value={brief.budget_urgency?.level ?? '–'} highlight />
        {brief.budget_urgency?.signal && <KV label="Signal" value={brief.budget_urgency.signal} />}
        <KV label="Cost pressure" value={brief.cost_pressure?.present ? 'Present' : 'Absent'} />
        {brief.cost_pressure?.icp_segment_implication && (
          <KV label="ICP implication" value={brief.cost_pressure.icp_segment_implication} />
        )}
      </Section>

      <Section title="Bench Match">
        <div className="flex flex-wrap gap-1 mb-2">
          {(brief.bench_match?.required_stacks ?? []).map((s) => (
            <span key={s} className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-xs text-slate-300">
              {s}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          {brief.bench_match?.bench_available ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
          )}
          <span className={cn('text-xs', brief.bench_match?.bench_available ? 'text-emerald-400' : 'text-rose-400')}>
            Bench {brief.bench_match?.bench_available ? 'available' : 'unavailable'}
          </span>
        </div>
      </Section>

      {/* Honesty flags */}
      {(brief.honesty_flags?.weak_hiring_velocity_signal || brief.honesty_flags?.bench_gap_detected || brief.disqualifiers?.length) && (
        <Section title="Flags & Warnings">
          {brief.honesty_flags?.weak_hiring_velocity_signal && (
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs text-amber-400">Weak hiring velocity signal</span>
            </div>
          )}
          {brief.honesty_flags?.bench_gap_detected && (
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-xs text-rose-400">Bench gap detected</span>
            </div>
          )}
          {brief.disqualifiers?.map((d, i) => (
            <div key={i} className="flex items-center gap-1.5 mb-1.5">
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-xs text-rose-400">{d}</span>
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}
