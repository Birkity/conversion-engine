import StatCard from '@/components/ui/StatCard';

interface HeroStatsProps {
  weeklySpend: number;
  costLow: number;
  costHigh: number;
  probesPassed: number;
  probesTotal: number;
  accuracy: number;
}

export default function HeroStats({
  weeklySpend,
  costLow,
  costHigh,
  probesPassed,
  probesTotal,
  accuracy,
}: HeroStatsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        label="Reply Accuracy"
        value={`${Math.round(accuracy * 100)}%`}
        sublabel="31/32 probes passed"
        color="emerald"
      />
      <StatCard
        label="Cost per Qualified Lead"
        value={`$${costLow.toFixed(2)}–$${costHigh.toFixed(2)}`}
        sublabel="vs $5.00 target ✓"
        color="emerald"
      />
      <StatCard
        label="Probe Suite"
        value={`${probesPassed}/${probesTotal}`}
        sublabel="+21.9pp vs Day-1 baseline"
        color="amber"
      />
      <StatCard
        label="Weekly LLM Spend"
        value={`$${weeklySpend.toFixed(2)}`}
        sublabel="Resend + SMS: $0.00"
        color="slate"
      />
    </div>
  );
}
