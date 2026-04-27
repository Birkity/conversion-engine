'use client';

import { Mail, MessageSquare, CalendarCheck, AlertTriangle, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import type { ConversationTurn } from '@/lib/types';
import { cn, getIntentColor, getNextStepColor, formatConfidence } from '@/lib/utils';

interface Props {
  turns: ConversationTurn[];
}

const TYPE_LABEL: Record<string, string> = {
  outbound_email: 'Outbound Email',
  clarification_email: 'Follow-up Email',
  cal_link_email: 'Booking Link Email',
};

function AgentTurnCard({ turn }: { turn: ConversationTurn }) {
  const label = TYPE_LABEL[turn.type ?? ''] ?? 'Agent Email';
  const isInitial = turn.type === 'outbound_email';

  return (
    <div className={cn(
      'rounded-xl border overflow-hidden',
      isInitial ? 'border-emerald-800/50 bg-emerald-950/20' : 'border-slate-700 bg-slate-900/60'
    )}>
      {/* Header */}
      <div className={cn(
        'flex items-center gap-2 px-4 py-2.5 border-b text-xs font-medium',
        isInitial ? 'border-emerald-800/40 text-emerald-400' : 'border-slate-700/60 text-slate-400'
      )}>
        <Mail className="w-3.5 h-3.5" />
        {label}
        {turn.sink_mode && (
          <span className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-900/40 border border-amber-700/40 text-amber-400 text-[10px]">
            sandbox → sink
          </span>
        )}
      </div>

      <div className="px-4 py-3 space-y-2">
        {turn.subject && (
          <div className="text-xs">
            <span className="text-slate-500">Subject: </span>
            <span className="text-slate-200 font-medium">{turn.subject}</span>
          </div>
        )}
        {turn.icp_segment_used && (
          <div className="text-xs">
            <span className="text-slate-500">Segment: </span>
            <span className="text-slate-400">{turn.icp_segment_used}</span>
          </div>
        )}
        {turn.body && (
          <pre className="text-xs text-slate-300 font-sans leading-relaxed whitespace-pre-wrap bg-slate-800/40 rounded-lg p-3 border border-slate-700/40 mt-2">
            {turn.body}
          </pre>
        )}
        {turn.grounding_facts && turn.grounding_facts.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-700/40">
            <div className="text-[10px] text-slate-500 mb-1.5">Grounding facts used</div>
            <ul className="space-y-1">
              {turn.grounding_facts.map((f, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs">
                  <span className="text-emerald-500 flex-shrink-0 mt-0.5">●</span>
                  <span className="text-slate-400">{f}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {turn.timestamp && (
        <div className="px-4 pb-2.5 text-[10px] text-slate-600">
          {new Date(turn.timestamp).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

function ProspectTurnCard({ turn }: { turn: ConversationTurn }) {
  const interp = turn.interpretation;
  const routing = turn.routing;
  const actions = routing?.actions ?? [];
  const errors = routing?.errors ?? [];

  const isBooked = actions.some(a => a.includes('cal_link_sent'));
  const isStopped = actions.some(a => a.includes('outreach_stopped'));

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
      {/* Prospect reply bubble */}
      <div className="px-4 py-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
          <MessageSquare className="w-3.5 h-3.5" />
          Prospect Reply
          {turn.channel && (
            <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] text-slate-400">
              {turn.channel.toUpperCase()}
            </span>
          )}
          {turn.timestamp && (
            <span className="ml-auto text-[10px] text-slate-600">
              {new Date(turn.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
        <blockquote className="text-sm text-slate-200 italic bg-slate-800/50 rounded-lg px-3 py-2 border-l-2 border-slate-600">
          "{turn.reply_text}"
        </blockquote>
      </div>

      {/* Classification */}
      {interp && (
        <div className="px-4 py-3 border-b border-slate-700/60">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-2">
            Intent Classification
          </div>
          <div className="flex flex-wrap gap-2 mb-2.5">
            <span className={cn('inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium', getIntentColor(interp.intent))}>
              {interp.intent}
            </span>
            <span className={cn('inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium', getNextStepColor(interp.next_step))}>
              {interp.next_step}
            </span>
            <span className={cn(
              'inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium',
              interp.confidence >= 0.8 ? 'bg-emerald-950/40 border-emerald-800/50 text-emerald-400'
                : interp.confidence >= 0.65 ? 'bg-amber-950/40 border-amber-800/50 text-amber-400'
                : 'bg-rose-950/40 border-rose-800/50 text-rose-400'
            )}>
              {formatConfidence(interp.confidence)}
            </span>
          </div>
          {interp.reasoning && (
            <p className="text-xs text-slate-400 leading-relaxed">{interp.reasoning}</p>
          )}
          {interp.grounding_facts_used && interp.grounding_facts_used.length > 0 && (
            <div className="mt-2 space-y-1">
              {interp.grounding_facts_used.map((f, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-slate-500">
                  <span className="text-blue-500 flex-shrink-0 mt-0.5">◆</span>
                  {f}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Routing actions */}
      {(actions.length > 0 || errors.length > 0 || routing?.cal_link) && (
        <div className="px-4 py-3">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-2">
            Routing Actions
          </div>
          <ul className="space-y-1.5">
            {actions.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <span className="text-slate-300 font-mono">{action}</span>
              </li>
            ))}
            {errors.map((err, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                <span className="text-amber-300 font-mono">{err}</span>
              </li>
            ))}
          </ul>

          {routing?.cal_link && (
            <a
              href={routing.cal_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-2.5 px-3 py-1.5 rounded-lg bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 text-xs font-medium hover:bg-emerald-900/60 transition-colors"
            >
              <CalendarCheck className="w-3.5 h-3.5" />
              Open Cal.com booking link
            </a>
          )}
        </div>
      )}

      {/* Terminal outcome */}
      {isBooked && (
        <div className="mx-4 mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-950/50 border border-emerald-700/50">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-emerald-300">Booked — meeting scheduled</span>
        </div>
      )}
      {isStopped && (
        <div className="mx-4 mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-rose-950/50 border border-rose-700/50">
          <XCircle className="w-4 h-4 text-rose-400" />
          <span className="text-xs font-semibold text-rose-300">Stopped — outreach ended</span>
        </div>
      )}

      {/* SMS status */}
      {turn.sms && (
        <div className="mx-4 mb-3 px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">SMS</div>
          <div className="flex items-center gap-3 text-xs">
            <span className={cn(
              'font-medium',
              turn.sms.delivered ? 'text-emerald-400' : turn.sms.routed_to_sink ? 'text-amber-400' : 'text-rose-400'
            )}>
              {turn.sms.delivered ? 'Delivered' : turn.sms.routed_to_sink ? 'Routed to sink' : 'Failed'}
            </span>
            {turn.sms.error && (
              <span className="text-slate-500 truncate">{turn.sms.error.slice(0, 60)}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function LiveConversationThread({ turns }: Props) {
  if (turns.length === 0) {
    return (
      <div className="text-center py-10 text-slate-600 text-sm">
        <RefreshCw className="w-6 h-6 mx-auto mb-2 opacity-30" />
        No turns yet — run the pipeline to start.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {turns.map((turn) => (
        <div key={turn.turn}>
          {turn.from === 'agent' ? (
            <AgentTurnCard turn={turn} />
          ) : (
            <ProspectTurnCard turn={turn} />
          )}
        </div>
      ))}
    </div>
  );
}
