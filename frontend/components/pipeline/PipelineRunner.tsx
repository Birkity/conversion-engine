'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, RotateCcw, MessageSquare } from 'lucide-react';
import type { ConversationState } from '@/lib/types';
import StatusBanner from './StatusBanner';
import PipelineStageTracker from './PipelineStageTracker';
import LiveConversationThread from './LiveConversationThread';
import ReplyPanel from './ReplyPanel';

interface Props {
  slug: string;
  companyName: string;
}

export default function PipelineRunner({ slug, companyName }: Props) {
  const [state, setState] = useState<ConversationState | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`/api/conversations/${slug}`);
      if (res.ok) {
        const data: ConversationState = await res.json();
        setState(data);
        return data;
      }
    } catch {
      // ignore transient fetch errors
    }
    return null;
  }, [slug]);

  useEffect(() => { fetchState(); }, [fetchState]);

  useEffect(() => {
    if (state?.status === 'processing') {
      pollRef.current = setInterval(async () => {
        const updated = await fetchState();
        if (updated && updated.status !== 'processing') {
          clearInterval(pollRef.current!);
        }
      }, 2000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [state?.status, fetchState]);

  const handleRun = async () => {
    setIsStarting(true);
    setRunError(null);
    try {
      const res = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRunError(data.error ?? 'Failed to start pipeline.');
      } else {
        setState(data);
      }
    } catch (err) {
      setRunError(String(err));
    } finally {
      setIsStarting(false);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await fetch(`/api/pipeline/reset/${slug}`, { method: 'POST' });
      await fetchState();
      setRunError(null);
      setReplyError(null);
    } finally {
      setIsResetting(false);
    }
  };

  const handleReply = async (replyText: string, channel: 'email' | 'sms') => {
    setIsSubmitting(true);
    setReplyError(null);
    const contactEmail = state?.prospect_email ?? '';
    try {
      const res = await fetch('/api/conversations/reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_email: contactEmail, channel, body: replyText }),
      });
      const data = await res.json();
      if (!res.ok) {
        setReplyError(data.error ?? 'Failed to process reply.');
      } else {
        setState(data);
      }
    } catch (err) {
      setReplyError(String(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const status = state?.status ?? 'idle';
  const turns = state?.turns ?? [];
  const isActive = status !== 'idle';
  const isTerminal = status === 'booked' || status === 'stopped';
  const isWaiting = status === 'waiting_for_reply';
  const hasTurns = turns.length > 0;

  return (
    <div className="space-y-4">
      {/* Stage tracker — always visible once pipeline context loaded */}
      <PipelineStageTracker status={status} turns={turns} />

      {/* Status banner */}
      <StatusBanner status={status} />

      {/* Run error */}
      {runError && (
        <p className="text-xs text-rose-400 bg-rose-950/30 border border-rose-800/50 rounded-lg px-3 py-2">
          {runError}
        </p>
      )}

      {/* Primary CTA: Reply panel — shown immediately when waiting (before thread) */}
      {isWaiting && state?.prospect_email && (
        <ReplyPanel
          prospectEmail={state.prospect_email}
          onSubmit={handleReply}
          isSubmitting={isSubmitting}
          error={replyError}
        />
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        {!isActive && (
          <button
            onClick={handleRun}
            disabled={isStarting}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-semibold transition-colors"
          >
            {isStarting ? (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            {isStarting ? 'Starting…' : 'Run Pipeline'}
          </button>
        )}

        {isActive && (
          <button
            onClick={handleReset}
            disabled={isResetting || status === 'processing'}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-sm font-medium transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {isResetting ? 'Resetting…' : 'Reset'}
          </button>
        )}

        {state?.started_at && (
          <span className="text-xs text-slate-600">
            Started {new Date(state.started_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Conversation thread */}
      {hasTurns && (
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 pt-1">
            <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Conversation Thread
            </h3>
            <span className="text-xs text-slate-700">
              {turns.length} turn{turns.length !== 1 ? 's' : ''}
            </span>
          </div>
          <LiveConversationThread turns={turns} />
        </div>
      )}

      {/* Terminal summary */}
      {isTerminal && (
        <div className="text-center pt-1 pb-2">
          <p className="text-xs text-slate-500">
            Pipeline complete.{' '}
            <button
              onClick={handleReset}
              className="text-slate-400 underline underline-offset-2 hover:text-slate-200 transition-colors"
            >
              Reset to run again.
            </button>
          </p>
        </div>
      )}
    </div>
  );
}
