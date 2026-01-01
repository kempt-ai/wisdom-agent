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
  History,
  CheckCircle,
  Archive,
  DollarSign,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getProjects, type Project } from '@/lib/api';

// API base URL - adjust if needed
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SidebarProps {
  className?: string;
}

interface SpendingData {
  month_display: string;
  total_spent: number;
  limit: number;
  percentage_used: number;
  at_warning: boolean;
}

// Spending Widget Component
function SpendingWidget() {
  const [spending, setSpending] = useState<SpendingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    // Fetch spending data from backend
    const fetchSpending = async () => {
      try {
        const response = await fetch(`${API_BASE}/spending/dashboard?user_id=1`);
        if (response.ok) {
          const data = await response.json();
          setSpending(data);
          setError(false);
        } else {
          setError(true);
        }
      } catch (err) {
        console.error('Failed to fetch spending data:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchSpending();
    
    // Refresh every 60 seconds
    const interval = setInterval(fetchSpending, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="px-4 py-3">
        <div className="h-12 bg-stone-100 dark:bg-stone-800 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !spending) {
    return null; // Silently hide if spending service isn't available
  }

  const percentageWidth = Math.min(spending.percentage_used, 100);
  
  // Color based on usage
  const getBarColor = () => {
    if (spending.percentage_used >= 100) return 'bg-red-500';
    if (spending.at_warning) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  const getTextColor = () => {
    if (spending.percentage_used >= 100) return 'text-red-600 dark:text-red-400';
    if (spending.at_warning) return 'text-amber-600 dark:text-amber-400';
    return 'text-stone-600 dark:text-stone-400';
  };

  return (
    <Link
      href="/settings#spending"
      className="block px-4 py-2 no-underline group"
    >
      <div className={cn(
        "p-3 rounded-lg transition-colors duration-150",
        "bg-stone-50 dark:bg-stone-800/50",
        "hover:bg-stone-100 dark:hover:bg-stone-800",
        "border border-stone-200 dark:border-stone-700"
      )}>
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <DollarSign className={cn("w-4 h-4", getTextColor())} />
            <span className="text-xs font-medium text-stone-500 dark:text-stone-400">
              {spending.month_display}
            </span>
          </div>
          {spending.at_warning && (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          )}
        </div>

        {/* Amount display */}
        <div className="flex items-baseline gap-1 mb-2">
          <span className={cn("text-lg font-semibold", getTextColor())}>
            ${spending.total_spent.toFixed(2)}
          </span>
          <span className="text-xs text-stone-400 dark:text-stone-500">
            / ${spending.limit.toFixed(0)}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 bg-stone-200 dark:bg-stone-700 rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-300", getBarColor())}
            style={{ width: `${percentageWidth}%` }}
          />
        </div>

        {/* Percentage label */}
        <div className="mt-1 text-right">
          <span className={cn("text-xs font-medium", getTextColor())}>
            {spending.percentage_used.toFixed(0)}% used
          </span>
        </div>
      </div>
    </Link>
  );
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsExpanded, setProjectsExpanded] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Load projects (excluding archived)
    getProjects()
      .then((allProjects) => {
        // Filter out archived projects for the sidebar
        const activeProjects = allProjects.filter(p => !p.is_archived);
        setProjects(activeProjects);
      })
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
    {
      name: 'Wisdom Sessions',
      href: '/sessions',
      icon: History,
    },
    {
      name: 'Fact Checker',
      href: '/fact-checker',
      icon: CheckCircle,
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
                    {/* Archived Projects Link */}
                    <Link
                      href="/projects/archived"
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg text-sm no-underline',
                        pathname === '/projects/archived'
                          ? 'bg-stone-200 dark:bg-stone-700 text-stone-700 dark:text-stone-300'
                          : 'text-stone-400 dark:text-stone-500 hover:bg-stone-200 dark:hover:bg-stone-800'
                      )}
                    >
                      <Archive className="w-4 h-4" />
                      Archived
                    </Link>
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

      {/* Footer - Spending Widget + Settings */}
      <div className="border-t border-stone-200 dark:border-stone-800">
        {/* Spending Widget */}
        <SpendingWidget />
        
        {/* Settings row */}
        <div className="p-4 pt-2 flex items-center justify-between">
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
