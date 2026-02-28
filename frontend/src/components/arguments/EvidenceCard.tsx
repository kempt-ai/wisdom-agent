'use client';

import { useState } from 'react';
import {
  FileText,
  ExternalLink,
  BookOpen,
  Quote,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  BarChart2,
  MessageSquare,
  GitBranch,
} from 'lucide-react';
import { ABEvidence, SupportingQuote } from '@/lib/arguments-api';

interface EvidenceCardProps {
  evidence: ABEvidence;
}

/**
 * Source type display config.
 * Maps source_type strings to human labels and badge colors.
 */
const sourceTypeConfig: Record<string, { label: string; color: string; bg: string }> = {
  'academic_paper':   { label: 'Academic Paper',   color: 'text-violet-700', bg: 'bg-violet-50 border-violet-200' },
  'news_article':     { label: 'News Article',     color: 'text-blue-700',   bg: 'bg-blue-50 border-blue-200' },
  'magazine_article': { label: 'Magazine Article', color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
  'essay':            { label: 'Essay',            color: 'text-indigo-700', bg: 'bg-indigo-50 border-indigo-200' },
  'think_tank':       { label: 'Think Tank',       color: 'text-indigo-700', bg: 'bg-indigo-50 border-indigo-200' },
  'government_report':{ label: 'Gov. Report',      color: 'text-emerald-700',bg: 'bg-emerald-50 border-emerald-200' },
  'book':             { label: 'Book',             color: 'text-amber-700',  bg: 'bg-amber-50 border-amber-200' },
  'interview':        { label: 'Interview',        color: 'text-rose-700',   bg: 'bg-rose-50 border-rose-200' },
  'blog_post':        { label: 'Blog Post',        color: 'text-cyan-700',   bg: 'bg-cyan-50 border-cyan-200' },
  'press_release':    { label: 'Press Release',    color: 'text-slate-600',  bg: 'bg-slate-100 border-slate-300' },
  'transcript':       { label: 'Transcript',       color: 'text-teal-700',   bg: 'bg-teal-50 border-teal-200' },
  'dataset':          { label: 'Dataset',          color: 'text-cyan-700',   bg: 'bg-cyan-50 border-cyan-200' },
  'legal_document':   { label: 'Legal Document',   color: 'text-slate-700',  bg: 'bg-slate-100 border-slate-300' },
  'opinion':          { label: 'Opinion',          color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
  'primary_source':   { label: 'Primary Source',   color: 'text-teal-700',   bg: 'bg-teal-50 border-teal-200' },
};

// ─── Supporting quotes sub-component ─────────────────────────────

const QUOTE_TYPE_STYLES: Record<string, { label: string; icon: typeof Quote; cls: string }> = {
  quote:     { label: 'Quote',     icon: Quote,          cls: 'text-blue-600' },
  example:   { label: 'Example',   icon: MessageSquare,  cls: 'text-purple-600' },
  data:      { label: 'Data',      icon: BarChart2,      cls: 'text-cyan-600' },
  statistic: { label: 'Statistic', icon: BarChart2,      cls: 'text-emerald-600' },
  citation:  { label: 'Citation',  icon: BookOpen,       cls: 'text-amber-600' },
  testimony: { label: 'Testimony', icon: MessageSquare,  cls: 'text-rose-600' },
};

function SupportingQuotesSection({ quotes }: { quotes: SupportingQuote[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-3 pt-3 border-t border-slate-100">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
      >
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        Supporting evidence ({quotes.length})
      </button>
      {expanded && (
        <ul className="mt-2 space-y-2">
          {quotes.map((sq, idx) => {
            const style = QUOTE_TYPE_STYLES[sq.quote_type] || QUOTE_TYPE_STYLES.example;
            const Icon = style.icon;
            return (
              <li key={idx} className="flex items-start gap-2 pl-1">
                <Icon className={`w-3 h-3 shrink-0 mt-0.5 ${style.cls}`} />
                <div>
                  <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                    {style.label}
                  </span>
                  <p className="text-xs text-slate-600 leading-relaxed">{sq.content}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────

/**
 * Displays a single evidence item with source info, type badge,
 * key quote, key point, supporting quotes, and links to source / KB resource.
 */
export function EvidenceCard({ evidence }: EvidenceCardProps) {
  const sourceType = evidence.source_type
    ? sourceTypeConfig[evidence.source_type] || {
        label: evidence.source_type.replace(/_/g, ' '),
        color: 'text-slate-600',
        bg: 'bg-slate-50 border-slate-200',
      }
    : null;

  // "View in parse" link — only when evidence was created from a parsed outline node
  const parseAnchor =
    evidence.source_anchor_type === 'parsed_outline' && evidence.source_anchor_data
      ? evidence.source_anchor_data as { parsed_resource_id: number; outline_node_id: string }
      : null;
  const viewInParseHref = parseAnchor
    ? `/arguments/outline/${parseAnchor.parsed_resource_id}?highlight=${encodeURIComponent(parseAnchor.outline_node_id)}`
    : null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 hover:border-slate-300 transition-colors">
      {/* Header: icon + title + source type badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0">
          <FileText className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span className="text-sm font-medium text-slate-800 leading-snug">
            {evidence.source_title || 'Untitled source'}
          </span>
        </div>
        {sourceType && (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border shrink-0 ${sourceType.bg} ${sourceType.color}`}
          >
            {sourceType.label}
          </span>
        )}
      </div>

      {/* Key quote */}
      {evidence.key_quote && (
        <div className="mt-3 flex gap-2">
          <Quote className="w-3.5 h-3.5 text-slate-300 shrink-0 mt-0.5" />
          <p className="text-sm text-slate-600 italic leading-relaxed">
            {evidence.key_quote}
          </p>
        </div>
      )}

      {/* Supporting quotes (expandable) */}
      {evidence.supporting_quotes && evidence.supporting_quotes.length > 0 && (
        <SupportingQuotesSection quotes={evidence.supporting_quotes} />
      )}

      {/* Key point */}
      {evidence.key_point && (
        <div className="mt-2 flex gap-2">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-sm text-slate-700 leading-relaxed">
            {evidence.key_point}
          </p>
        </div>
      )}

      {/* Action links */}
      {(evidence.source_url || evidence.kb_resource_id || viewInParseHref) && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-4">
          {evidence.source_url && (
            <a
              href={evidence.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              View source
            </a>
          )}
          {evidence.kb_resource_id && (
            <a
              href={`/knowledge/resources/${evidence.kb_resource_id}`}
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              <BookOpen className="w-3 h-3" />
              View in KB
            </a>
          )}
          {viewInParseHref && (
            <a
              href={viewInParseHref}
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              <GitBranch className="w-3 h-3" />
              View in parse
            </a>
          )}
        </div>
      )}
    </div>
  );
}
