import type { ScenarioLog, ConversationTurn } from '@/lib/types';
import { getIntentColor, getNextStepColor, cn } from '@/lib/utils';
import { CheckCircle2, XCircle, CalendarCheck, Mail, MessageSquare, StopCircle, HelpCircle, AlertTriangle } from 'lucide-react';

interface Props {
  log: ScenarioLog;
}

function IntentBadge({ intent }: { intent: string }) {
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium', getIntentColor(intent))}>
      {intent}
    </span>
  );
}

function NextStepBadge({ step }: { step: string }) {
  const icons: Record<string, React.ElementType> = {
    SEND_CAL_LINK: CalendarCheck,
    SEND_EMAIL: Mail,
    ASK_CLARIFICATION: HelpCircle,
    STOP: StopCircle,
  };
  const Icon = icons[step] ?? HelpCircle;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium', getNextStepColor(step))}>
      <Icon className="w-3 h-3" />
      {step}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? 'bg-emerald-500' : value >= 0.65 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 tabular-nums w-8 text-right">{pct}%</span>
    </div>
  );
}

function AgentEmailCard({ turn }: { turn: ConversationTurn }) {
  return (
    <div className="flex gap-3 items-start">
      <div className="w-7 h-7 bg-emerald-950 border border-emerald-800 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
        <Mail className="w-3.5 h-3.5 text-emerald-400" />
      </div>
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="text-xs text-slate-500 mb-2">
          <span className="font-medium text-slate-400">Tenacious (outbound)</span>
          {turn.subject && <span className="ml-2">· {turn.subject}</span>}
        </div>
        <pre className="text-sm text-slate-300 font-sans leading-relaxed whitespace-pre-wrap">
          {turn.body}
        </pre>
      </div>
    </div>
  );
}

function ProspectBubble({ turn }: { turn: ConversationTurn }) {
  return (
    <div className="flex gap-3 items-start justify-end">
      <div className="max-w-[75%] bg-slate-800 border border-slate-700 rounded-xl px-4 py-3">
        <div className="text-xs text-slate-500 mb-1.5">
          <span className="font-medium text-slate-400">Prospect</span>
          <span className="ml-2">Turn {turn.turn}</span>
        </div>
        <p className="text-sm text-slate-200">{turn.reply_text}</p>
      </div>
      <div className="w-7 h-7 bg-slate-700 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
        <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
      </div>
    </div>
  );
}

