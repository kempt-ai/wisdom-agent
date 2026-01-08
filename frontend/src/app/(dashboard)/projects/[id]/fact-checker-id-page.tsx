'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  MessageSquare,
  Calendar,
  Target,
  Trash2,
  Edit2,
  Loader2,
  Play,
  Sparkles,
} from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import { getProject, getSessions, deleteProject, type Project, type Session } from '@/lib/api';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      setIsLoading(true);
      const [projectData, sessionsData] = await Promise.all([
        getProject(projectId),
        getSessions(projectId).catch(() => []),
      ]);
      setProject(projectData);
      setSessions(sessionsData);
    } catch (err) {
      console.error('Failed to load project:', err);
      setError(err instanceof Error ? err.message : 'Failed to load project');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      await deleteProject(projectId);
      router.push('/projects');
    } catch (err) {
      console.error('Failed to delete project:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete project');
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-wisdom-500 animate-spin" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <h2 className="text-xl font-serif font-medium text-stone-800 dark:text-stone-200 mb-2">
          Project not found
        </h2>
        <p className="text-stone-500 dark:text-stone-400 mb-4">{error}</p>
        <Link href="/projects" className="btn-primary no-underline">
          Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/projects"
              className="p-2 rounded-lg text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors no-underline"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
                {project.name}
              </h1>
              <p className="text-sm text-stone-500 dark:text-stone-400 capitalize">
                {project.project_type}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-ghost">
              <Edit2 className="w-4 h-4" />
              Edit
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="btn-ghost text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Overview */}
          <div className="card p-6">
            <div className="flex items-start gap-4">
              <div className="flex-1">
                {project.description && (
                  <p className="text-stone-600 dark:text-stone-300 mb-4">
                    {project.description}
                  </p>
                )}
                <div className="flex flex-wrap gap-4 text-sm text-stone-500 dark:text-stone-400">
                  {project.created_at && (
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      <span>Created {formatDate(project.created_at)}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    <span>{sessions.length} sessions</span>
                  </div>
                </div>
              </div>
              <Link
                href={`/chat?project=${projectId}`}
                className="btn-primary no-underline"
              >
                <Play className="w-4 h-4" />
                Start Session
              </Link>
            </div>

            {/* Goals */}
            {project.goals && project.goals.length > 0 && (
              <div className="mt-6 pt-6 border-t border-stone-100 dark:border-stone-800">
                <h3 className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Goals
                </h3>
                <ul className="space-y-2">
                  {project.goals.map((goal, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-wisdom-500 mt-2" />
                      <span className="text-stone-600 dark:text-stone-300">{goal}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Sessions */}
          <div>
            <h2 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100 mb-4">
              Sessions
            </h2>
            {sessions.length === 0 ? (
              <div className="card p-8 text-center">
                <div className="w-12 h-12 rounded-xl bg-wisdom-100 dark:bg-wisdom-900/30 flex items-center justify-center mx-auto mb-4">
                  <MessageSquare className="w-6 h-6 text-wisdom-500" />
                </div>
                <p className="text-stone-500 dark:text-stone-400 mb-4">
                  No sessions yet. Start your first session to begin.
                </p>
                <Link
                  href={`/chat?project=${projectId}`}
                  className="btn-primary no-underline"
                >
                  <Play className="w-4 h-4" />
                  Start Session
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.map((session) => (
                  <Link
                    key={session.id}
                    href={`/chat?session=${session.id}`}
                    className="card p-4 flex items-center justify-between group hover:border-wisdom-200 dark:hover:border-wisdom-800 transition-colors no-underline"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-stone-100 dark:bg-stone-800 flex items-center justify-center">
                        <span className="text-sm font-medium text-stone-600 dark:text-stone-300">
                          #{session.session_number}
                        </span>
                      </div>
                      <div>
                        <div className="font-medium text-stone-800 dark:text-stone-200 group-hover:text-wisdom-600 dark:group-hover:text-wisdom-400 transition-colors">
                          Session {session.session_number}
                        </div>
                        <div className="text-sm text-stone-500 dark:text-stone-400">
                          {formatDate(session.started_at)} · {session.message_count} messages
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {session.has_reflection && (
                        <span className="px-2 py-1 rounded-full text-xs bg-gold-100 dark:bg-gold-900/30 text-gold-700 dark:text-gold-300">
                          <Sparkles className="w-3 h-3 inline mr-1" />
                          Reflected
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="card p-6 max-w-md w-full">
            <h3 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100 mb-2">
              Delete Project?
            </h3>
            <p className="text-stone-600 dark:text-stone-300 mb-6">
              This will permanently delete "{project.name}" and all its sessions. This action cannot be undone.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="btn-secondary"
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="btn bg-red-600 text-white hover:bg-red-700"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
