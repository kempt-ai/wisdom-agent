'use client';

import { useState } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { argumentsApi, ABEvidence } from '@/lib/arguments-api';

interface EvidenceEditorProps {
  claimId: number;
  /** Pass an existing evidence to edit, or omit for create mode */
  evidence?: ABEvidence;
  onSaved: (evidence: ABEvidence) => void;
  onCancel: () => void;
}

const SOURCE_TYPES = [
  { value: '', label: 'Select type...' },
  { value: 'academic_paper', label: 'Academic Paper' },
  { value: 'news_article', label: 'News Article' },
  { value: 'think_tank', label: 'Think Tank' },
  { value: 'government_report', label: 'Government Report' },
  { value: 'book', label: 'Book' },
  { value: 'interview', label: 'Interview' },
  { value: 'dataset', label: 'Dataset' },
  { value: 'legal_document', label: 'Legal Document' },
  { value: 'opinion', label: 'Opinion' },
  { value: 'primary_source', label: 'Primary Source' },
];

/**
 * Form to add or edit evidence on a claim.
 * Fields: source_title, source_url, source_type, key_quote, key_point, kb_resource_id.
 */
export function EvidenceEditor({
  claimId,
  evidence,
  onSaved,
  onCancel,
}: EvidenceEditorProps) {
  const isEdit = !!evidence;

  const [sourceTitle, setSourceTitle] = useState(evidence?.source_title || '');
  const [sourceUrl, setSourceUrl] = useState(evidence?.source_url || '');
  const [sourceType, setSourceType] = useState(evidence?.source_type || '');
  const [keyQuote, setKeyQuote] = useState(evidence?.key_quote || '');
  const [keyPoint, setKeyPoint] = useState(evidence?.key_point || '');
  const [kbResourceId, setKbResourceId] = useState(
    evidence?.kb_resource_id ? String(evidence.kb_resource_id) : ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    setSaving(true);
    setError(null);
    try {
      const payload = {
        source_title: sourceTitle.trim() || undefined,
        source_url: sourceUrl.trim() || undefined,
        source_type: sourceType || undefined,
        key_quote: keyQuote.trim() || undefined,
        key_point: keyPoint.trim() || undefined,
        kb_resource_id: kbResourceId ? parseInt(kbResourceId, 10) : undefined,
      };

      let result: ABEvidence;
      if (isEdit) {
        result = await argumentsApi.updateEvidence(evidence!.id, payload);
      } else {
        result = await argumentsApi.createEvidence(claimId, payload);
      }
      onSaved(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save evidence');
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

      {/* Source Title */}
      <div>
        <label htmlFor="ev-title" className="block text-sm font-medium text-slate-700 mb-1">
          Source Title
        </label>
        <input
          id="ev-title"
          type="text"
          value={sourceTitle}
          onChange={(e) => setSourceTitle(e.target.value)}
          placeholder="e.g., World Bank Trade Report 2024"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          autoFocus
        />
      </div>

      {/* Source Type and URL row */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="ev-type" className="block text-sm font-medium text-slate-700 mb-1">
            Source Type
          </label>
          <select
            id="ev-type"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {SOURCE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="ev-kb" className="block text-sm font-medium text-slate-700 mb-1">
            KB Resource ID
          </label>
          <input
            id="ev-kb"
            type="number"
            value={kbResourceId}
            onChange={(e) => setKbResourceId(e.target.value)}
            placeholder="Optional"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Source URL */}
      <div>
        <label htmlFor="ev-url" className="block text-sm font-medium text-slate-700 mb-1">
          Source URL
        </label>
        <input
          id="ev-url"
          type="url"
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="https://..."
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      {/* Key Quote */}
      <div>
        <label htmlFor="ev-quote" className="block text-sm font-medium text-slate-700 mb-1">
          Key Quote
        </label>
        <textarea
          id="ev-quote"
          value={keyQuote}
          onChange={(e) => setKeyQuote(e.target.value)}
          placeholder="A direct quote from the source..."
          rows={3}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      {/* Key Point */}
      <div>
        <label htmlFor="ev-point" className="block text-sm font-medium text-slate-700 mb-1">
          Key Point
        </label>
        <textarea
          id="ev-point"
          value={keyPoint}
          onChange={(e) => setKeyPoint(e.target.value)}
          placeholder="Your summary of why this evidence matters..."
          rows={3}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving && <RefreshCw className="w-4 h-4 animate-spin" />}
          {isEdit ? 'Save Changes' : 'Add Evidence'}
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
