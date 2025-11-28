'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, Plus, X } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { createProject } from '@/lib/api';

const PROJECT_TYPES = [
  { value: 'wisdom', label: 'Wisdom Journey', description: 'Personal growth and philosophical exploration' },
  { value: 'learning', label: 'Learning Project', description: 'Structured skill or knowledge acquisition' },
  { value: 'reflection', label: 'Reflection Practice', description: 'Regular contemplation and self-examination' },
  { value: 'creative', label: 'Creative Work', description: 'Writing, art, or other creative endeavors' },
  { value: 'other', label: 'Other', description: 'Custom project type' },
];

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState('wisdom');
  const [description, setDescription] = useState('');
  const [goals, setGoals] = useState<string[]>([]);
  const [newGoal, setNewGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addGoal = () => {
    if (newGoal.trim() && !goals.includes(newGoal.trim())) {
      setGoals([...goals, newGoal.trim()]);
      setNewGoal('');
    }
  };

  const removeGoal = (index: number) => {
    setGoals(goals.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const project = await createProject({
        name: name.trim(),
        project_type: projectType,
        description: description.trim() || undefined,
        goals: goals.length > 0 ? goals : undefined,
      });
      router.push(`/projects/${project.id || encodeURIComponent(project.name)}`);
    } catch (err) {
      console.error('Failed to create project:', err);
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <div className="flex items-center gap-4">
          <Link
            href="/projects"
            className="p-2 rounded-lg text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors no-underline"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
              Create New Project
            </h1>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Start a new wisdom journey
            </p>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-8">
          {/* Project Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">
              Project Name *
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Learning Spanish, Mindfulness Practice"
              className="input"
              required
            />
          </div>

          {/* Project Type */}
          <div>
            <label className="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">
              Project Type
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PROJECT_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setProjectType(type.value)}
                  className={cn(
                    'p-4 rounded-xl text-left transition-all duration-200',
                    'border-2',
                    projectType === type.value
                      ? 'border-wisdom-500 bg-wisdom-50 dark:bg-wisdom-900/20'
                      : 'border-stone-200 dark:border-stone-700 hover:border-stone-300 dark:hover:border-stone-600'
                  )}
                >
                  <div className={cn(
                    'font-medium',
                    projectType === type.value
                      ? 'text-wisdom-700 dark:text-wisdom-300'
                      : 'text-stone-800 dark:text-stone-200'
                  )}>
                    {type.label}
                  </div>
                  <div className="text-sm text-stone-500 dark:text-stone-400 mt-1">
                    {type.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this project about? What do you hope to achieve?"
              rows={4}
              className="input resize-none"
            />
          </div>

          {/* Goals */}
          <div>
            <label className="block text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">
              Goals
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={newGoal}
                onChange={(e) => setNewGoal(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addGoal();
                  }
                }}
                placeholder="Add a goal..."
                className="input flex-1"
              />
              <button
                type="button"
                onClick={addGoal}
                disabled={!newGoal.trim()}
                className="btn-secondary"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            {goals.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {goals.map((goal, i) => (
                  <span
                    key={i}
                    className={cn(
                      'inline-flex items-center gap-2 px-3 py-1.5 rounded-full',
                      'bg-wisdom-100 dark:bg-wisdom-900/30',
                      'text-sm text-wisdom-700 dark:text-wisdom-300'
                    )}
                  >
                    {goal}
                    <button
                      type="button"
                      onClick={() => removeGoal(i)}
                      className="hover:text-wisdom-900 dark:hover:text-wisdom-100"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Submit */}
          <div className="flex items-center gap-4 pt-4">
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="btn-primary"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Project'
              )}
            </button>
            <Link href="/projects" className="btn-ghost no-underline">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
