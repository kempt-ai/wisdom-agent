'use client';

import { BookOpen } from 'lucide-react';
import { Definition } from '@/lib/arguments-api';

interface DefinitionViewProps {
  definition: Definition;
  onSeeAlsoClick?: (slug: string) => void;
}

/**
 * Displays a definition in the slide-out panel.
 * Shows the term, definition HTML, and "see also" links.
 */
export function DefinitionView({ definition, onSeeAlsoClick }: DefinitionViewProps) {
  return (
    <div>
      {/* Term header */}
      <div className="flex items-center gap-2 mb-4">
        <BookOpen className="w-5 h-5 text-blue-500 shrink-0" />
        <h3 className="text-xl font-semibold text-slate-900">{definition.term}</h3>
      </div>

      {/* Definition content */}
      <div
        className="prose prose-slate max-w-none text-slate-700"
        dangerouslySetInnerHTML={{ __html: definition.definition_html }}
        style={{ lineHeight: '1.7' }}
      />

      {/* See also links */}
      {definition.see_also && definition.see_also.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-200">
          <h4 className="text-sm font-medium text-slate-500 mb-2">See also</h4>
          <div className="flex flex-wrap gap-2">
            {definition.see_also.map((slug) => (
              <button
                key={slug}
                onClick={() => onSeeAlsoClick?.(slug)}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors cursor-pointer"
              >
                {slug.replace(/-/g, ' ')}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
