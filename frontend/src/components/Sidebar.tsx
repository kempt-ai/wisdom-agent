'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  MessageSquare,
  FolderKanban,
  BookOpen,
  Settings,
  Sparkles,
  ChevronDown,
  Plus,
  Sun,
  Moon,
  History,  // NEW - icon for Sessions
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getProjects, type Project } from '@/lib/api';

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsExpanded, setProjectsExpanded] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Load projects
    getProjects()
      .then(setProjects)
      .catch(console.error);
  }, []);

  useEffect(() => {
    // Check for dark mode preference
    if (typeof window !== 'undefined') {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(isDark);
    }
  }, []);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  const navigation = [
    {
      name: 'Chat',
      href: '/chat',
      icon: MessageSquare,
    },
    // NEW - Wisdom Sessions link (Week 3 Day 4)
    {
      name: 'Wisdom Sessions',
      href: '/sessions',
      icon: History,
    },
    {
      name: 'Projects',
      href: '/projects',
      icon: FolderKanban,
      expandable: true,
    },
    {
      name: 'Philosophy',
      href: '/philosophy',
      icon: BookOpen,
    },
    {
      name: 'Reflections',
      href: '/reflections',
      icon: Sparkles,
    },
  ];

  return (
    <aside className={cn('sidebar flex flex-col', className)}>
      {/* Logo & Brand */}
      <div className="p-6 border-b border-stone-200 dark:border-stone-800">
        <Link href="/" className="flex items-center gap-3 no-underline">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-wisdom-500 to-wisdom-700 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-serif font-semibold text-stone-900 dark:text-stone-100">
              Wisdom Agent
            </h1>
            <p className="text-xs text-stone-500 dark:text-stone-400">
              Something Deeperism
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto scrollbar-hide">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
          const Icon = item.icon;

          if (item.expandable) {
            return (
              <div key={item.name}>
                <button
                  onClick={() => setProjectsExpanded(!projectsExpanded)}
                  className={cn(
                    'w-full flex items-center justify-between gap-3 px-4 py-3 rounded-lg',
                    'text-stone-600 dark:text-stone-300',
                    'hover:bg-stone-200 dark:hover:bg-stone-800',
                    'transition-colors duration-150'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.name}</span>
                  </div>
                  <ChevronDown
                    className={cn(
                      'w-4 h-4 transition-transform duration-200',
                      projectsExpanded && 'rotate-180'
                    )}
                  />
                </button>

                {/* Projects list */}
                {projectsExpanded && (
                  <div className="mt-1 ml-4 pl-4 border-l border-stone-200 dark:border-stone-700 space-y-1">
                    <Link
                      href="/projects"
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg text-sm no-underline',
                        pathname === '/projects'
                          ? 'bg-wisdom-100 dark:bg-wisdom-900/30 text-wisdom-700 dark:text-wisdom-300'
                          : 'text-stone-500 dark:text-stone-400 hover:bg-stone-200 dark:hover:bg-stone-800'
                      )}
                    >
                      All Projects
                    </Link>
                    {projects.slice(0, 5).map((project) => (
                      <Link
                        key={project.id || project.name}
                        href={`/projects/${project.id || encodeURIComponent(project.name)}`}
                        className={cn(
                          'flex items-center gap-2 px-3 py-2 rounded-lg text-sm no-underline',
                          'text-stone-500 dark:text-stone-400',
                          'hover:bg-stone-200 dark:hover:bg-stone-800',
                          'truncate'
                        )}
                      >
                        {project.name}
                      </Link>
                    ))}
                    <Link
                      href="/projects/new"
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg text-sm no-underline',
                        'text-wisdom-600 dark:text-wisdom-400',
                        'hover:bg-wisdom-50 dark:hover:bg-wisdom-900/20'
                      )}
                    >
                      <Plus className="w-4 h-4" />
                      New Project
                    </Link>
                  </div>
                )}
              </div>
            );
          }

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg no-underline',
                'transition-colors duration-150',
                isActive
                  ? 'bg-wisdom-100 dark:bg-wisdom-900/30 text-wisdom-700 dark:text-wisdom-300'
                  : 'text-stone-600 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-stone-800'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-stone-200 dark:border-stone-800">
        <div className="flex items-center justify-between">
          <Link
            href="/settings"
            className={cn(
              'flex items-center gap-3 px-4 py-3 rounded-lg no-underline',
              'text-stone-500 dark:text-stone-400',
              'hover:bg-stone-200 dark:hover:bg-stone-800',
              'transition-colors duration-150'
            )}
          >
            <Settings className="w-5 h-5" />
            <span className="font-medium">Settings</span>
          </Link>
          <button
            onClick={toggleDarkMode}
            className={cn(
              'p-2 rounded-lg',
              'text-stone-500 dark:text-stone-400',
              'hover:bg-stone-200 dark:hover:bg-stone-800',
              'transition-colors duration-150'
            )}
            aria-label="Toggle dark mode"
          >
            {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </aside>
  );
}
