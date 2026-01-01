'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  FolderKanban, 
  Calendar, 
  MessageSquare, 
  ChevronRight,
  MoreVertical,  // NEW
  Archive,       // NEW
  ArchiveRestore, // NEW
  Trash2,        // NEW
  X,             // NEW
} from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import { archiveProject, unarchiveProject, deleteProject } from '@/lib/api';
import type { Project } from '@/lib/api';

interface ProjectCardProps {
  project: Project;
  className?: string;
  onUpdate?: () => void;  // NEW - callback when project is modified
}

export function ProjectCard({ project, className, onUpdate }: ProjectCardProps) {
  const router = useRouter();
  const projectUrl = `/projects/${project.id || encodeURIComponent(project.name)}`;
  
  // NEW - state for dropdown and modals
  const [showMenu, setShowMenu] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  // NEW - handle archive/unarchive
  const handleArchive = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsArchiving(true);
    
    try {
      if (project.is_archived) {
        await unarchiveProject(project.id || project.name);
      } else {
        await archiveProject(project.id || project.name);
      }
      setShowMenu(false);
      onUpdate?.();
    } catch (err) {
      console.error('Failed to archive project:', err);
    } finally {
      setIsArchiving(false);
    }
  };

  // NEW - handle delete
  const handleDelete = async () => {
    setIsDeleting(true);
    
    try {
      await deleteProject(project.id || project.name);
      setShowDeleteModal(false);
      setShowMenu(false);
      onUpdate?.();
      router.push('/projects');
    } catch (err) {
      console.error('Failed to delete project:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <div className="relative group">
        <Link href={projectUrl} className="block no-underline">
          <div
            className={cn(
              'card p-6 transition-all duration-200',
              'hover:shadow-lg hover:border-wisdom-200 dark:hover:border-wisdom-800',
              'group-hover:-translate-y-0.5',
              project.is_archived && 'opacity-60',
              className
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div
                  className={cn(
                    'w-12 h-12 rounded-xl flex items-center justify-center',
                    project.is_archived
                      ? 'bg-stone-200 dark:bg-stone-700'
                      : 'bg-gradient-to-br from-wisdom-100 to-wisdom-200 dark:from-wisdom-900 dark:to-wisdom-800'
                  )}
                >
                  {project.is_archived ? (
                    <Archive className="w-6 h-6 text-stone-500 dark:text-stone-400" />
                  ) : (
                    <FolderKanban className="w-6 h-6 text-wisdom-600 dark:text-wisdom-400" />
                  )}
                </div>
                <div>
                  <h3 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100 group-hover:text-wisdom-600 dark:group-hover:text-wisdom-400 transition-colors">
                    {project.name}
                    {project.is_archived && (
                      <span className="ml-2 text-xs font-normal text-stone-400 dark:text-stone-500">
                        (Archived)
                      </span>
                    )}
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

        {/* NEW - Action Menu Button */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
          className={cn(
            'absolute top-4 right-4 p-2 rounded-lg',
            'text-stone-400 hover:text-stone-600 dark:hover:text-stone-300',
            'hover:bg-stone-100 dark:hover:bg-stone-800',
            'opacity-0 group-hover:opacity-100 transition-opacity',
            showMenu && 'opacity-100 bg-stone-100 dark:bg-stone-800'
          )}
        >
          <MoreVertical className="w-5 h-5" />
        </button>

        {/* NEW - Dropdown Menu */}
        {showMenu && (
          <>
            {/* Backdrop to close menu */}
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setShowMenu(false)}
            />
            
            <div className={cn(
              'absolute top-12 right-4 z-20',
              'bg-white dark:bg-stone-800 rounded-xl shadow-lg',
              'border border-stone-200 dark:border-stone-700',
              'py-2 min-w-[160px]'
            )}>
              <button
                onClick={handleArchive}
                disabled={isArchiving}
                className={cn(
                  'w-full px-4 py-2 text-left text-sm',
                  'flex items-center gap-3',
                  'text-stone-700 dark:text-stone-300',
                  'hover:bg-stone-100 dark:hover:bg-stone-700',
                  'disabled:opacity-50'
                )}
              >
                {project.is_archived ? (
                  <>
                    <ArchiveRestore className="w-4 h-4" />
                    Unarchive
                  </>
                ) : (
                  <>
                    <Archive className="w-4 h-4" />
                    Archive
                  </>
                )}
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowDeleteModal(true);
                }}
                className={cn(
                  'w-full px-4 py-2 text-left text-sm',
                  'flex items-center gap-3',
                  'text-red-600 dark:text-red-400',
                  'hover:bg-red-50 dark:hover:bg-red-900/20'
                )}
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          </>
        )}
      </div>

      {/* NEW - Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-stone-900 rounded-2xl max-w-md w-full p-6 shadow-xl">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <h3 className="text-lg font-serif font-medium text-stone-900 dark:text-stone-100">
                  Delete Project?
                </h3>
              </div>
              <button
                onClick={() => setShowDeleteModal(false)}
                className="text-stone-400 hover:text-stone-600 dark:hover:text-stone-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-stone-600 dark:text-stone-400 mb-2">
              Are you sure you want to delete <strong>{project.name}</strong>?
            </p>
            <p className="text-sm text-red-600 dark:text-red-400 mb-6">
              This will permanently delete the project and all its sessions. This action cannot be undone.
            </p>
            
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
                className={cn(
                  'flex-1 px-4 py-2 rounded-xl',
                  'bg-stone-100 dark:bg-stone-800',
                  'text-stone-700 dark:text-stone-300',
                  'hover:bg-stone-200 dark:hover:bg-stone-700',
                  'transition-colors duration-200',
                  'disabled:opacity-50'
                )}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className={cn(
                  'flex-1 px-4 py-2 rounded-xl',
                  'bg-red-600 dark:bg-red-500',
                  'text-white',
                  'hover:bg-red-700 dark:hover:bg-red-600',
                  'transition-colors duration-200',
                  'disabled:opacity-50 flex items-center justify-center gap-2'
                )}
              >
                {isDeleting ? (
                  'Deleting...'
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete Project
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
