'use client';

import { useState } from 'react';
import type { ChangeEvent, ElementType, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Building2, User, Mail, Briefcase, Lightbulb, ShieldCheck, AlertTriangle, Loader2 } from 'lucide-react';
import { cn, COMPANY_SLUGS, slugToDisplayName } from '@/lib/utils';

const REAL_DOMAINS = new Set([
  'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
  'icloud.com', 'protonmail.com', 'live.com',
]);

function isRealDomain(email: string) {
  const domain = email.split('@')[1]?.toLowerCase() ?? '';
  return REAL_DOMAINS.has(domain);
}

function Field({
  label,
  hint,
  icon: Icon,
  error,
  children,
}: Readonly<{
  label: string;
  hint?: string;
  icon: ElementType;
  error?: string;
  children: ReactNode;
}>) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
        <Icon className="w-3.5 h-3.5 text-slate-500" />
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-[11px] text-slate-600">{hint}</p>}
      {error && (
        <p className="flex items-center gap-1 text-[11px] text-rose-400">
          <AlertTriangle className="w-3 h-3 flex-shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}

const inputClass =
  'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-600/70 transition-colors';

const inputErrorClass =
  'w-full bg-slate-900 border border-rose-700/60 rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-rose-600 transition-colors';

export default function NewCompanyPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'seed' | 'custom'>('seed');
  const [selectedSeed, setSelectedSeed] = useState(COMPANY_SLUGS[0]);

  const [form, setForm] = useState({
    company_name: '',
    prospect_name: '',
    prospect_email: '',
    prospect_role: '',
    pitch_angle: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const set = (key: string) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setErrors((errs) => { const next = { ...errs }; delete next[key]; return next; });
  };

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!form.company_name.trim()) errs.company_name = 'Company name is required.';
    if (!form.prospect_name.trim()) errs.prospect_name = 'Prospect name is required.';
    if (!form.prospect_email.trim()) {
      errs.prospect_email = 'Email is required.';
    } else if (!form.prospect_email.includes('@')) {
      errs.prospect_email = 'Must be a valid email address.';
    } else if (isRealDomain(form.prospect_email)) {
      errs.prospect_email =
        'Must use a synthetic domain (e.g. firstname@sink.example.com) — real personal emails are not allowed.';
    }
    if (!form.prospect_role.trim()) errs.prospect_role = 'Role / title is required.';
    return errs;
  };

  const handleSubmit = async () => {
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    setSubmitting(true);
    setServerError(null);
    try {
      const res = await fetch('/api/companies/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (res.ok) {
        router.push(`/pipeline/${data.slug}`);
      } else {
        setServerError(data.error ?? 'Something went wrong.');
      }
    } catch (err) {
      setServerError(String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const emailSuggestion =
    form.prospect_name.trim()
      ? `${form.prospect_name.trim().split(' ')[0].toLowerCase()}@sink.example.com`
      : 'firstname@sink.example.com';

  const handleSeedContinue = () => {
    router.push(`/pipeline/${selectedSeed}`);
  };

  return (
    <div className="p-6 max-w-xl">
      {/* Breadcrumb */}
      <Link
        href="/pipeline"
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-5 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        All Companies
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-100">Select or Add Company</h1>
        <p className="text-sm text-slate-500 mt-1">
          Use a seeded company when available, or create a custom company entry.
        </p>
      </div>

      <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 p-1 mb-6 w-fit">
        <button
          type="button"
          onClick={() => setMode('seed')}
          className={cn(
            'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
            mode === 'seed'
              ? 'bg-emerald-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          )}
        >
          Use Seed Company
        </button>
        <button
          type="button"
          onClick={() => setMode('custom')}
          className={cn(
            'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
            mode === 'custom'
              ? 'bg-emerald-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          )}
        >
          Create Custom
        </button>
      </div>

      {mode === 'seed' ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="seed-company" className="text-xs font-medium text-slate-300">Choose a seeded company</label>
            <select
              id="seed-company"
              value={selectedSeed}
              onChange={(e) => setSelectedSeed(e.target.value)}
              className={inputClass}
            >
              {COMPANY_SLUGS.map((slug) => (
                <option key={slug} value={slug}>
                  {slugToDisplayName(slug)}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500">
              Seed companies already have required trace data, so pipeline can start immediately.
            </p>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              onClick={handleSeedContinue}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors"
            >
              <Building2 className="w-3.5 h-3.5" />
              Continue with Seed Company
            </button>

            <Link
              href="/pipeline"
              className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
            >
              Cancel
            </Link>
          </div>
        </div>
      ) : (
      <>
      {/* Policy notice */}
      <div className="flex items-start gap-2.5 bg-emerald-950/30 border border-emerald-800/40 rounded-xl px-4 py-3 mb-6">
        <ShieldCheck className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed">
          <span className="font-medium text-emerald-400">Data policy:</span> All prospect emails
          must be synthetic (e.g. <code className="text-amber-300 bg-slate-800 px-1 rounded">@sink.example.com</code>).
          Real personal addresses (Gmail, Outlook, etc.) are blocked. No live emails will
          be sent without the kill switch disabled.
        </div>
      </div>

      {/* Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">

        <Field label="Company Name" icon={Building2} error={errors.company_name}>
          <input
            type="text"
            value={form.company_name}
            onChange={set('company_name')}
            placeholder="e.g. Acme Corp"
            className={errors.company_name ? inputErrorClass : inputClass}
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Prospect Full Name" icon={User} error={errors.prospect_name}>
            <input
              type="text"
              value={form.prospect_name}
              onChange={set('prospect_name')}
              placeholder="e.g. Jordan Smith"
              className={errors.prospect_name ? inputErrorClass : inputClass}
            />
          </Field>

          <Field label="Role / Title" icon={Briefcase} error={errors.prospect_role}>
            <input
              type="text"
              value={form.prospect_role}
              onChange={set('prospect_role')}
              placeholder="e.g. Head of Data"
              className={errors.prospect_role ? inputErrorClass : inputClass}
            />
          </Field>
        </div>

        <Field
          label="Prospect Email"
          icon={Mail}
          hint={`Use a synthetic address — e.g. ${emailSuggestion}`}
          error={errors.prospect_email}
        >
          <input
            type="email"
            value={form.prospect_email}
            onChange={set('prospect_email')}
            placeholder={emailSuggestion}
            className={errors.prospect_email ? inputErrorClass : inputClass}
          />
        </Field>

        <Field
          label="Pitch Angle"
          icon={Lightbulb}
          hint="Optional — what's the hook for this prospect? Leave blank to auto-generate."
        >
          <textarea
            value={form.pitch_angle}
            onChange={set('pitch_angle')}
            placeholder="e.g. They're scaling their ML team post-Series B but hiring velocity has slowed — cost-efficient bench augmentation is the angle."
            rows={3}
            className={cn(inputClass, 'resize-none')}
          />
        </Field>

        {serverError && (
          <div className="flex items-start gap-2 text-xs text-rose-400 bg-rose-950/30 border border-rose-800/50 rounded-lg px-3 py-2.5">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            {serverError}
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-semibold transition-colors"
          >
            {submitting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Creating…
              </>
            ) : (
              <>
                <Building2 className="w-3.5 h-3.5" />
                Add Company &amp; Go to Pipeline
              </>
            )}
          </button>

          <Link
            href="/pipeline"
            className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </div>
      </>
      )}
    </div>
  );
}
