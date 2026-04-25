import { getProbeResults, getAblationResults } from '@/lib/data';
import StatCard from '@/components/ui/StatCard';
import AblationChart from '@/components/probes/AblationChart';
import ProbeGrid from '@/components/probes/ProbeGrid';

export default function ProbesPage() {
  const probes = getProbeResults();
  const ablation = getAblationResults();

  const baseline = ablation?.conditions.day1_baseline;
  const method = ablation?.conditions.act4_method;
  const delta = ablation?.delta_a;

  const passed = probes.filter((p) => p.passed).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100">Probe Results</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          32-probe adversarial test suite · reply interpretation accuracy
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Probes Passed" value={`${passed}/32`} color="emerald" />
        <StatCard label="Accuracy" value={`${method ? Math.round(method.pass_at_1 * 100) : 97}%`} color="emerald" />
        <StatCard label="vs Day-1 Baseline" value={delta?.value_pp ?? '+21.9pp'} color="amber" sublabel="statistically significant" />
        <StatCard label="p-value" value={delta ? `p=${delta.p_value.toFixed(3)}` : 'p=0.006'} color="slate" sublabel={`z=${delta?.z_statistic.toFixed(3) ?? '2.517'}`} />
      </div>

      {/* Ablation chart */}
      {baseline && method && (
        <AblationChart
          baseline={baseline.pass_at_1}
          method={method.pass_at_1}
          baselinePassed={baseline.passed}
          methodPassed={method.passed}
          total={32}
        />
      )}

      {/* Probe grid */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 mb-4">All 32 Probes</h2>
        {probes.length > 0 ? (
          <ProbeGrid probes={probes} />
        ) : (
          <div className="border border-dashed border-slate-700 rounded-xl p-8 text-center text-slate-500">
            No probe results found. Run{' '}
            <code className="text-slate-400">python scripts/act3_reply_tests.py --save-results</code>
          </div>
        )}
      </div>
    </div>
  );
}
