'use client';

import { useState } from 'react';
import { Counterargument, argumentsApi } from '@/lib/arguments-api';

interface CounterargumentEditorProps {
  claimId: number;
  /** Provide when editing an existing counterargument */
  existing?: Counterargument;
  onSaved: (ca: Counterargument) => void;
  onCancel: () => void;
}

/**
 * Inline form for creating or editing a counterargument.
 * counter_text is required; rebuttal_text is optional.
 */
export function CounterargumentEditor({
  claimId,
  existing,
  onSaved,
  onCancel,
}: CounterargumentEditorProps) {
  const [counterText, setCounterText] = useState(existing?.counter_text ?? '');
  const [rebuttalText, setRebuttalText] = useState(existing?.rebuttal_text ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!counterText.trim()) return;

    setSaving(true);
    setError(null);
    try {
      let saved: Counterargument;
      if (existing) {
        saved = await argumentsApi.updateCounterargument(existing.id, {
          counter_text: counterText.trim(),
          rebuttal_text: rebuttalText.trim() || undefined,
        });
      } else {
        saved = await argumentsApi.createCounterargument(claimId, {
          counter_text: counterText.trim(),
          rebuttal_text: rebuttalText.trim() || undefined,
        });
      }
      onSaved(saved);
    } catch (err: any) {
      setError(err.message || 'Failed to save counterargument');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Objection <span className="text-red-400">*</span>
        </label>
        <textarea
          value={counterText}
          onChange={(e) => setCounterText(e.target.value)}
          placeholder="State the counterargument or objection..."
          rows={3}
          className="w-full text-sm border border-slate-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
          required
          autoFocus
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Rebuttal <span className="text-slate-400">(optional)</span>
        </label>
        <textarea
          value={rebuttalText}
          onChange={(e) => setRebuttalText(e.target.value)}
          placeholder="How does this claim respond to the objection?"
          rows={3}
          className="w-full text-sm border border-slate-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
        />
      </div>

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={saving || !counterText.trim()}
          className="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving…' : existing ? 'Update' : 'Add'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-xs font-medium text-slate-500 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
