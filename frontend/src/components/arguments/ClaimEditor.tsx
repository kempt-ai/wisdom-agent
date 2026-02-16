'use client';

import { useState } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { argumentsApi, ABClaim } from '@/lib/arguments-api';

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
        });
      } else {
        result = await argumentsApi.createClaim(investigationSlug, {
          title: title.trim(),
          claim_text: claimText.trim(),
          exposition_html: expositionHtml || undefined,
          status,
          temporal_note: temporalNote || undefined,
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
