'use client';

import { useState } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { argumentsApi, Investigation } from '@/lib/arguments-api';

interface InvestigationEditorProps {
  /** Pass an existing investigation to edit, or omit for create mode */
  investigation?: Investigation;
  /** Called after successful save with the updated/created investigation */
  onSaved: (investigation: Investigation) => void;
  onCancel: () => void;
}

/**
 * Form to create or edit an investigation.
 * Fields: title, overview_html (textarea), status.
 */
export function InvestigationEditor({ investigation, onSaved, onCancel }: InvestigationEditorProps) {
  const isEdit = !!investigation;

  const [title, setTitle] = useState(investigation?.title || '');
  const [overviewHtml, setOverviewHtml] = useState(investigation?.overview_html || '');
  const [status, setStatus] = useState(investigation?.status || 'draft');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      let result: Investigation;
      if (isEdit) {
        result = await argumentsApi.updateInvestigation(investigation!.slug, {
          title: title.trim(),
          overview_html: overviewHtml,
          status,
        });
      } else {
        result = await argumentsApi.createInvestigation({
          title: title.trim(),
          overview_html: overviewHtml,
          status,
        });
      }
      onSaved(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save investigation');
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
        <label htmlFor="inv-title" className="block text-sm font-medium text-slate-700 mb-1">
          Title <span className="text-red-400">*</span>
        </label>
        <input
          id="inv-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., Is free trade beneficial?"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          autoFocus
        />
      </div>

      {/* Overview HTML */}
      <div>
        <label htmlFor="inv-overview" className="block text-sm font-medium text-slate-700 mb-1">
          Overview HTML
        </label>
        <textarea
          id="inv-overview"
          value={overviewHtml}
          onChange={(e) => setOverviewHtml(e.target.value)}
          placeholder="<p>HTML overview content with ab-link tags...</p>"
          rows={10}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 font-mono placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
        <p className="mt-1 text-xs text-slate-400">
          Use HTML with ab-link class for definition and claim links.
        </p>
      </div>

      {/* Status */}
      <div>
        <label htmlFor="inv-status" className="block text-sm font-medium text-slate-700 mb-1">
          Status
        </label>
        <select
          id="inv-status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving && <RefreshCw className="w-4 h-4 animate-spin" />}
          {isEdit ? 'Save Changes' : 'Create Investigation'}
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
