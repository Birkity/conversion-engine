import { getDemoLog } from '@/lib/data';
import ConversationThread from '@/components/communication/ConversationThread';
import type { ScenarioLog } from '@/lib/types';
import { cn } from '@/lib/utils';

function getOutcome(log: ScenarioLog): 'booked' | 'stopped' | 'in_progress' {
  const lastTurn = log.conversation[log.conversation.length - 1];
  if (lastTurn?.routing?.actions.some((a) => a.includes('outreach_stopped'))) return 'stopped';
  if (lastTurn?.routing?.actions.some((a) => a.includes('cal_link_sent'))) return 'booked';
  return 'in_progress';
}

const outcomeConfig = {
  booked: { label: '✅ BOOKED', color: 'text-emerald-300 bg-emerald-950 border-emerald-800' },
  stopped: { label: '⛔ STOPPED', color: 'text-rose-300 bg-rose-950 border-rose-800' },
  in_progress: { label: '🔄 IN PROGRESS', color: 'text-amber-300 bg-amber-950 border-amber-800' },
};

function ScenarioCard({ log }: { log: ScenarioLog }) {
  const outcome = getOutcome(log);
  const { label, color } = outcomeConfig[outcome];
  const turns = log.conversation.filter((t) => t.from === 'prospect').length;

  return (
    <a
      href={`#${log.scenario_id}`}
      className="block bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-colors group"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="font-mono text-xs text-slate-500">{log.scenario_id}</div>
        <span className={cn('inline-flex items-center px-2 py-0.5 rounded border text-xs font-semibold', color)}>
          {label}
        </span>
      </div>
      <div className="text-sm font-medium text-slate-200 mb-1">{log.company}</div>
      <div className="text-xs text-slate-500 mb-2">{log.segment}</div>
      <p className="text-xs text-slate-400 leading-relaxed">{log.description}</p>
      <div className="mt-3 text-xs text-slate-600">{turns} prospect turn{turns !== 1 ? 's' : ''}</div>
    </a>
  );
}

export default function ScenariosPage() {
  const logs = getDemoLog();

  if (logs.length === 0) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-bold text-slate-100 mb-4">Demo Scenarios</h1>
        <div className="border border-dashed border-slate-700 rounded-xl p-8 text-center text-slate-500">
          No scenarios found. Run{' '}
          <code className="text-slate-400">python scripts/demo_runner.py</code>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Demo Scenarios</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {logs.length} end-to-end conversation scenarios
        </p>
      </div>

      {/* 2×2 card grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {logs.map((log) => (
          <ScenarioCard key={log.scenario_id} log={log} />
        ))}
      </div>

      {/* Full conversation threads */}
      <div className="space-y-12">
        {logs.map((log) => (
          <div key={log.scenario_id} id={log.scenario_id} className="scroll-mt-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="text-xs font-mono text-slate-600 uppercase tracking-wide">
                #{logs.indexOf(log) + 1}
              </div>
              <div className="h-px flex-1 bg-slate-800" />
              <div className="text-xs text-slate-500">{log.scenario_id}</div>
            </div>
            <ConversationThread log={log} />
          </div>
        ))}
      </div>
    </div>
  );
}
