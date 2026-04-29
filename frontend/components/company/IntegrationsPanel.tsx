'use client';

import { useState, useEffect } from 'react';
import { ExternalLink, Copy, CheckCircle2, AlertTriangle, Loader2, User, Mail, Building2, CalendarCheck, Tag, BarChart2, Clock } from 'lucide-react';
import { cn, formatIcpSegment, getSegmentColor } from '@/lib/utils';

// ─── Types ───────────────────────────────────────────────────────

interface HubSpotData {
  found: boolean;
  contact_id?: string;
  prospect_email?: string;
  lead_status?: string;
  icp_segment?: string;
  ai_maturity_score?: string;
  enrichment_confidence?: string;
  tenacious_status?: string;
  enrichment_timestamp?: string;
  name?: string;
  company?: string;
  error?: string;
}

interface CalData {
  booking_url?: string;
  prospect_name?: string;
  prospect_email?: string;
  error?: string;
}

// ─── Lead status color map ────────────────────────────────────────

function leadStatusClass(status: string | undefined) {
  if (!status) return 'text-slate-400 bg-slate-800 border-slate-700';
  const s = status.toUpperCase();
  if (s === 'NEW') return 'text-blue-300 bg-blue-950 border-blue-800';
  if (s === 'IN_PROGRESS') return 'text-amber-300 bg-amber-950 border-amber-800';
  if (s === 'OPEN') return 'text-slate-300 bg-slate-800 border-slate-700';
  if (s === 'UNQUALIFIED') return 'text-rose-300 bg-rose-950 border-rose-800';
  if (s === 'CONNECTED') return 'text-emerald-300 bg-emerald-950 border-emerald-800';
  return 'text-slate-400 bg-slate-800 border-slate-700';
}

// ─── Small helpers ────────────────────────────────────────────────

function KV({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 border-b border-slate-800/60 last:border-0">
      <span className="text-xs text-slate-500 flex-shrink-0">{label}</span>
      <span className="text-xs text-slate-300 text-right">{children}</span>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="h-6 bg-slate-800 rounded" />
      ))}
    </div>
  );
}

// ─── HubSpot tab ─────────────────────────────────────────────────

function HubSpotTab({ slug }: { slug: string }) {
  const [data, setData] = useState<HubSpotData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/integrations/hubspot/${slug}`)
      .then((r) => r.json())
      .then((d: HubSpotData) => setData(d))
      .catch(() => setData({ found: false, error: 'Failed to reach backend.' }))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="p-4"><Skeleton /></div>;

  if (!data?.found) {
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-start gap-2 text-sm text-slate-500 bg-slate-800/50 rounded-lg p-3">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-slate-300">Not found in HubSpot</p>
            <p className="text-xs mt-0.5 text-slate-500">
              {data?.error ?? 'Run the pipeline to trigger a HubSpot contact upsert.'}
            </p>
          </div>
        </div>
        {data?.prospect_email && (
          <p className="text-xs text-slate-600">Searched for: <code className="text-slate-500">{data.prospect_email}</code></p>
        )}
      </div>
    );
  }

  const maturity = data.ai_maturity_score ? parseInt(data.ai_maturity_score) : null;
  const confidence = data.enrichment_confidence ? parseFloat(data.enrichment_confidence) : null;

  return (
    <div className="p-4 space-y-4">
      {/* Contact header */}
      <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-slate-400" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-200 truncate">{data.name || '—'}</p>
          <p className="text-xs text-slate-500 truncate">{data.prospect_email}</p>
        </div>
        {data.lead_status && (
          <span className={cn('ml-auto inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium flex-shrink-0', leadStatusClass(data.lead_status))}>
            {data.lead_status.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      {/* Enrichment fields */}
      <div className="space-y-0">
        {data.company && <KV label="Company"><Building2 className="inline w-3 h-3 mr-1 text-slate-500" />{data.company}</KV>}
        {data.icp_segment && (
          <KV label="ICP Segment">
            <span className={cn('inline-flex items-center px-1.5 py-0.5 rounded border text-xs', getSegmentColor(data.icp_segment))}>
              {formatIcpSegment(data.icp_segment)}
            </span>
          </KV>
        )}
        {maturity !== null && (
          <KV label="AI Maturity">
            <div className="flex items-center gap-1.5">
              {[0, 1, 2].map((i) => (
                <div key={i} className={cn('w-2 h-2 rounded-full', i < maturity ? 'bg-emerald-400' : 'bg-slate-700')} />
              ))}
              <span className="text-slate-400">{maturity}/3</span>
            </div>
          </KV>
        )}
        {confidence !== null && (
          <KV label="Enrichment Confidence">
            <span className={cn('font-mono', confidence >= 0.8 ? 'text-emerald-400' : confidence >= 0.6 ? 'text-amber-400' : 'text-rose-400')}>
              {Math.round(confidence * 100)}%
            </span>
          </KV>
        )}
        {data.tenacious_status && <KV label="Tenacious Status"><Tag className="inline w-3 h-3 mr-1 text-slate-500" />{data.tenacious_status}</KV>}
        {data.enrichment_timestamp && (
          <KV label="Enriched At">
            <Clock className="inline w-3 h-3 mr-1 text-slate-500" />
            {new Date(data.enrichment_timestamp).toLocaleString()}
          </KV>
        )}
      </div>

      {/* HubSpot link */}
      {data.contact_id && (
        <a
          href={`https://app.hubspot.com/contacts/contacts/${data.contact_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          Open in HubSpot
        </a>
      )}
    </div>
  );
}

