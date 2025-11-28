'use client';

import { useState, useEffect } from 'react';
import { Sparkles, Loader2, Calendar } from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import { ReflectionCard } from '@/components/ReflectionCard';
import { getSessions, getSessionReflection, type Session, type Reflection } from '@/lib/api';

interface ReflectionWithSession extends Reflection {
  session_number: number;
}

export default function ReflectionsPage() {
  const [reflections, setReflections] = useState<ReflectionWithSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReflections();
  }, []);

  const loadReflections = async () => {
    try {
      setIsLoading(true);
      // Get all sessions that have reflections
      const sessions = await getSessions();
      const sessionsWithReflections = sessions.filter((s) => s.has_reflection);

      // Load reflections for each session
      const reflectionPromises = sessionsWithReflections.map(async (session) => {
        try {
          const reflection = await getSessionReflection(session.id);
          return {
            ...reflection,
            session_number: session.session_number,
          };
        } catch {
          return null;
        }
      });

      const loadedReflections = (await Promise.all(reflectionPromises)).filter(
        (r): r is ReflectionWithSession => r !== null
      );

      // Sort by date, newest first
      loadedReflections.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setReflections(loadedReflections);
    } catch (err) {
      console.error('Failed to load reflections:', err);
      setError(err instanceof Error ? err.message : 'Failed to load reflections');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
          Reflections
        </h1>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          Track your growth through the 7 Universal Values
        </p>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 text-wisdom-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full">
            <p className="text-stone-500 mb-4">{error}</p>
            <button onClick={loadReflections} className="btn-secondary">
              Try again
            </button>
          </div>
        ) : reflections.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gold-100 dark:bg-gold-900/30 flex items-center justify-center mb-6">
              <Sparkles className="w-8 h-8 text-gold-500" />
            </div>
            <h2 className="text-2xl font-serif font-medium text-stone-800 dark:text-stone-200 mb-3">
              No Reflections Yet
            </h2>
            <p className="text-stone-500 dark:text-stone-400 max-w-md">
              Complete a conversation session to receive your first reflection and 
              7 Universal Values evaluation.
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {/* Summary stats */}
            <div className="card p-6 bg-gradient-to-br from-wisdom-50 to-gold-50 dark:from-wisdom-950 dark:to-stone-900">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-stone-800 dark:text-stone-200">
                    Your Wisdom Journey
                  </h3>
                  <p className="text-sm text-stone-500 dark:text-stone-400">
                    {reflections.length} reflection{reflections.length !== 1 ? 's' : ''} recorded
                  </p>
                </div>
                {reflections.length > 0 && (
                  <div className="text-right">
                    <div className="text-2xl font-medium text-wisdom-600 dark:text-wisdom-400">
                      {(
                        reflections.reduce((sum, r) => sum + (r.scores.overall || 0), 0) /
                        reflections.length
                      ).toFixed(1)}
                    </div>
                    <div className="text-xs text-stone-500 dark:text-stone-400">
                      Average Score
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Reflections list */}
            <div className="space-y-4">
              {reflections.map((reflection) => (
                <div key={reflection.session_id} className="animate-slide-up">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-stone-600 dark:text-stone-400">
                      Session #{reflection.session_number}
                    </span>
                    <span className="text-stone-300 dark:text-stone-600">•</span>
                    <span className="text-sm text-stone-500 dark:text-stone-500 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {formatDate(reflection.created_at)}
                    </span>
                  </div>
                  <ReflectionCard reflection={reflection} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
