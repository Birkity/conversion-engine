import StatCard from '@/components/ui/StatCard';

interface HeroStatsProps {
  probesPassed: number;
  probesTotal: number;
  accuracy: number;
}

export default function HeroStats({
  probesPassed,
  probesTotal,
  accuracy,
}: HeroStatsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <StatCard
        label="Reply Accuracy"
        value={`${Math.round(accuracy * 100)}%`}
        sublabel="31/32 probes passed"
        color="emerald"
      />
      <StatCard
        label="Probe Suite"
        value={`${probesPassed}/${probesTotal}`}
        sublabel="+21.9pp vs Day-1 baseline"
        color="amber"
      />
    </div>
  );
}
