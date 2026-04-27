'use client';

import { CalendarCheck, CircleDashed, Clock, Loader2, XCircle } from 'lucide-react';
import type { PipelineStatus } from '@/lib/types';
import { cn } from '@/lib/utils';

const CONFIG: Record<PipelineStatus, {
  icon: React.ElementType;
  label: string;
  sub: string;
  bg: string;
  border: string;
  text: string;
  dot?: string;
}> = {
  idle: {
    icon: CircleDashed,
    label: 'Pipeline not started',
    sub: 'Select a company and click Run Pipeline to begin.',
    bg: 'bg-slate-900',
    border: 'border-slate-700',
    text: 'text-slate-400',
  },
  waiting_for_reply: {
    icon: Clock,
    label: 'Waiting for reply',
    sub: 'The outbound email was sent. Paste the prospect reply below to continue.',
    bg: 'bg-amber-950/40',
    border: 'border-amber-700/50',
    text: 'text-amber-300',
    dot: 'bg-amber-400 animate-pulse',
  },
  processing: {
    icon: Loader2,
    label: 'Processing reply…',
    sub: 'Interpreting intent and routing the response.',
    bg: 'bg-blue-950/40',
    border: 'border-blue-700/50',
    text: 'text-blue-300',
    dot: 'bg-blue-400 animate-ping',
  },
  booked: {
    icon: CalendarCheck,
    label: 'Meeting booked',
    sub: 'Cal.com booking link sent. Prospect is interested.',
    bg: 'bg-emerald-950/40',
    border: 'border-emerald-700/50',
    text: 'text-emerald-300',
    dot: 'bg-emerald-400',
  },
  stopped: {
    icon: XCircle,
    label: 'Outreach stopped',
    sub: 'Prospect is not interested. HubSpot status set to UNQUALIFIED.',
    bg: 'bg-rose-950/40',
    border: 'border-rose-700/50',
    text: 'text-rose-300',
    dot: 'bg-rose-400',
  },
};

export default function StatusBanner({ status }: { status: PipelineStatus }) {
  const c = CONFIG[status];
  const Icon = c.icon;
  const isProcessing = status === 'processing';

  return (
    <div className={cn('rounded-xl border p-4 flex items-start gap-3', c.bg, c.border)}>
      <div className="flex-shrink-0 mt-0.5">
        {c.dot ? (
          <span className="relative flex h-3 w-3 mt-1">
            {isProcessing && <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', c.dot)} />}
            <span className={cn('relative inline-flex rounded-full h-3 w-3', c.dot)} />
          </span>
        ) : (
          <Icon className={cn('w-4 h-4', c.text)} />
        )}
      </div>
      <div>
        <div className={cn('text-sm font-semibold', c.text)}>
          {isProcessing ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              {c.label}
            </span>
          ) : (
            c.label
          )}
        </div>
        <div className="text-xs text-slate-500 mt-0.5">{c.sub}</div>
      </div>
    </div>
  );
}
