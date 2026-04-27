'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Building2,
  MessageSquare,
  FlaskConical,
  Workflow,
  ChevronDown,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';

const COMPANIES = [
  { slug: 'arcana', name: 'Arcana Analytics' },
  { slug: 'brightpath', name: 'BrightPath' },
  { slug: 'coraltech', name: 'CoralTech' },
  { slug: 'kinanalytics', name: 'KinAnalytics' },
  { slug: 'novaspark', name: 'NovaSpark' },
  { slug: 'pulsesight', name: 'PulseSight' },
  { slug: 'snaptrade', name: 'SnapTrade' },
  { slug: 'streamlineops', name: 'StreamlineOps' },
  { slug: 'wiseitech', name: 'WiseiTech' },
];

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/pipeline', label: 'Run Pipeline', icon: Workflow },
  { href: '/communication', label: 'Communication', icon: MessageSquare },
  { href: '/probes', label: 'Probe Results', icon: FlaskConical },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [companiesOpen, setCompaniesOpen] = useState(true);

  const isCompanyActive = pathname.startsWith('/company/');

  return (
    <aside className="fixed top-0 left-0 h-screen w-60 bg-slate-950 border-r border-slate-800 flex flex-col overflow-hidden z-30">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-800 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-emerald-500 rounded-md flex items-center justify-center flex-shrink-0">
            <Zap className="w-4 h-4 text-slate-950" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-100 leading-tight">Conversion Engine</div>
            <div className="text-[10px] text-slate-500 leading-tight">Tenacious Consulting</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {/* Dashboard */}
        <NavLink href="/" label="Dashboard" icon={LayoutDashboard} active={pathname === '/'} />

        {/* Companies (collapsible) */}
        <div className="mt-1">
          <button
            onClick={() => setCompaniesOpen((o) => !o)}
            className={cn(
              'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-colors',
              isCompanyActive
                ? 'text-emerald-400 bg-slate-800'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            )}
          >
            <Building2 className="w-4 h-4 flex-shrink-0" />
            <span className="flex-1 text-left font-medium">Companies</span>
            {companiesOpen ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
          </button>

          {companiesOpen && (
            <div className="ml-4 mt-0.5 border-l border-slate-800 pl-2 space-y-0.5">
              {COMPANIES.map((c) => {
                const active = pathname === `/company/${c.slug}`;
                return (
                  <Link
                    key={c.slug}
                    href={`/company/${c.slug}`}
                    className={cn(
                      'block px-2 py-1.5 rounded text-xs transition-colors truncate',
                      active
                        ? 'text-emerald-400 bg-emerald-950/40'
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/40'
                    )}
                  >
                    {c.name}
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Other nav items */}
        {NAV_ITEMS.slice(1).map((item) => (
          <NavLink
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            active={item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)}
          />
        ))}
      </nav>

      {/* Status footer */}
      <div className="border-t border-slate-800 px-3 py-3 flex-shrink-0 space-y-1.5">
        <StatusDot label="Kill switch" status="active" value="ACTIVE" />
        <StatusDot label="Live outbound" status="disabled" value="DISABLED" />
        <StatusDot label="Guardrails" status="active" value="2 / 0 fired" />
      </div>
    </aside>
  );
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: React.ElementType;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm font-medium transition-colors mt-0.5',
        active
          ? 'text-emerald-400 bg-slate-800'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
      )}
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      {label}
    </Link>
  );
}

function StatusDot({
  label,
  status,
  value,
}: {
  label: string;
  status: 'active' | 'disabled' | 'warning';
  value: string;
}) {
  const dot =
    status === 'active'
      ? 'bg-emerald-500'
      : status === 'disabled'
      ? 'bg-amber-500'
      : 'bg-rose-500';

  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] text-slate-500">{label}</span>
      <div className="flex items-center gap-1">
        <div className={cn('w-1.5 h-1.5 rounded-full', dot)} />
        <span className="text-[10px] text-slate-400">{value}</span>
      </div>
    </div>
  );
}
