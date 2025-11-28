'use client';

import Link from 'next/link';
import { FolderKanban, Calendar, MessageSquare, ChevronRight } from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import type { Project } from '@/lib/api';

interface ProjectCardProps {
  project: Project;
  className?: string;
}

export function ProjectCard({ project, className }: ProjectCardProps) {
  const projectUrl = `/projects/${project.id || encodeURIComponent(project.name)}`;

  return (
    <Link href={projectUrl} className="block no-underline group">
      <div
        className={cn(
          'card p-6 transition-all duration-200',
          'hover:shadow-lg hover:border-wisdom-200 dark:hover:border-wisdom-800',
          'group-hover:-translate-y-0.5',
          className
        )}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div
              className={cn(
                'w-12 h-12 rounded-xl flex items-center justify-center',
                'bg-gradient-to-br from-wisdom-100 to-wisdom-200',
                'dark:from-wisdom-900 dark:to-wisdom-800'
              )}
            >
              <FolderKanban className="w-6 h-6 text-wisdom-600 dark:text-wisdom-400" />
            </div>
            <div>
              <h3 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100 group-hover:text-wisdom-600 dark:group-hover:text-wisdom-400 transition-colors">
                {project.name}
              </h3>
              <p className="text-sm text-stone-500 dark:text-stone-400 capitalize">
                {project.project_type}
              </p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-stone-400 group-hover:text-wisdom-500 transition-colors" />
        </div>

        {project.description && (
          <p className="mt-4 text-sm text-stone-600 dark:text-stone-300 line-clamp-2">
            {project.description}
          </p>
        )}

        <div className="mt-4 pt-4 border-t border-stone-100 dark:border-stone-800 flex items-center gap-6 text-sm text-stone-500 dark:text-stone-400">
          {project.created_at && (
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(project.created_at)}</span>
            </div>
          )}
          {project.session_count !== undefined && (
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              <span>{project.session_count} sessions</span>
            </div>
          )}
        </div>

        {project.goals && project.goals.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {project.goals.slice(0, 3).map((goal, i) => (
              <span
                key={i}
                className={cn(
                  'px-2.5 py-1 rounded-full text-xs',
                  'bg-stone-100 dark:bg-stone-800',
                  'text-stone-600 dark:text-stone-400'
                )}
              >
                {goal}
              </span>
            ))}
            {project.goals.length > 3 && (
              <span className="px-2.5 py-1 text-xs text-stone-400 dark:text-stone-500">
                +{project.goals.length - 3} more
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
