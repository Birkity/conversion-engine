import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, User, Mail } from 'lucide-react';
import { getHiringBrief, getSignals, getCompetitorGap, getProspectInfo, getLastEmail } from '@/lib/data';
import { COMPANY_SLUGS, getSegmentColor, cn } from '@/lib/utils';
import type { CompanySlug } from '@/lib/types';
import SignalsPanel from '@/components/company/SignalsPanel';
import AIMaturityGauge from '@/components/company/AIMaturityGauge';
import HiringBriefAccordion from '@/components/company/HiringBriefAccordion';
import CompetitorGapPanel from '@/components/company/CompetitorGapPanel';
import EmailPreview from '@/components/company/EmailPreview';

export function generateStaticParams() {
  return COMPANY_SLUGS.map((slug) => ({ slug }));
}

export default async function CompanyPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  if (!COMPANY_SLUGS.includes(slug as CompanySlug)) notFound();

  const s = slug as CompanySlug;
  const [signals, brief, gap, prospect, email] = await Promise.all([
    getSignals(s),
    getHiringBrief(s),
    getCompetitorGap(s),
    getProspectInfo(s),
    getLastEmail(s),
  ]);

  const companyName = brief?.company ?? signals?.company_name ?? slug;

  return (
    <div className="p-6 space-y-5">
      {/* Breadcrumb + header */}
      <div>
        <Link href="/" className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-3 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          Dashboard
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-100">{companyName}</h1>
            {signals?.description && (
              <p className="text-sm text-slate-500 mt-1 max-w-2xl">{signals.description}</p>
            )}
          </div>
          {brief?.icp_segment && (
            <span className={cn('inline-flex items-center px-3 py-1 rounded-lg border text-sm font-medium', getSegmentColor(brief.icp_segment))}>
              {brief.icp_segment}
            </span>
          )}
        </div>

        {/* Prospect info pill */}
        {prospect && (
          <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
            <div className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" />
              <span className="text-slate-300">{prospect.name}</span>
              <span>·</span>
              <span>{prospect.role}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5" />
              <span>{prospect.email}</span>
            </div>
          </div>
        )}
      </div>

      {/* Main layout: left 60% + right 40% */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        {/* Left column */}
        <div className="lg:col-span-3 space-y-4">
          <SignalsPanel signals={signals} companyName={companyName} />
          <AIMaturityGauge
            score={brief?.ai_maturity_score ?? 0}
            rationale={brief?.ai_maturity_rationale ?? null}
          />
          <HiringBriefAccordion brief={brief} />
        </div>

        {/* Right column */}
        <div className="lg:col-span-2 space-y-4">
          <CompetitorGapPanel gap={gap} />
          <EmailPreview email={email} companyName={companyName} />
        </div>
      </div>
    </div>
  );
}
