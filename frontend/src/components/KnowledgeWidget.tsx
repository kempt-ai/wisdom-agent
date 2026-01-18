'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Database, Search, FolderOpen, FileText, 
  ChevronRight, Plus, RefreshCw
} from 'lucide-react';
import { knowledgeApi, CollectionSummary, KnowledgeStats } from '@/lib/knowledge-api';

interface KnowledgeWidgetProps {
  compact?: boolean;
  className?: string;
}

export function KnowledgeWidget({ compact = false, className = '' }: KnowledgeWidgetProps) {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [recentCollections, setRecentCollections] = useState<CollectionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [statsData, collectionsData] = await Promise.all([
        knowledgeApi.getStats(),
        knowledgeApi.listCollections(),
      ]);
      setStats(statsData);
      setRecentCollections(collectionsData.slice(0, 3));
    } catch (err) {
      console.error('Failed to load KB data:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className={`p-4 ${className}`}>
        <div className="flex items-center gap-2 text-slate-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  // Compact mode - just an icon link
  if (compact && !expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className={`p-3 hover:bg-slate-100 rounded-lg transition-colors ${className}`}
        title="Knowledge Base"
      >
        <Database className="w-5 h-5 text-slate-600" />
      </button>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-slate-200 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <Link 
            href="/knowledge" 
            className="flex items-center gap-2 font-medium text-slate-900 hover:text-indigo-600"
          >
            <Database className="w-4 h-4" />
            Knowledge Base
          </Link>
          <div className="flex items-center gap-1">
            <Link
              href="/knowledge/search"
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
              title="Search"
            >
              <Search className="w-4 h-4" />
            </Link>
            <Link
              href="/knowledge"
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
              title="Add new"
            >
              <Plus className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="px-4 py-3 grid grid-cols-2 gap-3 border-b border-slate-100">
          <div>
            <p className="text-lg font-semibold text-slate-900">{stats.collections}</p>
            <p className="text-xs text-slate-500">Collections</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-slate-900">{stats.resources}</p>
            <p className="text-xs text-slate-500">Resources</p>
          </div>
        </div>
      )}

      {/* Recent Collections */}
      {recentCollections.length > 0 && (
        <div className="px-2 py-2">
          <p className="px-2 text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
            Recent
          </p>
          {recentCollections.map((collection) => (
            <Link
              key={collection.id}
              href={`/knowledge/${collection.id}`}
              className="flex items-center gap-2 px-2 py-1.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50 rounded transition-colors"
            >
              <FolderOpen className="w-4 h-4 text-slate-400" />
              <span className="truncate flex-1">{collection.name}</span>
              <span className="text-xs text-slate-400">{collection.resource_count}</span>
            </Link>
          ))}
        </div>
      )}

      {/* Empty State */}
      {recentCollections.length === 0 && (
        <div className="px-4 py-6 text-center">
          <FolderOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No collections yet</p>
          <Link
            href="/knowledge"
            className="text-sm text-indigo-600 hover:text-indigo-700 mt-1 inline-block"
          >
            Create one →
          </Link>
        </div>
      )}

      {/* Footer Link */}
      <Link
        href="/knowledge"
        className="flex items-center justify-center gap-1 px-4 py-2 text-sm text-slate-600 hover:text-indigo-600 hover:bg-slate-50 border-t border-slate-100"
      >
        View all
        <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

// Quick search component for use in headers/navbars
export function KnowledgeQuickSearch({ className = '' }: { className?: string }) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      window.location.href = `/knowledge/search?q=${encodeURIComponent(query)}`;
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="Search knowledge..."
        className={`w-full pl-9 pr-3 py-1.5 text-sm bg-slate-100 border rounded-lg transition-all ${
          focused 
            ? 'border-indigo-500 bg-white ring-2 ring-indigo-100' 
            : 'border-transparent hover:bg-slate-200'
        }`}
      />
    </form>
  );
}

export default KnowledgeWidget;
