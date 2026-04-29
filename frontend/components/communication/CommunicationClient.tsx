'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { MessageSquare, Radio, CalendarCheck, XCircle, Clock, CircleDashed, Loader2, ArrowRight, RefreshCw } from 'lucide-react';
import ConversationThread from './ConversationThread';
import LiveConversationThread from '@/components/pipeline/LiveConversationThread';
import type { ScenarioLog, CompanyData, ConversationState, PipelineStatus } from '@/lib/types';
import { cn, formatIcpSegment, getSegmentColor } from '@/lib/utils';

interface Props {
  logs: ScenarioLog[];
  companies: CompanyData[];
}

// ─── Demo tab helpers ────────────────────────────────────────────

function getOutcomeColor(log: ScenarioLog): 'emerald' | 'rose' | 'amber' {
  const last = log.conversation[log.conversation.length - 1];
  if (last?.routing?.actions.some((a) => a.includes('outreach_stopped'))) return 'rose';
  if (last?.routing?.actions.some((a) => a.includes('cal_link_sent'))) return 'emerald';
  return 'amber';
}

const outcomeTab = {
  emerald: 'border-emerald-700/60 text-emerald-400',
  rose: 'border-rose-700/60 text-rose-400',
  amber: 'border-amber-700/60 text-amber-400',
};

const outcomeTabActive = {
  emerald: 'bg-emerald-950/40 border-emerald-600 text-emerald-300',
  rose: 'bg-rose-950/40 border-rose-600 text-rose-300',
  amber: 'bg-amber-950/40 border-amber-600 text-amber-300',
};

// ─── Live tab helpers ────────────────────────────────────────────

function statusDot(status: PipelineStatus) {
  if (status === 'waiting_for_reply') return (
    <span className="relative flex h-2 w-2 flex-shrink-0">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
    </span>
  );
  if (status === 'processing') return <Loader2 className="w-3 h-3 text-blue-400 animate-spin flex-shrink-0" />;
  if (status === 'booked') return <CalendarCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />;
  if (status === 'stopped') return <XCircle className="w-3 h-3 text-rose-400 flex-shrink-0" />;
  return <CircleDashed className="w-3 h-3 text-slate-600 flex-shrink-0" />;
}

function statusLabel(status: PipelineStatus, turns: number) {
  if (status === 'idle') return <span className="text-slate-600 text-[10px]">Not started</span>;
  if (status === 'waiting_for_reply') return <span className="text-amber-400 text-[10px]">Waiting · {turns}t</span>;
  if (status === 'processing') return <span className="text-blue-400 text-[10px]">Processing…</span>;
  if (status === 'booked') return <span className="text-emerald-400 text-[10px]">Booked</span>;
  return <span className="text-rose-400 text-[10px]">Stopped</span>;
}

// ─── Live conversation panel (polls when active) ─────────────────

