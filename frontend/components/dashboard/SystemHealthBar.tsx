interface Indicator {
  label: string;
  value: string;
  status: 'ok' | 'warn' | 'off';
}

const dot = (status: Indicator['status']) =>
  status === 'ok'
    ? 'bg-emerald-500'
    : status === 'warn'
    ? 'bg-amber-500'
    : 'bg-rose-500';

export default function SystemHealthBar({ companies }: { companies: number }) {
  const indicators: Indicator[] = [
    { label: 'Kill switch', value: 'ACTIVE', status: 'ok' },
    { label: 'Live outbound', value: 'DISABLED', status: 'warn' },
    { label: 'Companies enriched', value: `${companies}`, status: 'ok' },
    { label: 'Guardrails active', value: '2', status: 'ok' },
    { label: 'Guardrail firings', value: '0', status: 'ok' },
    { label: 'Sink emails', value: 'All routed', status: 'ok' },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
      <span className="text-xs text-slate-500 font-medium uppercase tracking-wide mr-2">System</span>
      {indicators.map((ind) => (
        <div key={ind.label} className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot(ind.status)}`} />
          <span className="text-xs text-slate-500">{ind.label}:</span>
          <span className="text-xs text-slate-300 font-medium">{ind.value}</span>
        </div>
      ))}
    </div>
  );
}
