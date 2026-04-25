import { DollarSign, Users, TrendingUp, Layers, Bot, Newspaper, AlertTriangle } from 'lucide-react';
import type { CompanySignals } from '@/lib/types';

interface Props {
  signals: CompanySignals | null;
  companyName: string;
}

function Pill({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-xs text-slate-300 mr-1 mb-1">
      {text}
    </span>
  );
}

function Row({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color?: string }) {
  return (
    <div className="flex gap-3 items-start py-2 border-b border-slate-800/60 last:border-0">
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${color ?? 'text-slate-500'}`} />
      <div>
        <div className="text-xs text-slate-500">{label}</div>
        <div className="text-sm text-slate-200 mt-0.5">{value}</div>
      </div>
    </div>
  );
}

export default function SignalsPanel({ signals, companyName }: Props) {
  if (!signals) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Enrichment Signals</h3>
        <div className="border border-dashed border-slate-700 rounded-lg p-4 text-center text-sm text-slate-500">
          Enrichment data not available for {companyName}
        </div>
      </div>
    );
  }

  const velocityText =
    signals.jobs_now !== undefined
      ? `${signals.jobs_now} open roles now (was ${signals.jobs_60_days} / 60 days ago)`
      : 'No velocity data';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Enrichment Signals</h3>
      <div className="space-y-0">
        <Row icon={DollarSign} label="Funding" value={signals.funding_info || 'No funding data'} color="text-emerald-500" />
        <Row icon={Users} label="Headcount" value={signals.headcount || '–'} />
        <Row icon={TrendingUp} label="Hiring Velocity" value={velocityText} color="text-blue-400" />
        {signals.layoffs && (
          <Row icon={AlertTriangle} label="Layoffs" value={signals.layoffs} color="text-amber-500" />
        )}
        {signals.recent_news && (
          <Row icon={Newspaper} label="Recent News" value={signals.recent_news} />
        )}
        {signals.leadership_changes && signals.leadership_changes !== 'No changes' && (
          <Row icon={Users} label="Leadership" value={signals.leadership_changes} color="text-violet-400" />
        )}
      </div>

      {/* Tech Stack */}
      {signals.tech_stack?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs text-slate-500">Tech Stack</span>
          </div>
          <div className="flex flex-wrap">
            {signals.tech_stack.map((s) => <Pill key={s} text={s} />)}
          </div>
        </div>
      )}

      {/* AI Roles */}
      {signals.ai_roles?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <div className="flex items-center gap-2 mb-2">
            <Bot className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-xs text-slate-500">AI/ML Roles Open</span>
          </div>
          <div className="flex flex-wrap">
            {signals.ai_roles.map((r) => (
              <span key={r} className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-xs text-emerald-300 mr-1 mb-1">
                {r}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
