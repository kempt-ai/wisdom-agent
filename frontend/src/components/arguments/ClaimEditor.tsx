'use client';

import { useState } from 'react';
import { RefreshCw, AlertCircle, Scale, Link2, X } from 'lucide-react';
import { argumentsApi, ABClaim, InvestigationSummary } from '@/lib/arguments-api';

interface ClaimEditorProps {
  investigationSlug: string;
  /** Pass an existing claim to edit, or omit for create mode */
  claim?: ABClaim;
  onSaved: (claim: ABClaim) => void;
  onCancel: () => void;
}

/**
 * Form to create or edit a claim.
 * Fields: title, claim_text, exposition_html, status, temporal_note.
 */
export function ClaimEditor({
  investigationSlug,
  claim,
  onSaved,
  onCancel,
}: ClaimEditorProps) {
  const isEdit = !!claim;

  const [title, setTitle] = useState(claim?.title || '');
  const [claimText, setClaimText] = useState(claim?.claim_text || '');
  const [expositionHtml, setExpositionHtml] = useState(claim?.exposition_html || '');
  const [status, setStatus] = useState(claim?.status || 'ongoing');
  const [temporalNote, setTemporalNote] = useState(claim?.temporal_note || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Linked sub-investigation state
  const [linkedInvId, setLinkedInvId] = useState<number | null>(claim?.linked_investigation_id ?? null);
  const [linkedInvTitle, setLinkedInvTitle] = useState<string>(claim?.linked_investigation?.title ?? '');
  const [showInvPicker, setShowInvPicker] = useState(false);
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [loadingInvs, setLoadingInvs] = useState(false);

  async function handleOpenInvPicker() {
    setShowInvPicker(true);
    if (investigations.length === 0) {
      setLoadingInvs(true);
      try {
        const all = await argumentsApi.listInvestigations();
        // Filter out the current investigation so a claim can't link to its own parent
        setInvestigations(all.filter((inv) => inv.slug !== investigationSlug));
      } finally {
        setLoadingInvs(false);
      }
    }
  }

  function handleSelectInvestigation(inv: InvestigationSummary) {
    setLinkedInvId(inv.id);
    setLinkedInvTitle(inv.title);
    setShowInvPicker(false);
  }

  function handleUnlinkInvestigation() {
    setLinkedInvId(null);
    setLinkedInvTitle('');
    setShowInvPicker(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!claimText.trim()) {
      setError('Claim text is required');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      let result: ABClaim;
      if (isEdit) {
        result = await argumentsApi.updateClaim(investigationSlug, claim!.slug, {
          title: title.trim(),
          claim_text: claimText.trim(),
          exposition_html: expositionHtml || undefined,
          status,
          temporal_note: temporalNote || undefined,
          linked_investigation_id: linkedInvId,
        });
      } else {
        result = await argumentsApi.createClaim(investigationSlug, {
          title: title.trim(),
          claim_text: claimText.trim(),
          exposition_html: expositionHtml || undefined,
          status,
          temporal_note: temporalNote || undefined,
          linked_investigation_id: linkedInvId,
        });
      }
      onSaved(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save claim');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Title */}
      <div>
        <label htmlFor="claim-title" className="block text-sm font-medium text-slate-700 mb-1">
          Title <span className="text-red-400">*</span>
        </label>
        <input
          id="claim-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., Free trade increases GDP"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          autoFocus
        />
      </div>

      {/* Claim Text */}
      <div>
        <label htmlFor="claim-text" className="block text-sm font-medium text-slate-700 mb-1">
          Claim Text <span className="text-red-400">*</span>
        </label>
        <textarea
          id="claim-text"
          value={claimText}
          onChange={(e) => setClaimText(e.target.value)}
          placeholder="The core assertion being made..."
          rows={4}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      {/* Exposition HTML */}
      <div>
        <label htmlFor="claim-exposition" className="block text-sm font-medium text-slate-700 mb-1">
          Exposition HTML
        </label>
        <textarea
          id="claim-exposition"
          value={expositionHtml}
          onChange={(e) => setExpositionHtml(e.target.value)}
          placeholder="<p>Detailed explanation of the claim...</p>"
          rows={6}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 font-mono placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      {/* Status and Temporal Note row */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="claim-status" className="block text-sm font-medium text-slate-700 mb-1">
            Status
          </label>
          <select
            id="claim-status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="ongoing">Ongoing</option>
            <option value="resolved">Resolved</option>
            <option value="historical">Historical</option>
            <option value="superseded">Superseded</option>
          </select>
        </div>
        <div>
          <label htmlFor="claim-temporal" className="block text-sm font-medium text-slate-700 mb-1">
            Temporal Note
          </label>
          <input
            id="claim-temporal"
            type="text"
            value={temporalNote}
            onChange={(e) => setTemporalNote(e.target.value)}
            placeholder="e.g., As of 2024"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Linked Sub-Investigation */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Linked Sub-Investigation
        </label>
        {linkedInvId ? (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg flex-1 truncate">
              <Scale className="w-3.5 h-3.5 shrink-0" />
              {linkedInvTitle}
            </span>
            <button
              type="button"
              onClick={handleUnlinkInvestigation}
              className="p-2 text-slate-400 hover:text-red-500 transition-colors"
              title="Unlink investigation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={handleOpenInvPicker}
            className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm border border-dashed border-slate-300 text-slate-600 rounded-lg hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Link2 className="w-3.5 h-3.5" />
            Link to Sub-Investigation
          </button>
        )}

        {/* Investigation picker dropdown */}
        {showInvPicker && (
          <div className="mt-2 bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
            {loadingInvs ? (
              <div className="flex items-center gap-2 px-3 py-3 text-sm text-slate-500">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Loading investigations…
              </div>
            ) : investigations.length === 0 ? (
              <p className="px-3 py-3 text-sm text-slate-400 italic">No other investigations found.</p>
            ) : (
              <ul className="max-h-48 overflow-y-auto divide-y divide-slate-100">
                {investigations.map((inv) => (
                  <li key={inv.id}>
                    <button
                      type="button"
                      onClick={() => handleSelectInvestigation(inv)}
                      className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-indigo-50 transition-colors"
                    >
                      <Scale className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      <span className="text-sm text-slate-700 truncate">{inv.title}</span>
                      <span className="ml-auto text-xs text-slate-400 shrink-0">{inv.claim_count} claims</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="border-t border-slate-100 px-3 py-2">
              <button
                type="button"
                onClick={() => setShowInvPicker(false)}
                className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving && <RefreshCw className="w-4 h-4 animate-spin" />}
          {isEdit ? 'Save Changes' : 'Create Claim'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
