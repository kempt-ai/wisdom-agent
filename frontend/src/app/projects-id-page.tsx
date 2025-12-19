'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Folder,
  MessageSquare,
  Calendar,
  Sparkles,
  Settings,
  Trash2,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getProject, getSessions, deleteProject, type Project } from '@/lib/api';
import { SessionCard } from '@/components/SessionCard';

interface Session {
  id: number;
  title?: string;
  summary?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  has_reflection: boolean;
  project_id?: number;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const loadProjectData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [projectData, sessionsData] = await Promise.all([
        getProject(projectId),
        getSessions(projectId),
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
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Calculate stats
  const totalMessages = sessions.reduce((sum, s) => sum + s.message_count, 0);
  const reflectedSessions = sessions.filter((s) => s.has_reflection).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-wisdom-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
        <button
          onClick={() => router.push('/projects')}
          className="mt-4 text-wisdom-600 hover:text-wisdom-700 flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </button>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-stone-500">Project not found</div>
        <button
          onClick={() => router.push('/projects')}
          className="mt-4 text-wisdom-600 hover:text-wisdom-700 flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push('/projects')}
          className="text-stone-500 hover:text-stone-700 flex items-center gap-1 text-sm mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          All Projects
        </button>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-wisdom-100 rounded-lg">
              <Folder className="w-6 h-6 text-wisdom-600" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-stone-800">
                {project.name}
              </h1>
              {project.description && (
                <p className="text-stone-500 mt-1">{project.description}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push(`/projects/${projectId}/settings`)}
              className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg transition-colors"
            >
              <Settings className="w-5 h-5" />
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="p-2 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-stone-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-stone-500 text-sm">
            <MessageSquare className="w-4 h-4" />
            Sessions
          </div>
          <div className="text-2xl font-semibold text-stone-800 mt-1">
            {sessions.length}
          </div>
        </div>
        <div className="bg-stone-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-stone-500 text-sm">
            <MessageSquare className="w-4 h-4" />
            Total Messages
          </div>
          <div className="text-2xl font-semibold text-stone-800 mt-1">
            {totalMessages}
          </div>
        </div>
        <div className="bg-gold-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-gold-600 text-sm">
            <Sparkles className="w-4 h-4" />
            Reflected
          </div>
          <div className="text-2xl font-semibold text-gold-700 mt-1">
            {reflectedSessions}
          </div>
        </div>
      </div>

      {/* Sessions List */}
      <div>
        <h2 className="text-lg font-medium text-stone-700 mb-4">
          Sessions
        </h2>

        {sessions.length === 0 ? (
          <div className="text-center py-12 bg-stone-50 rounded-lg">
            <MessageSquare className="w-12 h-12 text-stone-300 mx-auto mb-3" />
            <h3 className="text-stone-500 font-medium">No sessions yet</h3>
            <p className="text-stone-400 text-sm mt-1">
              Start a conversation to create your first session
            </p>
            <button
              onClick={() => router.push('/')}
              className="mt-4 px-4 py-2 bg-wisdom-600 text-white rounded-lg hover:bg-wisdom-700 transition-colors"
            >
              Start Chatting
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <SessionCard key={session.id} session={session} />
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-stone-800 mb-2">
              Delete Project?
            </h3>
            <p className="text-stone-600 mb-4">
              This will permanently delete "{project.name}" and all its sessions.
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-stone-600 hover:bg-stone-100 rounded-lg transition-colors"
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                disabled={isDeleting}
              >
                {isDeleting && <Loader2 className="w-4 h-4 animate-spin" />}
                Delete Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
