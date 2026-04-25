import { CheckCircle2, XCircle } from 'lucide-react';
import type { AIMaturityRationale } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  score: number;
  rationale: AIMaturityRationale | null;
}

const labels = ['No signal', 'Emerging', 'Active', 'Advanced'];
const colors = ['bg-slate-700', 'bg-amber-400', 'bg-emerald-400', 'bg-emerald-300'];
const textColors = ['text-slate-500', 'text-amber-400', 'text-emerald-400', 'text-emerald-300'];

export default function AIMaturityGauge({ score, rationale }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">AI Maturity Score</h3>

      {/* Score display */}
      <div className="flex items-center gap-4 mb-4">
        <div className={cn('text-5xl font-bold tabular-nums', textColors[score])}>{score}</div>
        <div>
          <div className={cn('text-sm font-semibold', textColors[score])}>{labels[score]}</div>
          <div className="text-xs text-slate-500">out of 3</div>
        </div>
      </div>

      {/* Segmented bar */}
      <div className="flex gap-1 mb-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={cn(
              'h-2.5 flex-1 rounded-full transition-all',
              i < score ? colors[score] : 'bg-slate-800'
            )}
          />
        ))}
      </div>

      {/* Rationale checklist */}
      {rationale && (
        <div className="space-y-1.5 text-xs">
          <RationaleItem
            label={`AI roles: ${rationale.ai_roles_found?.join(', ') || 'none'}`}
            present={rationale.ai_roles_found?.length > 0}
          />
          <RationaleItem
            label={`ML stack: ${rationale.modern_ml_stack_signals?.join(', ') || 'none'}`}
            present={rationale.modern_ml_stack_signals?.length > 0}
          />
          <RationaleItem
            label={`Named AI leadership: ${rationale.named_ai_leadership ? 'yes' : 'no'}`}
            present={rationale.named_ai_leadership}
          />
          <RationaleItem
            label={`Exec AI signals: ${rationale.executive_ai_signals || 'none'}`}
            present={!!rationale.executive_ai_signals && rationale.executive_ai_signals !== 'none'}
          />
        </div>
      )}
    </div>
  );
}

function RationaleItem({ label, present }: { label: string; present: boolean }) {
  return (
    <div className="flex items-start gap-1.5">
      {present ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
      ) : (
        <XCircle className="w-3.5 h-3.5 text-slate-600 mt-0.5 flex-shrink-0" />
      )}
      <span className={present ? 'text-slate-300' : 'text-slate-600'}>{label}</span>
    </div>
  );
}
