import { cn } from '@/lib/utils';

interface StatCardProps {
  label: string;
  value: string;
  sublabel?: string;
  color?: 'emerald' | 'amber' | 'rose' | 'slate' | 'blue';
  large?: boolean;
}

const colorMap = {
  emerald: 'text-emerald-400',
  amber: 'text-amber-400',
  rose: 'text-rose-400',
  slate: 'text-slate-300',
  blue: 'text-blue-400',
};

export default function StatCard({ label, value, sublabel, color = 'slate', large }: StatCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={cn('font-bold tabular-nums leading-none', large ? 'text-4xl' : 'text-3xl', colorMap[color])}>
        {value}
      </div>
      {sublabel && <div className="text-xs text-slate-500 mt-1.5">{sublabel}</div>}
    </div>
  );
}
