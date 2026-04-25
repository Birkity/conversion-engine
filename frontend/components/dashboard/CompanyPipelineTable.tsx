import Link from 'next/link';
import { ArrowRight, CheckCircle2, Minus } from 'lucide-react';
import type { CompanyData } from '@/lib/types';
import { getSegmentColor, getVelocityInfo, cn } from '@/lib/utils';

interface Props {
  data: CompanyData[];
}

function MaturityDots({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={cn(
            'w-2.5 h-2.5 rounded-full',
            i < score
              ? score === 1
                ? 'bg-amber-400'
                : 'bg-emerald-400'
              : 'bg-slate-700'
          )}
        />
      ))}
      <span className="text-xs text-slate-400 ml-1">{score}/3</span>
    </div>
  );
}

export default function CompanyPipelineTable({ data }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-slate-800">
        <h2 className="text-sm font-semibold text-slate-200">Pipeline — 9 Companies</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800">
              {['Company', 'Industries', 'ICP Segment', 'AI Maturity', 'Hiring Velocity', 'Email', 'Prospect'].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-left text-xs text-slate-500 font-medium uppercase tracking-wide whitespace-nowrap"
                  >
                    {h}
                  </th>
                )
              )}
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {data.map((row) => {
              const name =
                row.brief?.company ??
                row.signals?.company_name ??
                row.slug;
              const industries = row.signals?.industries?.slice(0, 2).join(', ') ?? '–';
              const segment = row.brief?.icp_segment ?? '–';
              const maturity = row.brief?.ai_maturity_score ?? 0;
              const velocity = getVelocityInfo(
                row.brief?.hiring_velocity?.direction,
                row.brief?.hiring_velocity?.delta_pct ?? null
              );
              const hasEmail = !!row.email;
              const prospect = row.prospect
                ? `${row.prospect.name} / ${row.prospect.role}`
                : '–';
              const segColor = getSegmentColor(segment);

              return (
                <tr
                  key={row.slug}
                  className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors group"
                >
                  <td className="px-4 py-3 font-medium text-slate-200 whitespace-nowrap">
                    {name}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs max-w-[140px] truncate">
                    {industries}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium',
                        segColor
                      )}
                    >
                      {segment}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <MaturityDots score={maturity} />
                  </td>
                  <td className={cn('px-4 py-3 text-xs font-medium whitespace-nowrap', velocity.color)}>
                    {velocity.label}
                  </td>
                  <td className="px-4 py-3">
                    {hasEmail ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Minus className="w-4 h-4 text-amber-500/70" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap max-w-[160px] truncate">
                    {prospect}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/company/${row.slug}`}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <ArrowRight className="w-4 h-4 text-emerald-400" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
