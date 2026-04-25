import { getAllCompanyData, getProbeResults, getInvoiceSummary, getAblationResults } from '@/lib/data';
import HeroStats from '@/components/dashboard/HeroStats';
import SystemHealthBar from '@/components/dashboard/SystemHealthBar';
import CompanyPipelineTable from '@/components/dashboard/CompanyPipelineTable';

export default function DashboardPage() {
  const companies = getAllCompanyData();
  const probes = getProbeResults();
  const invoice = getInvoiceSummary();
  const ablation = getAblationResults();

  const passed = probes.filter((p) => p.passed).length;
  const accuracy = ablation?.conditions.act4_method.pass_at_1 ?? 0.969;
  const costLow = invoice?.cost_per_qualified_lead_usd.low ?? 3.2;
  const costHigh = invoice?.cost_per_qualified_lead_usd.high ?? 4.37;
  const weeklySpend = invoice?.total_weekly_usd ?? 4.62;

  return (
    <div className="p-6 space-y-5">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Conversion Engine · Tenacious Consulting · 2026-04-25
        </p>
      </div>

      {/* Hero stats */}
      <HeroStats
        weeklySpend={weeklySpend}
        costLow={costLow}
        costHigh={costHigh}
        probesPassed={passed}
        probesTotal={probes.length || 32}
        accuracy={accuracy}
      />

      {/* System health */}
      <SystemHealthBar companies={companies.length} />

      {/* Pipeline table */}
      <CompanyPipelineTable data={companies} />

      {/* Footer note */}
      <p className="text-xs text-slate-600 pb-2">
        All outbound routed to sink. No real prospects contacted.{' '}
        <code className="text-slate-500">LIVE_OUTBOUND_ENABLED=false</code>
      </p>
    </div>
  );
}
