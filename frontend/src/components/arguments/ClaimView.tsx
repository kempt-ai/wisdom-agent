'use client';

import { MessageSquareQuote, Clock, FileText, Shield } from 'lucide-react';
import { ABClaim } from '@/lib/arguments-api';

interface ClaimViewProps {
  claim: ABClaim;
}

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  ongoing: { label: 'Ongoing', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  resolved: { label: 'Resolved', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  historical: { label: 'Historical', color: 'text-slate-500', bg: 'bg-slate-50 border-slate-200' },
  superseded: { label: 'Superseded', color: 'text-purple-600', bg: 'bg-purple-50 border-purple-200' },
};

/**
 * Displays a claim in the slide-out panel.
 * Shows title, claim text, exposition, status, and temporal note.
 * Evidence and counterarguments sections are placeholders for Phase 4+.
 */
export function ClaimView({ claim }: ClaimViewProps) {
  const status = statusConfig[claim.status] || statusConfig.ongoing;

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

      {/* Evidence placeholder */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-2">Evidence</h4>
        {claim.evidence.length > 0 ? (
          <div className="space-y-2">
            {claim.evidence.map((ev) => (
              <div
                key={ev.id}
                className="bg-slate-50 rounded-lg border border-slate-200 p-3"
              >
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <FileText className="w-4 h-4 text-slate-400" />
                  {ev.source_title || 'Untitled source'}
                </div>
                {ev.key_point && (
                  <p className="text-sm text-slate-500 mt-1">{ev.key_point}</p>
                )}
              </div>
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
