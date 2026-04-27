import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, User, Mail } from 'lucide-react';
import { getHiringBrief, getProspectInfo } from '@/lib/data';
import { COMPANY_SLUGS, getSegmentColor, formatIcpSegment, cn } from '@/lib/utils';
import PipelineRunner from '@/components/pipeline/PipelineRunner';

export function generateStaticParams() {
  return COMPANY_SLUGS.map((slug) => ({ slug }));
}

export const dynamicParams = true;

export default async function PipelineSlugPage({
  params,
}: Readonly<{
  params: Promise<{ slug: string }>;
}>) {
  const { slug } = await params;

  // Load brief dynamically — works for both built-in and custom companies
  const [brief, prospect] = await Promise.all([
    getHiringBrief(slug),
    getProspectInfo(slug),
  ]);

  // 404 only if there are truly no trace files for this slug
  if (!brief && !prospect) notFound();

  const companyName = brief?.company ?? slug;
  const segment = brief?.icp_segment ?? '';
  const segmentLabel = formatIcpSegment(segment);

  return (
    <div className="p-6 space-y-5">
      {/* Breadcrumb */}
      <div>
        <Link
          href="/pipeline"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-4 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          All Companies
        </Link>

        {/* Company header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-100">{companyName}</h1>
            {brief?.recommended_pitch_angle && (
              <p className="text-sm text-slate-500 mt-1 max-w-2xl leading-relaxed">
                {brief.recommended_pitch_angle}
              </p>
            )}
          </div>
          {segmentLabel && (
            <span className={cn(
              'inline-flex items-center px-3 py-1 rounded-lg border text-sm font-medium flex-shrink-0',
              getSegmentColor(segment)
            )}>
              {segmentLabel}
            </span>
          )}
        </div>

        {/* Prospect info row */}
        {prospect && (
          <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
            <div className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-slate-600" />
              <span className="text-slate-300 font-medium">{prospect.name}</span>
              <span className="text-slate-600">·</span>
              <span>{prospect.role}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5 text-slate-600" />
              <span className="font-mono">{prospect.email}</span>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-slate-800" />

      <PipelineRunner slug={slug} companyName={companyName} />
    </div>
  );
}