// ─── Cal.com tab ──────────────────────────────────────────────────

function CalTab({ slug }: { slug: string }) {
  const [data, setData] = useState<CalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch(`/api/integrations/calendar/${slug}`)
      .then((r) => r.json())
      .then((d: CalData) => setData(d))
      .catch(() => setData({ error: 'Failed to reach backend.' }))
      .finally(() => setLoading(false));
  }, [slug]);

  const copy = () => {
    if (!data?.booking_url) return;
    navigator.clipboard.writeText(data.booking_url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) return <div className="p-4"><Skeleton /></div>;

  if (data?.error || !data?.booking_url) {
    return (
      <div className="p-4">
        <div className="flex items-start gap-2 text-sm text-slate-500 bg-slate-800/50 rounded-lg p-3">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-slate-300">Booking link unavailable</p>
            <p className="text-xs mt-0.5 text-slate-500">{data?.error ?? 'No prospect data found.'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Prospect context */}
      <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
        <CalendarCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-200">{data.prospect_name || 'Prospect'}</p>
          <p className="text-xs text-slate-500">{data.prospect_email}</p>
        </div>
      </div>

      {/* Booking URL */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-slate-400">Pre-filled booking link</p>
        <div className="flex items-stretch gap-2">
          <div className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-400 font-mono truncate">{data.booking_url}</p>
          </div>
          <button
            onClick={copy}
            className="flex-shrink-0 flex items-center gap-1 px-3 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
          >
            {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Open button */}
      <a
        href={data.booking_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors"
      >
        <CalendarCheck className="w-3.5 h-3.5" />
        Open Booking Page
        <ExternalLink className="w-3 h-3" />
      </a>

      <p className="text-[11px] text-slate-600 leading-relaxed">
        This link pre-fills the prospect's name and email. Share it directly or use it as
        the cal_link sent by the routing agent.
      </p>
    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────

type IntTab = 'hubspot' | 'cal';

interface Props {
  slug: string;
}

export default function IntegrationsPanel({ slug }: Readonly<Props>) {
  const [tab, setTab] = useState<IntTab>('hubspot');

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-slate-200">Integrations</h3>
        <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950 p-0.5">
          <button
            onClick={() => setTab('hubspot')}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors',
              tab === 'hubspot' ? 'bg-slate-800 text-slate-200' : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <BarChart2 className="w-3 h-3" />
            HubSpot
          </button>
          <button
            onClick={() => setTab('cal')}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors',
              tab === 'cal' ? 'bg-slate-800 text-slate-200' : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <CalendarCheck className="w-3 h-3" />
            Cal.com
          </button>
        </div>
      </div>

      {/* Tab content */}
      {tab === 'hubspot' ? <HubSpotTab slug={slug} /> : <CalTab slug={slug} />}
    </div>
  );
}
