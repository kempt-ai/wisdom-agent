'use client';

import { cn, getScoreColor, UNIVERSAL_VALUES } from '@/lib/utils';

interface ValueScoreProps {
  valueKey: string;
  score: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ValueScore({
  valueKey,
  score,
  showLabel = true,
  size = 'md',
  className,
}: ValueScoreProps) {
  const value = UNIVERSAL_VALUES.find((v) => v.key === valueKey);
  const label = value?.label || valueKey;
  const description = value?.description || '';

  const sizeClasses = {
    sm: 'w-10 h-10 text-sm',
    md: 'w-14 h-14 text-lg',
    lg: 'w-20 h-20 text-2xl',
  };

  // Calculate the percentage for the circular progress
  const percentage = (score / 10) * 100;
  const circumference = 2 * Math.PI * 45; // radius = 45
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className={cn('relative', sizeClasses[size])}>
        {/* Background circle */}
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            className="text-stone-100 dark:text-stone-800"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(
              'transition-all duration-500 ease-out',
              score >= 8 && 'text-sage-500',
              score >= 6 && score < 8 && 'text-gold-500',
              score >= 4 && score < 6 && 'text-wisdom-500',
              score < 4 && 'text-stone-400'
            )}
          />
        </svg>
        {/* Score number */}
        <div className="absolute inset-0 flex items-center justify-center font-medium text-stone-700 dark:text-stone-300">
          {score.toFixed(1)}
        </div>
      </div>

      {showLabel && (
        <div className="flex-1 min-w-0">
          <div className="font-medium text-stone-800 dark:text-stone-200 truncate">
            {label}
          </div>
          {size !== 'sm' && (
            <div className="text-xs text-stone-500 dark:text-stone-400 truncate">
              {description}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface ValueScoresGridProps {
  scores: Record<string, number>;
  className?: string;
}

export function ValueScoresGrid({ scores, className }: ValueScoresGridProps) {
  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-2 gap-4', className)}>
      {UNIVERSAL_VALUES.map((value) => (
        <ValueScore
          key={value.key}
          valueKey={value.key}
          score={scores[value.key] || 0}
          size="md"
        />
      ))}
    </div>
  );
}
