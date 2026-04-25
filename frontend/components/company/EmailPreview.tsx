import type { LastEmail } from '@/lib/types';
import { Mail, Clock, Tag } from 'lucide-react';
import { getSegmentColor, cn } from '@/lib/utils';

interface Props {
  email: LastEmail | null;
  companyName: string;
}

function highlightGrounding(body: string, facts: string[]): React.ReactNode[] {
  if (!facts || facts.length === 0) return [body];

  let remaining = body;
  const parts: React.ReactNode[] = [];
  let key = 0;

  for (const fact of facts) {
    const idx = remaining.toLowerCase().indexOf(fact.toLowerCase().slice(0, 30));
    if (idx === -1) continue;
    const matchLen = Math.min(fact.length, remaining.length - idx);
    if (idx > 0) parts.push(remaining.slice(0, idx));
    parts.push(
      <mark key={key++} className="grounding-highlight not-italic">
        {remaining.slice(idx, idx + matchLen)}
      </mark>
    );
    remaining = remaining.slice(idx + matchLen);
  }
  if (remaining) parts.push(remaining);
  return parts.length > 0 ? parts : [body];
}

export default function EmailPreview({ email, companyName }: Props) {
  if (!email) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Generated Email</h3>
        <div className="border border-dashed border-slate-700 rounded-lg p-4 text-center text-sm text-slate-500">
          No email generated for {companyName}
        </div>
      </div>
    );
  }

  const facts = email.grounding_facts ?? [];
  const bodyParts = highlightGrounding(email.body, facts);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">Generated Email</h3>

      {/* Email header */}
      <div className="bg-slate-800/50 rounded-lg p-3 mb-3 space-y-1.5 text-xs">
        <div className="flex items-start gap-2">
          <Mail className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
          <div>
            <span className="text-slate-500">To: </span>
            <span className="text-slate-300">{email.prospect_email}</span>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Tag className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
          <div>
            <span className="text-slate-500">Subject: </span>
            <span className="text-slate-200 font-medium">{email.subject}</span>
          </div>
        </div>
        {email.timestamp && (
          <div className="flex items-start gap-2">
            <Clock className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
            <span className="text-slate-500">{new Date(email.timestamp).toLocaleString()}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          {email.icp_segment_used && (
            <span className={cn('inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium', getSegmentColor(email.icp_segment_used))}>
              {email.icp_segment_used}
            </span>
          )}
          <span className="inline-flex items-center px-2 py-0.5 rounded border text-xs bg-slate-700 text-slate-400 border-slate-600">
            X-Status: draft
          </span>
        </div>
      </div>

      {/* Email body */}
      <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/50">
        <pre className="text-xs text-slate-300 font-sans leading-relaxed whitespace-pre-wrap">
          {bodyParts}
        </pre>
      </div>

      {/* Grounding facts */}
      {facts.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <div className="text-xs text-slate-500 mb-2">
            Grounding facts used ({facts.length})
          </div>
          <ul className="space-y-1">
            {facts.map((f, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs">
                <span className="text-emerald-500 flex-shrink-0 mt-0.5">●</span>
                <span className="text-slate-400">{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
