'use client';

import { CredibilityVerdict } from '@/lib/arguments-api';

interface CredibilityBadgeProps {
  verdict: CredibilityVerdict | null | undefined;
  onOpenAssessment: () => void;
}

const verdictConfig: Record<CredibilityVerdict, { label: string; classes: string; icon: string }> = {
  trustworthy: {
    label: 'Trustworthy',
    classes: 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100',
    icon: '✅',
  },
  possible_issues: {
    label: 'Check credibility',
    classes: 'bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100',
    icon: '⚠️',
  },
  known_issues: {
    label: 'Credibility issues',
    classes: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100',
    icon: '🚫',
  },
};

/**
 * Small inline badge showing the credibility verdict for a source.
 * Clicking it opens the assessment modal.
 */
export function CredibilityBadge({ verdict, onOpenAssessment }: CredibilityBadgeProps) {
  if (!verdict) {
    return (
      <button
        onClick={(e) => { e.stopPropagation(); onOpenAssessment(); }}
        className="inline-flex items-center text-xs text-slate-400 hover:text-slate-600 transition-colors border border-dashed border-slate-200 rounded px-1.5 py-0.5 hover:border-slate-300"
        title="Rate source credibility"
      >
        Rate source
      </button>
    );
  }

  const config = verdictConfig[verdict];

  return (
    <button
      onClick={(e) => { e.stopPropagation(); onOpenAssessment(); }}
      className={`inline-flex items-center gap-1 text-xs font-medium border rounded px-1.5 py-0.5 transition-colors ${config.classes}`}
      title="Edit credibility assessment"
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </button>
  );
}
