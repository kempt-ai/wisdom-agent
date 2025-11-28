'use client';

import { Sparkles, Calendar, ChevronDown } from 'lucide-react';
import { cn, formatDate, UNIVERSAL_VALUES } from '@/lib/utils';
import { ValueScore } from './ValueScore';
import type { Reflection } from '@/lib/api';
import { useState } from 'react';

interface ReflectionCardProps {
  reflection: Reflection;
  className?: string;
}

export function ReflectionCard({ reflection, className }: ReflectionCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Calculate average score
  const scores = reflection.scores;
  const avgScore = scores.overall || 
    Object.values(scores).reduce((a, b) => a + b, 0) / Object.keys(scores).length;

  return (
    <div
      className={cn(
        'card overflow-hidden transition-all duration-300',
        className
      )}
    >
      {/* Header */}
      <div className="p-6 bg-gradient-to-br from-wisdom-50 to-gold-50 dark:from-wisdom-950 dark:to-stone-900">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-white/80 dark:bg-stone-800/80 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-gold-500" />
            </div>
            <div>
              <h3 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100">
                Session Reflection
              </h3>
              <div className="flex items-center gap-2 text-sm text-stone-500 dark:text-stone-400">
                <Calendar className="w-4 h-4" />
                <span>{formatDate(reflection.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Overall score badge */}
          <div className="flex flex-col items-center">
            <div className={cn(
              'text-2xl font-medium',
              avgScore >= 8 && 'text-sage-600',
              avgScore >= 6 && avgScore < 8 && 'text-gold-600',
              avgScore < 6 && 'text-wisdom-600'
            )}>
              {avgScore.toFixed(1)}
            </div>
            <div className="text-xs text-stone-500 dark:text-stone-400">
              Overall
            </div>
          </div>
        </div>
      </div>

      {/* Scores preview */}
      <div className="p-6 border-b border-stone-100 dark:border-stone-800">
        <div className="flex flex-wrap gap-3">
          {UNIVERSAL_VALUES.map((value) => (
            <div
              key={value.key}
              className={cn(
                'px-3 py-1.5 rounded-full text-sm',
                'bg-stone-100 dark:bg-stone-800',
                'flex items-center gap-2'
              )}
            >
              <span className="text-stone-500 dark:text-stone-400">
                {value.label}:
              </span>
              <span className={cn(
                'font-medium',
                (scores[value.key as keyof typeof scores] || 0) >= 8 && 'text-sage-600',
                (scores[value.key as keyof typeof scores] || 0) >= 6 && 
                (scores[value.key as keyof typeof scores] || 0) < 8 && 'text-gold-600',
                (scores[value.key as keyof typeof scores] || 0) < 6 && 'text-stone-600'
              )}>
                {(scores[value.key as keyof typeof scores] || 0).toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Reflection text */}
      <div className="p-6">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between text-left"
        >
          <span className="text-sm font-medium text-stone-600 dark:text-stone-300">
            {expanded ? 'Hide reflection' : 'View reflection'}
          </span>
          <ChevronDown
            className={cn(
              'w-5 h-5 text-stone-400 transition-transform duration-200',
              expanded && 'rotate-180'
            )}
          />
        </button>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-stone-100 dark:border-stone-800">
            <div className="prose-chat text-stone-700 dark:text-stone-300">
              {reflection.reflection_text.split('\n').map((paragraph, i) => (
                <p key={i} className="mb-3 last:mb-0">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
