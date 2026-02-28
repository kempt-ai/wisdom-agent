'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, AlertCircle, Database } from 'lucide-react';
import { argumentsApi, ABEvidence, SupportingQuote } from '@/lib/arguments-api';
import { knowledgeApi, CollectionSummary } from '@/lib/knowledge-api';
import { KBResourcePicker, KBSelection } from './KBResourcePicker';

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
  { value: 'magazine_article', label: 'Magazine Article' },
  { value: 'essay', label: 'Essay' },
  { value: 'think_tank', label: 'Think Tank' },
  { value: 'government_report', label: 'Government Report' },
  { value: 'book', label: 'Book' },
  { value: 'interview', label: 'Interview' },
  { value: 'blog_post', label: 'Blog Post' },
  { value: 'press_release', label: 'Press Release' },
  { value: 'transcript', label: 'Transcript' },
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
  const [sourceAnchorType, setSourceAnchorType] = useState(
    evidence?.source_anchor_type || ''
  );
  const [sourceAnchorData, setSourceAnchorData] = useState<Record<string, any> | null>(
    evidence?.source_anchor_data || null
  );
  const [supportingQuotes, setSupportingQuotes] = useState<SupportingQuote[] | null>(
    evidence?.supporting_quotes || null
  );
  const [showKBPicker, setShowKBPicker] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingStep, setSavingStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // "Add to KB" state
  const [addToKB, setAddToKB] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState('');
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(false);

  // Show "Add to KB" only when URL is set and not already linked to KB
  const showAddToKBOption = sourceUrl.trim().length > 0 && !kbResourceId;
  console.log('showAddToKBOption:', showAddToKBOption, 'sourceUrl:', sourceUrl, 'kbResourceId:', kbResourceId);

  // Load collections when user enables "Add to KB"
  useEffect(() => {
    if (addToKB && collections.length === 0) {
      setLoadingCollections(true);
      knowledgeApi.listCollections()
        .then((cols) => {
          setCollections(cols);
          if (cols.length > 0) setSelectedCollectionId(String(cols[0].id));
        })
        .catch(() => {})
        .finally(() => setLoadingCollections(false));
    }
  }, [addToKB]);

  // Auto-enable addToKB when conditions are met; reset when they're not
  useEffect(() => {
    if (showAddToKBOption) {
      setAddToKB(true);
    } else {
      setAddToKB(false);
    }
  }, [showAddToKBOption]);

  function handleKBResourceSelected(selection: KBSelection) {
    setKbResourceId(String(selection.id));
    setSourceTitle(selection.name);
    if (selection.source_url) {
      setSourceUrl(selection.source_url);
    }
    // Map KB resource_type to evidence source_type where possible
    const typeMap: Record<string, string> = {
      article: 'news_article',
      nonfiction_book: 'book',
      fiction_book: 'book',
      document: 'primary_source',
    };
    if (typeMap[selection.resource_type]) {
      setSourceType(typeMap[selection.resource_type]);
    }
    // If parsed content was selected, auto-fill key_quote
    if (selection.selectedText) {
      setKeyQuote(selection.selectedText);
    }
    // Store parse tracking data for "View in parse" feature
    if (selection.parsedResourceId && selection.outlineNodeId) {
      setSourceAnchorType('parsed_outline');
      setSourceAnchorData({
        parsed_resource_id: selection.parsedResourceId,
        outline_node_id: selection.outlineNodeId,
        outline_node_type: selection.outlineNodeType,
      });
    }
    // Store supporting quotes from parent claim children
    if (selection.supportingQuotes && selection.supportingQuotes.length > 0) {
      setSupportingQuotes(selection.supportingQuotes);
    } else {
      setSupportingQuotes(null);
    }
    setShowKBPicker(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    setSaving(true);
    setSavingStep(null);
    setError(null);
    try {
      let finalKbResourceId = kbResourceId ? parseInt(kbResourceId, 10) : undefined;

      // Step 1: Add to KB first if requested
      if (addToKB && sourceUrl.trim() && !kbResourceId && selectedCollectionId) {
        setSavingStep('Adding to Knowledge Base…');
        const kbResult = await knowledgeApi.addResourceFromUrl(parseInt(selectedCollectionId, 10), {
          url: sourceUrl.trim(),
          name: sourceTitle.trim() || undefined,
        });
        finalKbResourceId = kbResult.resource.id;
        setKbResourceId(String(finalKbResourceId));
        setSavingStep('Saving evidence…');
      }

      const payload = {
        source_title: sourceTitle.trim() || undefined,
        source_url: sourceUrl.trim() || undefined,
        source_type: sourceType || undefined,
        key_quote: keyQuote.trim() || undefined,
        key_point: keyPoint.trim() || undefined,
        kb_resource_id: finalKbResourceId,
        source_anchor_type: sourceAnchorType || undefined,
        source_anchor_data: sourceAnchorData || undefined,
        supporting_quotes: supportingQuotes || undefined,
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
      setSavingStep(null);
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
            KB Resource
          </label>
          {kbResourceId ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg flex-1 truncate">
                <Database className="w-3.5 h-3.5 shrink-0" />
                Linked (ID: {kbResourceId})
              </span>
              <button
                type="button"
                onClick={() => setKbResourceId('')}
                className="px-2 py-2 text-xs text-slate-500 hover:text-red-600 transition-colors"
                title="Unlink KB resource"
              >
                Unlink
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowKBPicker(true)}
              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm border border-dashed border-slate-300 text-slate-600 rounded-lg hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              Search Knowledge Base
            </button>
          )}
        </div>
      </div>

      {/* KB Resource Picker */}
      {showKBPicker && (
        <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
          <KBResourcePicker
            onSelect={handleKBResourceSelected}
            onCancel={() => setShowKBPicker(false)}
          />
        </div>
      )}

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

        {/* Add to KB option — only shown when URL is set and not already linked */}
        {showAddToKBOption && (
          <div className="mt-2 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={addToKB}
                onChange={(e) => setAddToKB(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-xs text-slate-700 font-medium">Also add to Knowledge Base</span>
            </label>

            {addToKB && (
              <div className="flex items-center gap-2 ml-5">
                <label className="text-xs text-slate-600 shrink-0">Collection:</label>
                {loadingCollections ? (
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Loading…
                  </span>
                ) : collections.length === 0 ? (
                  <span className="text-xs text-slate-400">No collections found</span>
                ) : (
                  <select
                    value={selectedCollectionId}
                    onChange={(e) => setSelectedCollectionId(e.target.value)}
                    className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    {collections.map((c) => (
                      <option key={c.id} value={String(c.id)}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>
        )}
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

      {/* Supporting Quotes Preview */}
      {supportingQuotes && supportingQuotes.length > 0 && (
        <div className="bg-slate-50 rounded-lg border border-slate-200 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">
              Supporting evidence ({supportingQuotes.length})
            </span>
            <button
              type="button"
              onClick={() => setSupportingQuotes(null)}
              className="text-xs text-slate-400 hover:text-red-500 transition-colors"
            >
              Clear
            </button>
          </div>
          <ul className="space-y-1.5">
            {supportingQuotes.map((sq, idx) => (
              <li key={idx} className="flex items-start gap-2 text-xs text-slate-600">
                <span className="font-medium text-slate-400 uppercase tracking-wider shrink-0 mt-0.5">
                  {sq.quote_type}
                </span>
                <span className="line-clamp-2">{sq.content}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

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
          {saving
            ? (savingStep ?? 'Saving…')
            : (isEdit ? 'Save Changes' : 'Add Evidence')}
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
