'use client';

/**
 * Wisdom Sessions Page
 * 
 * Browse past conversation sessions, view transcripts,
 * summaries, and 7 Universal Values reflections.
 * 
 * Created: Week 3 Day 4
 */

import { useState, useEffect } from 'react';
import SessionList from '@/components/SessionList';
import { getProjects, type Project } from '@/lib/api';

export default function SessionsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number>(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await getProjects();
      setProjects(data);
      // Default to first project if available
      if (data.length > 0 && data[0].id) {
        setSelectedProjectId(Number(data[0].id));
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900">
        <h1 className="text-2xl font-serif font-semibold text-stone-900 dark:text-stone-100">
          Wisdom Sessions
        </h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">
          Browse your past conversations, summaries, and reflections
        </p>
        
        {/* Project Selector */}
        {projects.length > 1 && (
          <div className="mt-4">
            <label className="text-sm text-stone-600 dark:text-stone-400 mr-2">
              Project:
            </label>
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(Number(e.target.value))}
              className="px-3 py-2 rounded-lg border border-stone-300 dark:border-stone-600 
                         bg-white dark:bg-stone-800 text-stone-800 dark:text-stone-200
                         focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              {projects.map((project) => (
                <option key={project.id || project.name} value={Number(project.id) || 1}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-hidden bg-white dark:bg-stone-900">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin inline-block w-8 h-8 border-2 border-stone-300 border-t-amber-500 rounded-full mb-3"></div>
              <p className="text-stone-500">Loading...</p>
            </div>
          </div>
        ) : (
          <SessionList 
            projectId={selectedProjectId}
            onSelectSession={(sessionId) => {
              console.log('Selected session:', sessionId);
            }}
          />
        )}
      </div>
    </div>
  );
}
