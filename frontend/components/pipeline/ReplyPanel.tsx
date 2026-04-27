'use client';

import { useState } from 'react';
import { Send, Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  prospectEmail: string;
  onSubmit: (replyText: string, channel: 'email' | 'sms') => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export default function ReplyPanel({ prospectEmail, onSubmit, isSubmitting, error }: Props) {
  const [replyText, setReplyText] = useState('');
  const [channel, setChannel] = useState<'email' | 'sms'>('email');

  const canSubmit = replyText.trim().length > 0 && !isSubmitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    await onSubmit(replyText.trim(), channel);
    setReplyText('');
  };

  const curlCmd = `curl -X POST http://localhost:8000/conversations/reply \\
  -H "Content-Type: application/json" \\
  -d '{"contact_email":"${prospectEmail}","channel":"${channel}","body":"<reply text>"}'`;

  return (
    <div className="rounded-xl border border-amber-700/40 bg-amber-950/20 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-amber-700/30 flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
        </span>
        <span className="text-sm font-semibold text-amber-300">Simulate Prospect Reply</span>
      </div>

      <div className="p-4 space-y-4">
        {/* Instructions */}
        <div className="bg-slate-900/60 rounded-lg p-3.5 space-y-2 text-xs text-slate-400">
          <p className="font-medium text-slate-300">How to continue the pipeline</p>
          <p>
            Resend is in sandbox mode — emails go to your sink inbox, not the actual prospect.
            To simulate a reply:
          </p>
          <ol className="list-decimal list-inside space-y-1 pl-1">
            <li>Open your sink inbox (<code className="text-amber-300 bg-slate-800 px-1 rounded">OUTBOUND_SINK_EMAIL</code>)</li>
            <li>Find the outbound email and decide what the prospect would say</li>
            <li>Type or paste that reply in the field below</li>
            <li>Click <strong className="text-slate-200">Process Reply</strong></li>
          </ol>
          <p>Or trigger from the terminal:</p>
          <div className="relative mt-1">
            <div className="flex items-center gap-1.5 text-slate-500 mb-1">
              <Terminal className="w-3 h-3" />
              <span className="text-[10px] font-mono">curl</span>
            </div>
            <pre className="text-[10px] font-mono bg-slate-800/80 rounded p-2 overflow-x-auto text-slate-300 leading-relaxed whitespace-pre-wrap break-all">
              {curlCmd}
            </pre>
          </div>
        </div>

        {/* Channel selector */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">Channel:</span>
          {(['email', 'sms'] as const).map((ch) => (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              className={cn(
                'px-3 py-1 rounded-md text-xs font-medium border transition-colors',
                channel === ch
                  ? 'bg-amber-900/50 border-amber-600 text-amber-200'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
              )}
            >
              {ch.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Reply textarea */}
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          placeholder="Paste the prospect's reply here…"
          rows={4}
          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-600/70 resize-none transition-colors"
        />

        {/* Error */}
        {error && (
          <p className="text-xs text-rose-400 bg-rose-950/30 border border-rose-800/50 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all',
            canSubmit
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          )}
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing…
            </span>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              Process Reply
            </>
          )}
        </button>
      </div>
    </div>
  );
}
