import Link from 'next/link';
import { ArrowRight, User, Workflow, Clock, CalendarCheck, XCircle, CircleDashed, Loader2 } from 'lucide-react';
import { getAllCompanyData } from '@/lib/data';
import { getSegmentColor, cn } from '@/lib/utils';
import type { PipelineStatus, CompanyData } from '@/lib/types';

function StatusIndicator({ status, turns }: { status: PipelineStatus; turns: number }) {
  if (status === 'idle') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-slate-500">
        <CircleDashed className="w-3 h-3" />
        Not started
      </span>
    );
  }
  if (status === 'waiting_for_reply') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-amber-400">
        <span className="relative flex h-2 w-2 flex-shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
        </span>
        Waiting for reply · turn {turns}
      </span>
    );
  }
  if (status === 'processing') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-blue-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        Processing…
      </span>
    );
  }
  if (status === 'booked') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-emerald-400">
        <CalendarCheck className="w-3 h-3" />
        Meeting booked
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1.5 text-xs text-rose-400">
      <XCircle className="w-3 h-3" />
      Stopped
    </span>
  );
}

function CompanyCard({ company, variant }: { company: CompanyData; variant: 'active' | 'ready' | 'completed' }) {
  const status: PipelineStatus = company.conversationState?.status ?? 'idle';
  const turns = company.conversationState?.turns?.length ?? 0;
  const companyName = company.brief?.company ?? company.slug;
  const segment = company.brief?.icp_segment ?? '';
  const segColor = getSegmentColor(segment);
  const pitchAngle = company.brief?.recommended_pitch_angle;

  const cardClass = {
    active: 'border-amber-700/50 bg-amber-950/10 hover:border-amber-600/70 hover:bg-amber-950/20',
    ready: 'border-slate-800 bg-slate-900 hover:border-slate-700 hover:bg-slate-800/60',
    completed: 'border-slate-800/60 bg-slate-900/50 opacity-70 hover:opacity-100 hover:border-slate-700',
  }[variant];

  const btnClass = {
    active: 'bg-amber-600 hover:bg-amber-500 text-white',
    ready: 'bg-emerald-600 hover:bg-emerald-500 text-white',
    completed: 'bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300',
  }[variant];

  const btnLabel = {
    active: 'Continue',
    ready: 'Run Pipeline',
    completed: 'View Thread',
  }[variant];

  return (
    <Link
      href={`/pipeline/${company.slug}`}
      className={cn('group block rounded-xl border transition-all p-4 space-y-3', cardClass)}
    >
      {/* Company name + segment */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-100 truncate">{companyName}</h3>
          {segment && (
            <span className={cn('inline-flex items-center mt-1 px-2 py-0.5 rounded border text-xs font-medium', segColor)}>
              {segment}
            </span>
          )}
        </div>
        <StatusIndicator status={status} turns={turns} />
      </div>

      {/* Prospect */}
      {company.prospect && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <User className="w-3 h-3 flex-shrink-0 text-slate-600" />
          <span className="text-slate-400 truncate">{company.prospect.name}</span>
          <span className="text-slate-600">·</span>
          <span className="truncate">{company.prospect.role}</span>
        </div>
      )}

      {/* Pitch angle — only for ready cards */}
      {variant === 'ready' && pitchAngle && (
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{pitchAngle}</p>
      )}

      {/* Active: show last action */}
      {variant === 'active' && turns > 0 && (
        <div className="text-xs text-slate-500 bg-slate-900/60 rounded-lg px-2.5 py-1.5 border border-slate-800">
          {turns} turn{turns !== 1 ? 's' : ''} completed — reply pending
        </div>
      )}

      {/* Completed: show outcome */}
      {variant === 'completed' && (
        <div className={cn(
          'flex items-center gap-1.5 text-xs rounded-lg px-2.5 py-1.5 border',
          status === 'booked'
            ? 'bg-emerald-950/40 border-emerald-800/50 text-emerald-400'
            : 'bg-rose-950/40 border-rose-800/50 text-rose-400'
        )}>
          {status === 'booked' ? <CalendarCheck className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
          {status === 'booked' ? 'Meeting booked' : 'Outreach stopped'} · {turns} turn{turns !== 1 ? 's' : ''}
        </div>
      )}

      {/* CTA */}
      <div className="flex justify-end pt-0.5">
        <span className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
          btnClass
        )}>
          {btnLabel}
          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
        </span>
      </div>
    </Link>
  );
}

function SectionHeader({ label, count, accent }: { label: string; count: number; accent: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className={cn('w-2 h-2 rounded-full flex-shrink-0', accent)} />
      <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">{label}</span>
      <span className="text-xs text-slate-600 font-medium tabular-nums">{count}</span>
      <div className="flex-1 h-px bg-slate-800" />
    </div>
  );
}

export default function PipelinePage() {
  const companies = getAllCompanyData();

  const active = companies.filter(c =>
    ['waiting_for_reply', 'processing'].includes(c.conversationState?.status ?? 'idle')
  );
  const ready = companies.filter(c =>
    (c.conversationState?.status ?? 'idle') === 'idle'
  );
  const completed = companies.filter(c =>
    ['booked', 'stopped'].includes(c.conversationState?.status ?? 'idle')
  );

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-slate-500 mb-1">
          <Workflow className="w-4 h-4" />
          <span className="text-xs font-medium uppercase tracking-wider">Pipeline Runner</span>
        </div>
        <h1 className="text-xl font-bold text-slate-100">Run Pipeline</h1>
        <p className="text-sm text-slate-500 mt-1">
          Select a company to start or continue the outbound email pipeline.
        </p>
      </div>

      {/* Active */}
      {active.length > 0 && (
        <div className="space-y-3">
          <SectionHeader label="Active" count={active.length} accent="bg-amber-400 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {active.map(c => <CompanyCard key={c.slug} company={c} variant="active" />)}
          </div>
        </div>
      )}

      {/* Ready to start */}
      {ready.length > 0 && (
        <div className="space-y-3">
          <SectionHeader label="Ready to Start" count={ready.length} accent="bg-emerald-500" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {ready.map(c => <CompanyCard key={c.slug} company={c} variant="ready" />)}
          </div>
        </div>
      )}

      {/* Completed */}
      {completed.length > 0 && (
        <div className="space-y-3">
          <SectionHeader label="Completed" count={completed.length} accent="bg-slate-500" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {completed.map(c => <CompanyCard key={c.slug} company={c} variant="completed" />)}
          </div>
        </div>
      )}
    </div>
  );
}
