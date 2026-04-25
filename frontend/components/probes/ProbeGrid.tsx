'use client';

import { useState } from 'react';
import type { ProbeResult } from '@/lib/types';
import { getIntentColor, getNextStepColor, cn } from '@/lib/utils';
import { CheckCircle2, XCircle } from 'lucide-react';

interface Props {
  probes: ProbeResult[];
}

const CATEGORIES = [
  'all',
  'reply_intent_ambiguity',
  'hostile_sarcastic',
  'icp_misclassification',
  'signal_over_claim',
  'bench_over_commit',
  'tone_drift',
  'scheduling_edge_cases',
  'low_signal_honesty',
  'off_topic_identity',
  'mixed_intent_multi_question',
];

const CATEGORY_LABELS: Record<string, string> = {
  all: 'All (32)',
  reply_intent_ambiguity: 'Intent Ambiguity',
  hostile_sarcastic: 'Hostile / Sarcastic',
  icp_misclassification: 'ICP Misclassification',
  signal_over_claim: 'Signal Over-Claim',
  bench_over_commit: 'Bench Over-Commit',
  tone_drift: 'Tone Drift',
  scheduling_edge_cases: 'Scheduling',
  low_signal_honesty: 'Low Signal Honesty',
  off_topic_identity: 'Off-Topic Identity',
  mixed_intent_multi_question: 'Mixed Intent',
};

function CategoryPassRates({ probes }: { probes: ProbeResult[] }) {
  const cats = CATEGORIES.slice(1);
  return (
    <div className="flex flex-wrap gap-2">
      {cats.map((cat) => {
        const inCat = probes.filter((p) => p.category === cat);
        const passed = inCat.filter((p) => p.passed).length;
        const allPass = passed === inCat.length;
        return (
          <div
            key={cat}
            className={cn(
              'px-2.5 py-1.5 rounded-lg border text-xs',
              allPass
                ? 'bg-emerald-950/30 border-emerald-900 text-emerald-400'
                : 'bg-rose-950/30 border-rose-900 text-rose-400'
            )}
          >
            <span className="font-medium">{CATEGORY_LABELS[cat]}</span>
            <span className="ml-1.5 opacity-70">{passed}/{inCat.length}</span>
          </div>
        );
      })}
    </div>
  );
}

function ProbeCard({ probe }: { probe: ProbeResult }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={cn(
        'rounded-xl border p-4 space-y-3 transition-colors',
        probe.passed
          ? 'bg-emerald-950/10 border-emerald-900/50 hover:border-emerald-800'
          : 'bg-rose-950/20 border-rose-900/50 hover:border-rose-800'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-600 font-mono">#{probe.id}</span>
          {probe.passed ? (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500 text-slate-950 text-[10px] font-bold uppercase">
              <CheckCircle2 className="w-2.5 h-2.5" /> PASS
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-rose-500 text-white text-[10px] font-bold uppercase">
              <XCircle className="w-2.5 h-2.5" /> FAIL
            </span>
          )}
        </div>
        <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-amber-950 border border-amber-900 text-amber-400 text-[10px] font-medium">
          {CATEGORY_LABELS[probe.category] ?? probe.category}
        </span>
      </div>

      {/* Reply quote */}
      <p className="text-xs text-slate-300 italic border-l-2 border-slate-700 pl-2 leading-relaxed">
        &ldquo;{probe.reply}&rdquo;
      </p>

      {/* Intent/step comparison */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-1.5 text-xs flex-wrap">
          <span className="text-slate-600 w-16 flex-shrink-0">Expected</span>
          <span className={cn('px-1.5 py-0.5 rounded border text-[10px] font-medium', getIntentColor(probe.expected_intent))}>
            {probe.expected_intent}
          </span>
          <span className="text-slate-700">→</span>
          <span className={cn('px-1.5 py-0.5 rounded border text-[10px] font-medium', getNextStepColor(probe.expected_next_step))}>
            {probe.expected_next_step}
          </span>
        </div>
        {!probe.passed && (
          <div className="flex items-center gap-1.5 text-xs flex-wrap">
            <span className="text-slate-600 w-16 flex-shrink-0">Actual</span>
            <span className={cn('px-1.5 py-0.5 rounded border text-[10px] font-medium', getIntentColor(probe.actual_intent))}>
              {probe.actual_intent}
            </span>
            <span className="text-slate-700">→</span>
            <span className={cn('px-1.5 py-0.5 rounded border text-[10px] font-medium', getNextStepColor(probe.actual_next_step))}>
              {probe.actual_next_step}
            </span>
          </div>
        )}
      </div>

      {/* Confidence */}
      <div className="flex items-center gap-2">
        <div className="text-xs text-slate-600 w-16 flex-shrink-0">Confidence</div>
        <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full', probe.confidence >= 0.8 ? 'bg-emerald-500' : 'bg-amber-500')}
            style={{ width: `${Math.round(probe.confidence * 100)}%` }}
          />
        </div>
        <span className="text-xs text-slate-500 tabular-nums">{Math.round(probe.confidence * 100)}%</span>
      </div>

      {/* Risk (toggle) */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
      >
        {expanded ? '▲ hide risk' : '▼ show risk'}
      </button>
      {expanded && (
        <p className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-800 pt-2">
          {probe.risk_explained}
        </p>
      )}
    </div>
  );
}

export default function ProbeGrid({ probes }: Props) {
  const [activeCategory, setActiveCategory] = useState('all');

  const filtered = activeCategory === 'all' ? probes : probes.filter((p) => p.category === activeCategory);

  // Sort: failed first
  const sorted = [...filtered].sort((a, b) => (a.passed === b.passed ? a.id - b.id : a.passed ? 1 : -1));

  return (
    <div className="space-y-5">
      <CategoryPassRates probes={probes} />

      {/* Category filter */}
      <div className="flex flex-wrap gap-1.5">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={cn(
              'px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors',
              activeCategory === cat
                ? 'bg-slate-700 border-slate-600 text-slate-200'
                : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300 hover:bg-slate-800'
            )}
          >
            {cat === 'all' ? 'All' : CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
        {sorted.map((probe) => (
          <ProbeCard key={probe.id} probe={probe} />
        ))}
      </div>
    </div>
  );
}
