import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date for display
 */
export function formatDate(date: string | Date): string {
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format a timestamp for display
 */
export function formatTime(date: string | Date): string {
  const d = new Date(date);
  return d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Generate a simple ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

/**
 * Debounce a function
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Map reflection score to a color
 */
export function getScoreColor(score: number): string {
  if (score >= 8) return 'text-sage-600';
  if (score >= 6) return 'text-gold-600';
  if (score >= 4) return 'text-stone-500';
  return 'text-stone-400';
}

/**
 * Format the 7 Universal Values for display
 */
export const UNIVERSAL_VALUES = [
  { key: 'awareness', label: 'Awareness', description: 'Present-moment attention and mindfulness' },
  { key: 'honesty', label: 'Honesty', description: 'Truthfulness with self and others' },
  { key: 'accuracy', label: 'Accuracy', description: 'Precision in thought and expression' },
  { key: 'competence', label: 'Competence', description: 'Skill and capability development' },
  { key: 'compassion', label: 'Compassion', description: 'Understanding and caring for others' },
  { key: 'loving_kindness', label: 'Loving-Kindness', description: 'Unconditional positive regard' },
  { key: 'joyful_sharing', label: 'Joyful Sharing', description: 'Delight in giving and connecting' },
] as const;