function LivePanel({ company }: { company: CompanyData }) {
  const [state, setState] = useState<ConversationState | null>(company.conversationState);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch(`/api/conversations/${company.slug}`);
      if (res.ok) setState(await res.json());
    } catch { /* ignore */ }
  }, [company.slug]);

  useEffect(() => {
    fetch_();
  }, [fetch_]);

  useEffect(() => {
    const s = state?.status;
    if (s === 'waiting_for_reply' || s === 'processing') {
      pollRef.current = setInterval(fetch_, 4000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [state?.status, fetch_]);

  const turns = state?.turns ?? [];
  const status = state?.status ?? 'idle';
  const companyName = company.brief?.company ?? company.slug;
  const segment = company.brief?.icp_segment ?? '';

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
      {/* Company header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-100">{companyName}</h2>
          {segment && (
            <span className={cn('inline-flex items-center mt-1 px-2 py-0.5 rounded border text-xs font-medium', getSegmentColor(segment))}>
              {formatIcpSegment(segment)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {state?.last_updated && (
            <span className="text-[10px] text-slate-600">
              Updated {new Date(state.last_updated).toLocaleTimeString()}
            </span>
          )}
          <Link
            href={`/pipeline/${company.slug}`}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-400 text-xs transition-colors"
          >
            Pipeline <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Empty state */}
      {status === 'idle' && turns.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
          <CircleDashed className="w-8 h-8 text-slate-700" />
          <p className="text-sm text-slate-500">No pipeline started for this company.</p>
          <Link
            href={`/pipeline/${company.slug}`}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
          >
            Run Pipeline <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      )}

      {/* Live thread */}
      {turns.length > 0 && <LiveConversationThread turns={turns} />}
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────

type Tab = 'live' | 'demo';

export default function CommunicationClient({ logs, companies }: Props) {
  const [tab, setTab] = useState<Tab>('live');
  const [activeSlug, setActiveSlug] = useState<string>(companies[0]?.slug ?? '');
  const [activeDemoId, setActiveDemoId] = useState(logs[0]?.scenario_id ?? '');

  const liveCompanies = companies;
  const activeCompany = liveCompanies.find((c) => c.slug === activeSlug) ?? liveCompanies[0];
  const activeLog = logs.find((l) => l.scenario_id === activeDemoId);

  const activeCount = companies.filter((c) =>
    ['waiting_for_reply', 'processing'].includes(c.conversationState?.status ?? 'idle')
  ).length;

  return (
    <div className="flex flex-col h-[calc(100vh-1px)] overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-slate-500" />
          <h1 className="text-sm font-semibold text-slate-200">Communication</h1>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
          <button
            onClick={() => setTab('live')}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              tab === 'live'
                ? 'bg-slate-800 text-slate-200'
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <Radio className="w-3 h-3" />
            Live
            {activeCount > 0 && (
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-slate-950">
                {activeCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setTab('demo')}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              tab === 'demo'
                ? 'bg-slate-800 text-slate-200'
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <RefreshCw className="w-3 h-3" />
            Demo Scenarios
            <span className="text-slate-600">{logs.length}</span>
          </button>
        </div>
      </div>

      {/* Body */}
      {tab === 'live' ? (
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Company sidebar */}
          <div className="w-52 flex-shrink-0 border-r border-slate-800 overflow-y-auto">
            {liveCompanies.map((c) => {
              const status: PipelineStatus = c.conversationState?.status ?? 'idle';
              const turns = c.conversationState?.turns?.length ?? 0;
              const name = c.brief?.company ?? c.slug;
              const isActive = c.slug === activeSlug;

              return (
                <button
                  key={c.slug}
                  onClick={() => setActiveSlug(c.slug)}
                  className={cn(
                    'w-full text-left px-3 py-2.5 border-b border-slate-800/60 transition-colors',
                    isActive ? 'bg-slate-800' : 'hover:bg-slate-800/40'
                  )}
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    {statusDot(status)}
                    <span className={cn('text-xs font-medium truncate', isActive ? 'text-slate-100' : 'text-slate-400')}>
                      {name}
                    </span>
                  </div>
                  {statusLabel(status, turns)}
                </button>
              );
            })}
          </div>

          {/* Right panel */}
          {activeCompany ? (
            <LivePanel key={activeCompany.slug} company={activeCompany} />
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-600 text-sm">
              Select a company
            </div>
          )}
        </div>
      ) : (
        /* Demo tab */
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Scenario sidebar */}
          <div className="w-52 flex-shrink-0 border-r border-slate-800 overflow-y-auto py-1">
            {logs.map((l) => {
              const color = getOutcomeColor(l);
              const isActive = l.scenario_id === activeDemoId;
              return (
                <button
                  key={l.scenario_id}
                  onClick={() => setActiveDemoId(l.scenario_id)}
                  className={cn(
                    'w-full text-left px-3 py-2.5 border-b border-slate-800/60 transition-colors',
                    isActive ? 'bg-slate-800' : 'hover:bg-slate-800/40'
                  )}
                >
                  <div className="text-xs font-medium text-slate-300 truncate mb-0.5">
                    {l.company}
                  </div>
                  <div className={cn('text-[10px]', {
                    emerald: 'text-emerald-500',
                    rose: 'text-rose-500',
                    amber: 'text-amber-500',
                  }[color])}>
                    {l.segment?.split('(')[0]?.trim() ?? '—'}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Thread panel */}
          <div className="flex-1 min-h-0 overflow-y-auto p-5">
            {activeLog ? (
              <ConversationThread log={activeLog} />
            ) : (
              <div className="flex items-center justify-center h-full text-slate-600 text-sm">
                Select a scenario
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
