'use client';

import { useState } from 'react';
import { Shield, Pencil, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import { Counterargument, argumentsApi } from '@/lib/arguments-api';
import { CounterargumentEditor } from '@/components/arguments/CounterargumentEditor';

interface CounterargumentCardProps {
  ca: Counterargument;
  idx: number;
  total: number;
  reorderingId: number | null;
  onReorder: (caId: number, direction: 'up' | 'down', idx: number) => void;
  onUpdated: (ca: Counterargument) => void;
  onDeleted: (caId: number) => void;
}

/**
 * Displays a single counterargument with its optional rebuttal.
 * Supports inline edit, delete, and ↑↓ reorder.
 */
export function CounterargumentCard({
  ca,
  idx,
  total,
  reorderingId,
  onReorder,
  onUpdated,
  onDeleted,
}: CounterargumentCardProps) {
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!confirm('Delete this counterargument?')) return;
    setDeleting(true);
    try {
      await argumentsApi.deleteCounterargument(ca.id);
      onDeleted(ca.id);
    } catch (err) {
      console.error('Failed to delete counterargument:', err);
      setDeleting(false);
    }
  }

  if (editing) {
    return (
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-3">
        <CounterargumentEditor
          claimId={ca.claim_id}
          existing={ca}
          onSaved={(updated) => {
            onUpdated(updated);
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-3 hover:border-slate-300 transition-colors">
      {/* Objection */}
      <div className="flex items-start gap-2">
        <Shield className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <p className="text-sm text-slate-700 leading-relaxed flex-1">{ca.counter_text}</p>
        {/* Actions */}
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={() => onReorder(ca.id, 'up', idx)}
            disabled={idx === 0 || reorderingId !== null}
            className="p-0.5 text-slate-300 hover:text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Move up"
          >
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onReorder(ca.id, 'down', idx)}
            disabled={idx === total - 1 || reorderingId !== null}
            className="p-0.5 text-slate-300 hover:text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Move down"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setEditing(true)}
            className="p-0.5 text-slate-300 hover:text-indigo-500 transition-colors ml-1"
            title="Edit"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-0.5 text-slate-300 hover:text-red-500 disabled:opacity-50 transition-colors"
            title="Delete"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Rebuttal */}
      {ca.rebuttal_text && (
        <div className="mt-2 ml-6 pl-2 border-l-2 border-indigo-100">
          <p className="text-xs font-medium text-indigo-500 mb-0.5">Response</p>
          <p className="text-sm text-slate-600 leading-relaxed">{ca.rebuttal_text}</p>
        </div>
      )}
    </div>
  );
}
