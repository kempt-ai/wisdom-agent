'use client';

import { useState } from 'react';
import { RefreshCw, AlertCircle, X } from 'lucide-react';
import { argumentsApi, Definition } from '@/lib/arguments-api';

interface DefinitionEditorProps {
  investigationSlug: string;
  /** Pass an existing definition to edit, or omit for create mode */
  definition?: Definition;
  onSaved: (definition: Definition) => void;
  onCancel: () => void;
}

/**
 * Form to create or edit a definition.
 * Fields: term, definition_html, see_also (tag input).
 */
export function DefinitionEditor({
  investigationSlug,
  definition,
  onSaved,
  onCancel,
}: DefinitionEditorProps) {
  const isEdit = !!definition;

  const [term, setTerm] = useState(definition?.term || '');
  const [definitionHtml, setDefinitionHtml] = useState(definition?.definition_html || '');
  const [seeAlso, setSeeAlso] = useState<string[]>(definition?.see_also || []);
  const [seeAlsoInput, setSeeAlsoInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addSeeAlso() {
    const val = seeAlsoInput.trim().toLowerCase().replace(/\s+/g, '-');
    if (val && !seeAlso.includes(val)) {
      setSeeAlso([...seeAlso, val]);
    }
    setSeeAlsoInput('');
  }

  function removeSeeAlso(slug: string) {
    setSeeAlso(seeAlso.filter((s) => s !== slug));
  }

  function handleSeeAlsoKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSeeAlso();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!term.trim()) {
      setError('Term is required');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      let result: Definition;
      if (isEdit) {
        result = await argumentsApi.updateDefinition(investigationSlug, definition!.slug, {
          term: term.trim(),
          definition_html: definitionHtml,
          see_also: seeAlso,
        });
      } else {
        result = await argumentsApi.createDefinition(investigationSlug, {
          term: term.trim(),
          definition_html: definitionHtml,
          see_also: seeAlso,
        });
      }
      onSaved(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save definition');
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

      {/* Term */}
      <div>
        <label htmlFor="def-term" className="block text-sm font-medium text-slate-700 mb-1">
          Term <span className="text-red-400">*</span>
        </label>
        <input
          id="def-term"
          type="text"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="e.g., Liberal"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          autoFocus
        />
      </div>

      {/* Definition HTML */}
      <div>
        <label htmlFor="def-html" className="block text-sm font-medium text-slate-700 mb-1">
          Definition HTML
        </label>
        <textarea
          id="def-html"
          value={definitionHtml}
          onChange={(e) => setDefinitionHtml(e.target.value)}
          placeholder="<p>The definition content...</p>"
          rows={6}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 font-mono placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      {/* See Also */}
      <div>
        <label htmlFor="def-see-also" className="block text-sm font-medium text-slate-700 mb-1">
          See Also
        </label>
        <div className="flex gap-2">
          <input
            id="def-see-also"
            type="text"
            value={seeAlsoInput}
            onChange={(e) => setSeeAlsoInput(e.target.value)}
            onKeyDown={handleSeeAlsoKeyDown}
            placeholder="Type a slug and press Enter"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <button
            type="button"
            onClick={addSeeAlso}
            className="px-3 py-2 text-sm font-medium text-indigo-600 border border-indigo-300 rounded-lg hover:bg-indigo-50 transition-colors"
          >
            Add
          </button>
        </div>
        {seeAlso.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {seeAlso.map((slug) => (
              <span
                key={slug}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-blue-50 text-blue-600 border border-blue-200"
              >
                {slug}
                <button
                  type="button"
                  onClick={() => removeSeeAlso(slug)}
                  className="text-blue-400 hover:text-blue-700"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
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
          {isEdit ? 'Save Changes' : 'Create Definition'}
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
