'use client';

import { useState } from 'react';
import ConversationThread from './ConversationThread';
import type { ScenarioLog } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  logs: ScenarioLog[];
}

function getOutcomeColor(log: ScenarioLog): 'emerald' | 'rose' | 'amber' {
  const lastTurn = log.conversation[log.conversation.length - 1];
  if (lastTurn?.routing?.actions.some((a) => a.includes('outreach_stopped'))) return 'rose';
  if (lastTurn?.routing?.actions.some((a) => a.includes('cal_link_sent'))) return 'emerald';
  return 'amber';
}

const outColors = {
  emerald: 'border-emerald-700 text-emerald-400',
  rose: 'border-rose-700 text-rose-400',
  amber: 'border-amber-700 text-amber-400',
};

export default function CommunicationClient({ logs }: Props) {
  const [active, setActive] = useState(logs[0]?.scenario_id ?? '');
  const log = logs.find((l) => l.scenario_id === active);

  if (logs.length === 0) {
    return (
      <div className="p-6 text-center py-20 text-slate-500">
        No demo scenarios found. Run <code className="text-slate-400">python scripts/demo_runner.py</code> first.
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Communication Chain</h1>
        <p className="text-sm text-slate-500 mt-0.5">Multi-turn email scenarios with live reply classification</p>
      </div>

      {/* Scenario tabs */}
      <div className="flex flex-wrap gap-2">
        {logs.map((l) => {
          const isActive = l.scenario_id === active;
          const color = getOutcomeColor(l);
          return (
            <button
              key={l.scenario_id}
              onClick={() => setActive(l.scenario_id)}
              className={cn(
                'px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
                isActive
                  ? cn('bg-slate-800', outColors[color])
                  : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300 hover:bg-slate-800'
              )}
            >
              {l.scenario_id.replace(/_/g, ' ')}
            </button>
          );
        })}
      </div>

      {/* Active conversation */}
      {log && <ConversationThread log={log} />}
    </div>
  );
}
