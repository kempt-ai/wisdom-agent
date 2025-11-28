'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Plus, Search, FolderKanban, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProjectCard } from '@/components/ProjectCard';
import { getProjects, type Project } from '@/lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [filteredProjects, setFilteredProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      setFilteredProjects(
        projects.filter(
          (p) =>
            p.name.toLowerCase().includes(query) ||
            p.description?.toLowerCase().includes(query) ||
            p.project_type.toLowerCase().includes(query)
        )
      );
    } else {
      setFilteredProjects(projects);
    }
  }, [searchQuery, projects]);

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      const data = await getProjects();
      setProjects(data);
      setFilteredProjects(data);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
              Projects
            </h1>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Manage your wisdom journey projects
            </p>
          </div>
          <Link
            href="/projects/new"
            className="btn-primary no-underline"
          >
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </div>

        {/* Search */}
        <div className="mt-4 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-12"
          />
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full">
            <Loader2 className="w-8 h-8 text-wisdom-500 animate-spin mb-4" />
            <p className="text-stone-500 dark:text-stone-400">Loading projects...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-4">
              <FolderKanban className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-serif font-medium text-stone-800 dark:text-stone-200 mb-2">
              Failed to load projects
            </h2>
            <p className="text-stone-500 dark:text-stone-400 mb-4">{error}</p>
            <button onClick={loadProjects} className="btn-secondary">
              Try again
            </button>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-wisdom-100 dark:bg-wisdom-900/30 flex items-center justify-center mb-4">
              <FolderKanban className="w-8 h-8 text-wisdom-500" />
            </div>
            {searchQuery ? (
              <>
                <h2 className="text-xl font-serif font-medium text-stone-800 dark:text-stone-200 mb-2">
                  No matching projects
                </h2>
                <p className="text-stone-500 dark:text-stone-400">
                  Try adjusting your search query
                </p>
              </>
            ) : (
              <>
                <h2 className="text-xl font-serif font-medium text-stone-800 dark:text-stone-200 mb-2">
                  No projects yet
                </h2>
                <p className="text-stone-500 dark:text-stone-400 mb-4">
                  Create your first project to begin your wisdom journey
                </p>
                <Link href="/projects/new" className="btn-primary no-underline">
                  <Plus className="w-4 h-4" />
                  Create Project
                </Link>
              </>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredProjects.map((project) => (
              <ProjectCard key={project.id || project.name} project={project} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
