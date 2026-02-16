'use client';

import { useState } from 'react';
import { MessageSquareQuote, Clock, Shield, Plus } from 'lucide-react';
import { ABClaim, ABEvidence } from '@/lib/arguments-api';
import { EvidenceCard } from '@/components/arguments/EvidenceCard';
import { EvidenceEditor } from '@/components/arguments/EvidenceEditor';

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
                setLocalEvidence([...localEvidence, ev]);
                setShowEvidenceEditor(false);
                onAddEvidence?.();
              }}
              onCancel={() => setShowEvidenceEditor(false)}
            />
          </div>
        )}

        {localEvidence.length > 0 ? (
          <div className="space-y-3">
            {localEvidence.map((ev) => (
              <EvidenceCard key={ev.id} evidence={ev} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic">No evidence added yet.</p>
        )}
      </div>

      {/* Counterarguments placeholder */}
      <div>
        <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">
          Counterarguments & Rebuttals
        </h4>
        {claim.counterarguments.length > 0 ? (
          <div className="space-y-2">
            {claim.counterarguments.map((ca) => (
              <div
                key={ca.id}
                className="bg-slate-50 rounded-lg border border-slate-200 p-3"
              >
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <Shield className="w-4 h-4 text-slate-400" />
                  <span className="line-clamp-2">{ca.counter_text}</span>
                </div>
                {ca.rebuttal_text && (
                  <p className="text-sm text-slate-500 mt-1 ml-6">
                    Response: {ca.rebuttal_text}
                  </p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic">No counterarguments yet.</p>
        )}
      </div>
    </div>
  );
}
