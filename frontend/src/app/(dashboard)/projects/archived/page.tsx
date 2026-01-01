'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Archive, ArrowLeft, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getArchivedProjects, type Project } from '@/lib/api';
import { ProjectCard } from '@/components/ProjectCard';

export default function ArchivedProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const archivedProjects = await getArchivedProjects();
      setProjects(archivedProjects);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load archived projects');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-stone-950">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/projects"
            className={cn(
              'inline-flex items-center gap-2 mb-4 text-sm',
              'text-stone-500 dark:text-stone-400',
              'hover:text-wisdom-600 dark:hover:text-wisdom-400',
              'no-underline transition-colors'
            )}
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Projects
          </Link>
          
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-stone-200 dark:bg-stone-700 flex items-center justify-center">
              <Archive className="w-7 h-7 text-stone-500 dark:text-stone-400" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-semibold text-stone-900 dark:text-stone-100">
                Archived Projects
              </h1>
              <p className="text-stone-500 dark:text-stone-400">
                Projects you've archived for later reference
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-8 h-8 animate-spin text-stone-400" />
          </div>
        ) : error ? (
          <div className="card p-8 text-center">
            <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
            <button
              onClick={loadProjects}
              className={cn(
                'px-4 py-2 rounded-lg',
                'bg-stone-100 dark:bg-stone-800',
                'text-stone-700 dark:text-stone-300',
                'hover:bg-stone-200 dark:hover:bg-stone-700',
                'transition-colors'
              )}
            >
              Try Again
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div className="card p-12 text-center">
            <Archive className="w-16 h-16 mx-auto mb-4 text-stone-300 dark:text-stone-600" />
            <h2 className="text-xl font-serif font-medium text-stone-900 dark:text-stone-100 mb-2">
              No Archived Projects
            </h2>
            <p className="text-stone-500 dark:text-stone-400 mb-6">
              Projects you archive will appear here. You can archive a project from its card menu.
            </p>
            <Link
              href="/projects"
              className={cn(
                'inline-flex items-center gap-2 px-4 py-2 rounded-lg',
                'bg-wisdom-100 dark:bg-wisdom-900/30',
                'text-wisdom-700 dark:text-wisdom-300',
                'hover:bg-wisdom-200 dark:hover:bg-wisdom-900/50',
                'no-underline transition-colors'
              )}
            >
              <ArrowLeft className="w-4 h-4" />
              View Active Projects
            </Link>
          </div>
        ) : (
          <div className="grid gap-6">
            {projects.map((project) => (
              <ProjectCard
                key={project.id || project.name}
                project={project}
                onUpdate={loadProjects}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
