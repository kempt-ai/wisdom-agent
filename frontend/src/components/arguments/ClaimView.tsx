'use client';

import { useState } from 'react';
import { MessageSquareQuote, Clock, Plus, Scale, ArrowRight, ChevronUp, ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { ABClaim, ABEvidence, Counterargument, argumentsApi } from '@/lib/arguments-api';
import { EvidenceCard } from '@/components/arguments/EvidenceCard';
import { EvidenceEditor } from '@/components/arguments/EvidenceEditor';
import { CounterargumentEditor } from '@/components/arguments/CounterargumentEditor';
import { CounterargumentCard } from '@/components/arguments/CounterargumentCard';

interface ClaimViewProps {
  claim: ABClaim;
  /** Called when evidence is added, so parent can refresh data */
  onAddEvidence?: () => void;
}

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  ongoing: { label: 'Ongoing', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  resolved: { label: 'Resolved', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  historical: { label: 'Historical', color: 'text-slate-500', bg: 'bg-slate-50 border-slate-200' },
  superseded: { label: 'Superseded', color: 'text-purple-600', bg: 'bg-purple-50 border-purple-200' },
};

/**
 * Displays a claim in the slide-out panel.
 * Shows title, claim text, exposition, status, temporal note,
 * evidence cards, and counterarguments.
 */
export function ClaimView({ claim, onAddEvidence }: ClaimViewProps) {
  const status = statusConfig[claim.status] || statusConfig.ongoing;
  const [showEvidenceEditor, setShowEvidenceEditor] = useState(false);
  const [localEvidence, setLocalEvidence] = useState<ABEvidence[]>(claim.evidence);
  const [reorderingEvidenceId, setReorderingEvidenceId] = useState<number | null>(null);
  const [showCounterargumentEditor, setShowCounterargumentEditor] = useState(false);
  const [localCounterarguments, setLocalCounterarguments] = useState<Counterargument[]>(claim.counterarguments);
  const [reorderingCaId, setReorderingCaId] = useState<number | null>(null);

  async function handleReorderCounterargument(caId: number, direction: 'up' | 'down', idx: number) {
    if (reorderingCaId !== null) return;
    setReorderingCaId(caId);
    try {
      await argumentsApi.reorderCounterargument(caId, direction);
      setLocalCounterarguments((prev) => {
        const next = [...prev];
        const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
        [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
        return next;
      });
    } catch (err) {
      console.error('Failed to reorder counterargument:', err);
    } finally {
      setReorderingCaId(null);
    }
  }

  async function handleReorderEvidence(evidenceId: number, direction: 'up' | 'down', idx: number) {
    if (reorderingEvidenceId !== null) return;
    setReorderingEvidenceId(evidenceId);
    try {
      await argumentsApi.reorderEvidence(evidenceId, direction);
      // Optimistic update: swap in local state to match server
      setLocalEvidence((prev) => {
        const next = [...prev];
        const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
        [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
        return next;
      });
    } catch (err) {
      console.error('Failed to reorder evidence:', err);
    } finally {
      setReorderingEvidenceId(null);
    }
  }

  return (
    <div>
      {/* Claim header */}
      <div className="flex items-start gap-2 mb-4">
        <MessageSquareQuote className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
        <h3 className="text-xl font-semibold text-slate-900">{claim.title}</h3>
      </div>

      {/* Status and temporal info */}
      <div className="flex items-center gap-3 mb-6">
        <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium border ${status.bg} ${status.color}`}>
          {status.label}
        </span>
        {claim.temporal_note && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5" />
            {claim.temporal_note}
          </span>
        )}
      </div>

      {/* Claim text */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">Claim</h4>
        <p className="text-slate-700 leading-relaxed">{claim.claim_text}</p>
      </div>

      {/* Exposition */}
      {claim.exposition_html && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">Exposition</h4>
          <div
            className="prose prose-slate max-w-none text-slate-700"
            dangerouslySetInnerHTML={{ __html: claim.exposition_html }}
            style={{ lineHeight: '1.7' }}
          />
        </div>
      )}

      {/* Sub-Investigation link */}
      {claim.linked_investigation && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">
            Sub-Investigation
          </h4>
          <Link
            href={`/investigations/${claim.linked_investigation.slug}`}
            className="flex items-center justify-between gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 hover:bg-indigo-100 transition-colors group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <Scale className="w-4 h-4 text-indigo-500 shrink-0" />
              <span className="text-sm font-medium text-indigo-700 truncate">
                {claim.linked_investigation.title}
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-indigo-400 shrink-0 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      )}

      {/* Evidence */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
            Evidence ({localEvidence.length})
          </h4>
          {!showEvidenceEditor && (
            <button
              onClick={() => setShowEvidenceEditor(true)}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add Evidence
            </button>
          )}
        </div>

        {/* Inline evidence editor */}
        {showEvidenceEditor && (
          <div className="mb-3 bg-slate-50 rounded-lg border border-slate-200 p-4">
            <EvidenceEditor
              claimId={claim.id}
              onSaved={(ev) => {
                setLocalEvidence((prev) => [...prev, ev]);
                setShowEvidenceEditor(false);
                onAddEvidence?.();
              }}
              onCancel={() => setShowEvidenceEditor(false)}
            />
          </div>
        )}

        {localEvidence.length > 0 ? (
          <div className="space-y-3">
            {localEvidence.map((ev, idx) => (
              <div key={ev.id} className="flex items-start gap-1">
                <div className="flex flex-col gap-0.5 pt-1 shrink-0">
                  <button
                    onClick={() => handleReorderEvidence(ev.id, 'up', idx)}
                    disabled={idx === 0 || reorderingEvidenceId !== null}
                    className="p-0.5 text-slate-300 hover:text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title="Move up"
                  >
                    <ChevronUp className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleReorderEvidence(ev.id, 'down', idx)}
                    disabled={idx === localEvidence.length - 1 || reorderingEvidenceId !== null}
                    className="p-0.5 text-slate-300 hover:text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title="Move down"
                  >
                    <ChevronDown className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="flex-1 min-w-0">
                  <EvidenceCard evidence={ev} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic">No evidence added yet.</p>
        )}
      </div>

      {/* Counterarguments & Rebuttals */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
            Counterarguments ({localCounterarguments.length})
          </h4>
          {!showCounterargumentEditor && (
            <button
              onClick={() => setShowCounterargumentEditor(true)}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add
            </button>
          )}
        </div>

        {/* Inline counterargument editor */}
        {showCounterargumentEditor && (
          <div className="mb-3 bg-slate-50 rounded-lg border border-slate-200 p-4">
            <CounterargumentEditor
              claimId={claim.id}
              onSaved={(ca) => {
                setLocalCounterarguments((prev) => [...prev, ca]);
                setShowCounterargumentEditor(false);
              }}
              onCancel={() => setShowCounterargumentEditor(false)}
            />
          </div>
        )}

        {localCounterarguments.length > 0 ? (
          <div className="space-y-2">
            {localCounterarguments.map((ca, idx) => (
              <CounterargumentCard
                key={ca.id}
                ca={ca}
                idx={idx}
                total={localCounterarguments.length}
                reorderingId={reorderingCaId}
                onReorder={handleReorderCounterargument}
                onUpdated={(updated) =>
                  setLocalCounterarguments((prev) =>
                    prev.map((c) => (c.id === updated.id ? updated : c))
                  )
                }
                onDeleted={(caId) =>
                  setLocalCounterarguments((prev) => prev.filter((c) => c.id !== caId))
                }
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic">No counterarguments yet.</p>
        )}
      </div>
    </div>
  );
}
