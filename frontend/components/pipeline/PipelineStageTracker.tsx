'use client';

import { Check, Clock, Loader2, CircleDot } from 'lucide-react';
import type { PipelineStatus, ConversationTurn } from '@/lib/types';
import { cn } from '@/lib/utils';

type StageState = 'complete' | 'active' | 'pending';

interface StageInfo {
  label: string;
  state: StageState;
  sub?: string;
}

function pluralize(count: number, singular: string, plural: string) {
  if (count === 1) return singular;
  return plural;
}

function getAwaitingReplyState(status: PipelineStatus, replyRound: number, started: boolean): StageState {
  if (status === 'booked' || status === 'stopped' || status === 'processing') return 'complete';
  if (status === 'waiting_for_reply') return 'active';
  if (replyRound > 0) return 'complete';
  if (started) return 'active';
  return 'pending';
}

function getAwaitingReplySub(status: PipelineStatus, replyRound: number): string | undefined {
  if (replyRound > 0) {
    const noun = pluralize(replyRound, 'reply', 'replies');
    return `${replyRound} ${noun} received`;
  }
  if (status === 'waiting_for_reply') return 'Paste reply below';
  return undefined;
}

function getOutcomeSub(status: PipelineStatus): string | undefined {
  if (status === 'booked') return 'Meeting booked';
  if (status === 'stopped') return 'Outreach stopped';
  return undefined;
}

function getLabelClass(state: StageState): string {
  if (state === 'complete') return 'text-slate-300';
  if (state === 'active') return 'text-amber-300';
  return 'text-slate-600';
}

function deriveStages(status: PipelineStatus, turns: ConversationTurn[]): StageInfo[] {
  const agentTurns = turns.filter(t => t.from === 'agent');
  const prospectTurns = turns.filter(t => t.from === 'prospect');
  const isTerminal = status === 'booked' || status === 'stopped';
  const started = status !== 'idle';

  const replyRound = prospectTurns.length;
  const agentRound = agentTurns.length;
  const emailSub = agentRound > 0
    ? `${agentRound} ${pluralize(agentRound, 'email sent', 'emails sent')}`
    : undefined;
  const awaitingReplyState = getAwaitingReplyState(status, replyRound, started);
  const awaitingReplySub = getAwaitingReplySub(status, replyRound);

  return [
    {
      label: 'Research',
      state: started ? 'complete' : 'pending',
      sub: started ? 'Brief & ICP loaded' : 'Will analyze traces on run',
    },
    {
      label: 'Email Sent',
      state: started ? 'complete' : 'pending',
      sub: emailSub,
    },
    {
      label: 'Awaiting Reply',
      state: awaitingReplyState,
      sub: awaitingReplySub,
    },
    {
      label: 'Outcome',
      state: isTerminal ? 'complete' : 'pending',
      sub: getOutcomeSub(status),
    },
  ];
}

function StageIcon({ state, isProcessing }: Readonly<{ state: StageState; isProcessing?: boolean }>) {
  if (state === 'complete') {
    return (
      <div className="w-6 h-6 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0">
        <Check className="w-3 h-3 text-white" strokeWidth={3} />
      </div>
    );
  }
  if (state === 'active') {
    if (isProcessing) {
      return (
        <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
          <Loader2 className="w-3 h-3 text-white animate-spin" />
        </div>
      );
    }
    return (
      <div className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center flex-shrink-0 ring-2 ring-amber-400/30">
        <Clock className="w-3 h-3 text-white" />
      </div>
    );
  }
  return (
    <div className="w-6 h-6 rounded-full border border-slate-700 bg-slate-900 flex items-center justify-center flex-shrink-0">
      <CircleDot className="w-3 h-3 text-slate-600" />
    </div>
  );
}

interface Props {
  status: PipelineStatus;
  turns: ConversationTurn[];
}

export default function PipelineStageTracker({ status, turns }: Readonly<Props>) {
  const stages = deriveStages(status, turns);
  const isProcessing = status === 'processing';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3.5">
      <div className="flex items-start gap-0">
        {stages.map((stage, i) => {
          const isLast = i === stages.length - 1;

          return (
            <div key={stage.label} className="flex items-start flex-1 min-w-0">
              {/* Stage node */}
              <div className="flex flex-col items-center gap-1 flex-shrink-0">
                <StageIcon
                  state={stage.state}
                  isProcessing={isProcessing && i === 2}
                />
              </div>

              {/* Connector line */}
              {!isLast && (
                <div className={cn(
                  'h-px flex-1 mt-3 mx-1.5',
                  stage.state === 'complete' ? 'bg-emerald-700/60' : 'bg-slate-700/60'
                )} />
              )}

              {/* Label (shown below icon, positioned) */}
            </div>
          );
        })}
      </div>

      {/* Labels row */}
      <div className="flex items-start gap-0 mt-1.5">
        {stages.map((stage, i) => {
          const isLast = i === stages.length - 1;
          return (
            <div key={stage.label} className="flex items-start flex-1 min-w-0">
              <div className="flex flex-col min-w-0">
                <span className={cn(
                  'text-[11px] font-medium truncate',
                  getLabelClass(stage.state)
                )}>
                  {stage.label}
                </span>
                {stage.sub && (
                  <span className="text-[10px] text-slate-500 truncate">{stage.sub}</span>
                )}
              </div>
              {!isLast && <div className="flex-1" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
