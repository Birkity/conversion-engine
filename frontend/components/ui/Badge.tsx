import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'emerald' | 'rose' | 'amber' | 'slate' | 'blue' | 'violet' | 'cyan';
  className?: string;
}

const variants = {
  emerald: 'bg-emerald-950 text-emerald-300 border-emerald-800',
  rose: 'bg-rose-950 text-rose-300 border-rose-800',
  amber: 'bg-amber-950 text-amber-300 border-amber-800',
  slate: 'bg-slate-800 text-slate-300 border-slate-700',
  blue: 'bg-blue-950 text-blue-300 border-blue-800',
  violet: 'bg-violet-950 text-violet-300 border-violet-800',
  cyan: 'bg-cyan-950 text-cyan-300 border-cyan-800',
};

export default function Badge({ children, variant = 'slate', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
