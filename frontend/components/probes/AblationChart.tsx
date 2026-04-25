'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

interface Props {
  baseline: number;
  method: number;
  baselinePassed: number;
  methodPassed: number;
  total: number;
}

export default function AblationChart({ baseline, method, baselinePassed, methodPassed, total }: Props) {
  const data = [
    {
      name: 'Day-1 Baseline',
      'Pass Rate (%)': Math.round(baseline * 100),
      fill: '#475569',
    },
    {
      name: 'Act IV Method',
      'Pass Rate (%)': Math.round(method * 100),
      fill: '#10b981',
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-300">Guardrail Improvement</h3>
          <p className="text-xs text-slate-500 mt-0.5">Day-1 baseline vs Act IV method</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-emerald-400 tabular-nums">+21.9pp</div>
          <div className="text-xs text-slate-500">z=2.517 · p=0.006</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 40, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={{ stroke: '#1e293b' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0', fontSize: 12 }}
            itemStyle={{ color: '#94a3b8', fontSize: 12 }}
            formatter={(v) => [`${v}%`, 'Pass Rate']}
          />
          <ReferenceLine x={75} stroke="#64748b" strokeDasharray="4 4" label={{ value: '75%', position: 'top', fill: '#64748b', fontSize: 10 }} />
          <Bar dataKey="Pass Rate (%)" radius={[0, 4, 4, 0]} maxBarSize={40}>
            {data.map((entry, i) => (
              <rect key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-6 mt-3 pt-3 border-t border-slate-800">
        <StatPill label="Baseline" value={`${baselinePassed}/${total}`} color="text-slate-400" />
        <StatPill label="Act IV" value={`${methodPassed}/${total}`} color="text-emerald-400" />
        <StatPill label="95% CI" value="[+5.0pp, +38.8pp]" color="text-slate-500" />
      </div>
    </div>
  );
}

function StatPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div>
      <div className="text-xs text-slate-600">{label}</div>
      <div className={`text-sm font-semibold tabular-nums ${color}`}>{value}</div>
    </div>
  );
}
