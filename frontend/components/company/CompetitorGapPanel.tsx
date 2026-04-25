import type { CompetitorGapBrief } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  gap: CompetitorGapBrief | null;
}

function PositionBadge({ position }: { position: string }) {
  const map: Record<string, string> = {
    top_quartile: 'text-emerald-300 bg-emerald-950 border-emerald-800',
    above_median: 'text-blue-300 bg-blue-950 border-blue-800',
    below_median: 'text-amber-300 bg-amber-950 border-amber-800',
    at_median: 'text-slate-300 bg-slate-800 border-slate-700',
  };
  const style = map[position] ?? 'text-slate-300 bg-slate-800 border-slate-700';
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium', style)}>
      {position.replace(/_/g, ' ')}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? 'bg-emerald-500' : value >= 0.5 ? 'bg-amber-500' : 'bg-slate-600';
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500 tabular-nums w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function CompetitorGapPanel({ gap }: Props) {
  if (!gap) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Competitor Gap Analysis</h3>
        <div className="border border-dashed border-slate-700 rounded-lg p-4 text-center text-sm text-slate-500">
          No competitor gap data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">Competitor Gap Analysis</h3>

      {/* Summary row */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="bg-slate-800 rounded-lg px-3 py-2">
          <div className="text-xs text-slate-500">Sector</div>
          <div className="text-sm text-slate-200 font-medium">{gap.sector}</div>
        </div>
        <div className="bg-slate-800 rounded-lg px-3 py-2">
          <div className="text-xs text-slate-500">Competitors</div>
          <div className="text-sm text-slate-200 font-medium">{gap.competitors_analyzed} analyzed</div>
        </div>
        <div className="bg-slate-800 rounded-lg px-3 py-2">
          <div className="text-xs text-slate-500">Prospect AI Score</div>
          <div className="text-sm text-slate-200 font-medium">{gap.prospect_ai_score}/3</div>
        </div>
      </div>

      {/* Sector position */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-slate-500">Position in sector:</span>
        <PositionBadge position={gap.prospect_position_in_sector} />
      </div>

      {gap.statistical_note && (
        <div className="text-xs text-amber-400/80 mb-3 bg-amber-950/30 border border-amber-900/40 rounded px-3 py-2">
          ⚠ {gap.statistical_note}
        </div>
      )}

      {/* Overall confidence */}
      <div className="mb-4">
        <div className="text-xs text-slate-500 mb-1">Overall confidence</div>
        <ConfidenceBar value={gap.overall_confidence} />
      </div>

      {/* Gaps */}
      {gap.gaps?.length > 0 && (
        <div className="space-y-3 border-t border-slate-800 pt-3">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide">Identified Gaps</div>
          {gap.gaps.map((g, i) => (
            <div key={i} className="bg-slate-800/50 rounded-lg p-3 text-xs space-y-2">
              <div className="font-medium text-slate-200">{g.practice}</div>
              <div className="space-y-1">
                <div className="text-slate-500">Top quartile: <span className="text-slate-300">{g.evidence_in_top_quartile}</span></div>
                <div className="text-slate-500">Prospect: <span className="text-slate-300">{g.evidence_at_prospect}</span></div>
              </div>
              <div className="text-slate-400 italic">{g.gap_insight}</div>
              <div>
                <div className="text-slate-600 mb-0.5">Confidence</div>
                <ConfidenceBar value={g.confidence} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