function ClassificationPanel({ turn }: { turn: ConversationTurn }) {
  if (!turn.interpretation) return null;
  const { intent, next_step, confidence, reasoning, grounding_facts_used } = turn.interpretation;

  const intentOk = turn.expected_intent ? intent === turn.expected_intent : true;
  const stepOk = turn.expected_next_step ? next_step === turn.expected_next_step : true;

  return (
    <div className="mx-10 bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Reply Classification</div>

      {/* Intent + next step */}
      <div className="flex flex-wrap gap-3">
        <div className="space-y-1">
          <div className="text-xs text-slate-600">Intent</div>
          <div className="flex items-center gap-1.5">
            <IntentBadge intent={intent} />
            {turn.expected_intent && (
              intentOk
                ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                : <XCircle className="w-3.5 h-3.5 text-rose-400" />
            )}
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-xs text-slate-600">Next step</div>
          <div className="flex items-center gap-1.5">
            <NextStepBadge step={next_step} />
            {turn.expected_next_step && (
              stepOk
                ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                : <XCircle className="w-3.5 h-3.5 text-rose-400" />
            )}
          </div>
        </div>
        <div className="space-y-1 flex-1 min-w-[120px]">
          <div className="text-xs text-slate-600">Confidence</div>
          <ConfidenceBar value={confidence} />
        </div>
      </div>

      {/* Reasoning */}
      <p className="text-xs text-slate-400 leading-relaxed">{reasoning}</p>

      {/* Grounding facts */}
      {grounding_facts_used?.length > 0 && (
        <div>
          <div className="text-xs text-slate-600 mb-1">Grounding facts used</div>
          <ul className="space-y-0.5">
            {grounding_facts_used.map((f, i) => (
              <li key={i} className="text-xs text-slate-500 flex gap-1.5">
                <span className="text-emerald-600">●</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function RoutingPanel({ turn }: { turn: ConversationTurn }) {
  if (!turn.routing) return null;
  const { actions, errors, cal_link } = turn.routing;
  const hasStop = actions.some((a) => a.includes('outreach_stopped'));
  const hasCal = actions.some((a) => a.includes('cal_link_sent'));

  return (
    <div className="mx-10 bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Routing Actions</div>
      <ul className="space-y-1">
        {actions.map((a, i) => (
          <li key={i} className="flex items-center gap-1.5 text-xs">
            <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
            <span className="text-slate-400">{a}</span>
          </li>
        ))}
      </ul>
      {errors.length > 0 && (
        <ul className="space-y-1">
          {errors.map((e, i) => (
            <li key={i} className="flex items-center gap-1.5 text-xs">
              <XCircle className="w-3 h-3 text-rose-400 flex-shrink-0" />
              <span className="text-rose-400">{e}</span>
            </li>
          ))}
        </ul>
      )}
      {cal_link && (
        <div className="mt-1 p-2 bg-emerald-950/40 border border-emerald-900/50 rounded text-xs">
          <span className="text-emerald-400 font-medium">📅 Cal link: </span>
          <span className="text-emerald-500/80 break-all">{cal_link}</span>
        </div>
      )}
      {/* SMS status */}
      {turn.sms?.attempted && (
        <div className={cn('mt-1 p-2 rounded border text-xs', turn.sms.error ? 'bg-amber-950/30 border-amber-900/50' : 'bg-emerald-950/30 border-emerald-900/50')}>
          {turn.sms.error ? (
            <div className="flex items-start gap-1.5">
              <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
              <span className="text-amber-400">SMS delivery failed (sandbox) — {turn.sms.error.slice(0, 80)}…</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">SMS delivered to sink</span>
            </div>
          )}
        </div>
      )}
      {/* Terminal outcome */}
      {hasStop && (
        <div className="mt-2 py-2 px-3 bg-rose-950/40 border border-rose-900/50 rounded text-xs text-rose-400 font-medium text-center">
          ⛔ OUTREACH STOPPED — UNQUALIFIED
        </div>
      )}
      {hasCal && !hasStop && (
        <div className="mt-2 py-2 px-3 bg-emerald-950/40 border border-emerald-900/50 rounded text-xs text-emerald-400 font-medium text-center">
          ✅ BOOKING LINK SENT
        </div>
      )}
    </div>
  );
}

export default function ConversationThread({ log }: Props) {
  const lastTurn = log.conversation[log.conversation.length - 1];
  const outcome = lastTurn?.routing?.actions.some((a) => a.includes('outreach_stopped'))
    ? 'stopped'
    : lastTurn?.routing?.actions.some((a) => a.includes('cal_link_sent'))
    ? 'booked'
    : 'in_progress';

  return (
    <div className="space-y-4">
      {/* Scenario header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-200">{log.company}</div>
            <div className="text-xs text-slate-500 mt-0.5">{log.segment}</div>
            <div className="text-xs text-slate-400 mt-1">{log.description}</div>
          </div>
          <OutcomeBadge outcome={outcome} />
        </div>
      </div>

      {/* Conversation turns */}
      <div className="space-y-4">
        {log.conversation.map((turn) => (
          <div key={turn.turn} className="space-y-3">
            {turn.from === 'agent' ? (
              <AgentEmailCard turn={turn} />
            ) : (
              <>
                <ProspectBubble turn={turn} />
                <ClassificationPanel turn={turn} />
                <RoutingPanel turn={turn} />
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function OutcomeBadge({ outcome }: { outcome: 'booked' | 'stopped' | 'in_progress' }) {
  const map = {
    booked: 'text-emerald-300 bg-emerald-950 border-emerald-800',
    stopped: 'text-rose-300 bg-rose-950 border-rose-800',
    in_progress: 'text-amber-300 bg-amber-950 border-amber-800',
  };
  const labels = { booked: '✅ BOOKED', stopped: '⛔ STOPPED', in_progress: '🔄 IN PROGRESS' };
  return (
    <span className={cn('inline-flex items-center px-2.5 py-1 rounded-lg border text-xs font-semibold whitespace-nowrap', map[outcome])}>
      {labels[outcome]}
    </span>
  );
}
