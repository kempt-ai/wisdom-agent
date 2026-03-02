'use client';

import { useState, useEffect } from 'react';
import { X, Shield } from 'lucide-react';
import { CredibilityVerdict, CredibilityChecklist } from '@/lib/arguments-api';

// ============================================================
// Types
// ============================================================

interface CredibilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Human-readable label shown in the header (source title or URL) */
  sourceLabel?: string | null;
  /** Pre-fill state from an existing assessment */
  initialVerdict?: CredibilityVerdict | null;
  initialChecklist?: CredibilityChecklist | null;
  initialNotes?: string | null;
  /** Called on Save with the computed verdict, checklist state, and notes */
  onSave: (
    verdict: CredibilityVerdict,
    checklist: CredibilityChecklist,
    notes: string | null
  ) => Promise<void>;
}

// ============================================================
// Checklist definition
// ============================================================

const CHECKLIST_GROUPS: {
  label: string;
  items: { key: keyof CredibilityChecklist; text: string }[];
}[] = [
  {
    label: 'Who published this?',
    items: [
      {
        key: 'publisher_identified',
        text: 'I can identify the author or organization responsible for this content',
      },
      {
        key: 'publisher_credible',
        text: 'The author/organization has relevant expertise or clear accountability',
      },
    ],
  },
  {
    label: 'Is this the original source?',
    items: [
      {
        key: 'primary_or_traced',
        text: "This is a primary source, OR I've traced it back to the original claim",
      },
    ],
  },
  {
    label: 'Has this been corroborated?',
    items: [
      {
        key: 'independently_corroborated',
        text: 'At least one independent source makes the same claim',
      },
    ],
  },
  {
    label: 'Does this support the specific claim?',
    items: [
      {
        key: 'evidence_supports_claim',
        text: "The evidence actually supports the specific claim I'm using it for",
      },
      {
        key: 'no_clear_bias',
        text: 'There\u2019s no obvious financial, political, or ideological stake distorting this',
      },
    ],
  },
];

const DEFAULT_CHECKLIST: CredibilityChecklist = {
  publisher_identified: false,
  publisher_credible: false,
  no_clear_bias: false,
  primary_or_traced: false,
  independently_corroborated: false,
  evidence_supports_claim: false,
};

// ============================================================
// Verdict calculation
// ============================================================

function computeVerdict(checklist: CredibilityChecklist): CredibilityVerdict {
  const checked = Object.values(checklist).filter(Boolean).length;
  if (checked === 6) return 'trustworthy';
  if (checked >= 4) return 'possible_issues';
  return 'known_issues';
}

const verdictDisplay: Record<CredibilityVerdict, { label: string; icon: string; classes: string }> = {
  trustworthy: {
    label: 'Trustworthy Source',
    icon: '✅',
    classes: 'bg-green-50 text-green-800 border-green-200',
  },
  possible_issues: {
    label: 'Possible Credibility Issues',
    icon: '⚠️',
    classes: 'bg-yellow-50 text-yellow-800 border-yellow-200',
  },
  known_issues: {
    label: 'Known Credibility Issues',
    icon: '🚫',
    classes: 'bg-red-50 text-red-800 border-red-200',
  },
};

// ============================================================
// Component
// ============================================================

export function CredibilityModal({
  isOpen,
  onClose,
  sourceLabel,
  initialVerdict,
  initialChecklist,
  initialNotes,
  onSave,
}: CredibilityModalProps) {
  const [checklist, setChecklist] = useState<CredibilityChecklist>(
    initialChecklist ?? DEFAULT_CHECKLIST
  );
  const [notes, setNotes] = useState<string>(initialNotes ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when modal opens with new data
  useEffect(() => {
    if (isOpen) {
      setChecklist(initialChecklist ?? DEFAULT_CHECKLIST);
      setNotes(initialNotes ?? '');
      setError(null);
    }
  }, [isOpen, initialChecklist, initialNotes]);

  if (!isOpen) return null;

  const verdict = computeVerdict(checklist);
  const display = verdictDisplay[verdict];
  const checkedCount = Object.values(checklist).filter(Boolean).length;

  function toggle(key: keyof CredibilityChecklist) {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await onSave(verdict, checklist, notes.trim() || null);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save assessment');
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="credibility-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between p-5 border-b border-slate-200 shrink-0">
            <div className="flex items-start gap-2.5">
              <Shield className="w-5 h-5 text-indigo-500 shrink-0 mt-0.5" />
              <div>
                <h2 id="credibility-modal-title" className="text-base font-semibold text-slate-900">
                  Source Credibility Assessment
                </h2>
                {sourceLabel && (
                  <p className="text-xs text-slate-500 mt-0.5 truncate max-w-sm" title={sourceLabel}>
                    {sourceLabel}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-600 transition-colors rounded"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Scrollable body */}
          <div className="overflow-y-auto flex-1 p-5 space-y-5">
            {/* Checklist groups */}
            {CHECKLIST_GROUPS.map((group) => (
              <div key={group.label}>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  {group.label}
                </h3>
                <div className="space-y-2">
                  {group.items.map(({ key, text }) => (
                    <label
                      key={key}
                      className="flex items-start gap-3 cursor-pointer group"
                    >
                      <div className="mt-0.5 shrink-0">
                        <input
                          type="checkbox"
                          checked={checklist[key]}
                          onChange={() => toggle(key)}
                          className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                        />
                      </div>
                      <span className={`text-sm leading-snug transition-colors ${
                        checklist[key] ? 'text-slate-800' : 'text-slate-500'
                      } group-hover:text-slate-700`}>
                        {text}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}

            {/* Live verdict */}
            <div className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium ${display.classes}`}>
              <span>{display.icon}</span>
              <span>{display.label}</span>
              <span className="ml-auto text-xs font-normal opacity-70">
                {checkedCount}/6 criteria met
              </span>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                Why did you rate it this way? (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Reuters is a wire service with strong editorial standards"
                rows={3}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 placeholder-slate-300"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 p-4 border-t border-slate-200 shrink-0">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-50 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Save Assessment'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
