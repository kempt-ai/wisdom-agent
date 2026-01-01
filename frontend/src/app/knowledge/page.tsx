'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  FolderOpen, Plus, Search, BookOpen, FileText, 
  GraduationCap, Layers, MoreVertical, Trash2, Edit,
  RefreshCw, Database
} from 'lucide-react';
import { knowledgeApi, CollectionSummary, CollectionType, KnowledgeStats } from '@/lib/knowledge-api';

// Collection type icons and colors
const collectionTypeConfig: Record<CollectionType, { icon: any; color: string; bg: string }> = {
  research: { icon: Search, color: 'text-blue-600', bg: 'bg-blue-100' },
  fiction: { icon: BookOpen, color: 'text-purple-600', bg: 'bg-purple-100' },
  learning: { icon: GraduationCap, color: 'text-green-600', bg: 'bg-green-100' },
  general: { icon: Layers, color: 'text-gray-600', bg: 'bg-gray-100' },
};

export default function KnowledgeBasePage() {
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterType, setFilterType] = useState<CollectionType | 'all'>('all');

  // Load collections and stats
  useEffect(() => {
    loadData();
  }, [filterType]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [collectionsData, statsData] = await Promise.all([
        knowledgeApi.listCollections(undefined, filterType === 'all' ? undefined : filterType),
        knowledgeApi.getStats(),
      ]);
      setCollections(collectionsData);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteCollection(id: number, name: string) {
    if (!confirm(`Delete "${name}" and all its resources? This cannot be undone.`)) {
      return;
    }
    try {
      await knowledgeApi.deleteCollection(id);
      setCollections(collections.filter(c => c.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete');
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Database className="w-6 h-6 text-indigo-600" />
              <h1 className="text-xl font-semibold text-slate-900">Knowledge Base</h1>
            </div>
            <div className="flex items-center gap-3">
              <Link 
                href="/knowledge/search"
                className="flex items-center gap-2 px-3 py-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <Search className="w-4 h-4" />
                <span className="hidden sm:inline">Search</span>
              </Link>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>New Collection</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard label="Collections" value={stats.collections} icon={FolderOpen} />
            <StatCard label="Resources" value={stats.resources} icon={FileText} />
            <StatCard label="Total Tokens" value={formatNumber(stats.total_tokens)} icon={Layers} />
            <StatCard 
              label="Indexing Cost" 
              value={`$${stats.total_indexing_cost.toFixed(2)}`} 
              icon={Database} 
            />
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          <FilterTab 
            active={filterType === 'all'} 
            onClick={() => setFilterType('all')}
            label="All"
          />
          <FilterTab 
            active={filterType === 'research'} 
            onClick={() => setFilterType('research')}
            label="Research"
            icon={Search}
          />
          <FilterTab 
            active={filterType === 'fiction'} 
            onClick={() => setFilterType('fiction')}
            label="Fiction"
            icon={BookOpen}
          />
          <FilterTab 
            active={filterType === 'learning'} 
            onClick={() => setFilterType('learning')}
            label="Learning"
            icon={GraduationCap}
          />
          <FilterTab 
            active={filterType === 'general'} 
            onClick={() => setFilterType('general')}
            label="General"
            icon={Layers}
          />
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
            <span className="ml-2 text-slate-600">Loading...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
            <button 
              onClick={loadData}
              className="mt-2 text-red-600 hover:text-red-800 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && collections.length === 0 && (
          <div className="text-center py-12">
            <FolderOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h2 className="text-xl font-medium text-slate-700 mb-2">No collections yet</h2>
            <p className="text-slate-500 mb-6">
              Create your first collection to start organizing your knowledge.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
              Create Collection
            </button>
          </div>
        )}

        {/* Collections Grid */}
        {!loading && collections.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {collections.map((collection) => (
              <CollectionCard
                key={collection.id}
                collection={collection}
                onDelete={() => handleDeleteCollection(collection.id, collection.name)}
              />
            ))}
          </div>
        )}
      </main>

      {/* Create Collection Modal */}
      {showCreateModal && (
        <CreateCollectionModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(newCollection) => {
            setCollections([...collections, {
              id: newCollection.id,
              name: newCollection.name,
              collection_type: newCollection.collection_type,
              resource_count: 0,
              updated_at: newCollection.updated_at,
            }]);
            setShowCreateModal(false);
          }}
        />
      )}
    </div>
  );
}

// Stat Card Component
function StatCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: any }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-50 rounded-lg">
          <Icon className="w-5 h-5 text-indigo-600" />
        </div>
        <div>
          <p className="text-2xl font-semibold text-slate-900">{value}</p>
          <p className="text-sm text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

// Filter Tab Component
function FilterTab({ active, onClick, label, icon: Icon }: { 
  active: boolean; 
  onClick: () => void; 
  label: string;
  icon?: any;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
        active 
          ? 'bg-indigo-600 text-white' 
          : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
      }`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {label}
    </button>
  );
}

// Collection Card Component
function CollectionCard({ collection, onDelete }: { 
  collection: CollectionSummary; 
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const config = collectionTypeConfig[collection.collection_type] || collectionTypeConfig.general;
  const Icon = config.icon;

  return (
    <div className="bg-white rounded-lg border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all">
      <Link href={`/knowledge/${collection.id}`} className="block p-5">
        <div className="flex items-start justify-between">
          <div className={`p-2 rounded-lg ${config.bg}`}>
            <Icon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div className="relative">
            <button
              onClick={(e) => {
                e.preventDefault();
                setShowMenu(!showMenu);
              }}
              className="p-1 text-slate-400 hover:text-slate-600 rounded"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
            {showMenu && (
              <div className="absolute right-0 mt-1 w-36 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-10">
                <Link
                  href={`/knowledge/${collection.id}/edit`}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Edit className="w-4 h-4" />
                  Edit
                </Link>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    setShowMenu(false);
                    onDelete();
                  }}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
        <h3 className="mt-3 font-medium text-slate-900 truncate">{collection.name}</h3>
        <p className="mt-1 text-sm text-slate-500">
          {collection.resource_count} resource{collection.resource_count !== 1 ? 's' : ''}
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Updated {formatDate(collection.updated_at)}
        </p>
      </Link>
    </div>
  );
}

// Create Collection Modal
function CreateCollectionModal({ onClose, onCreated }: {
  onClose: () => void;
  onCreated: (collection: any) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<CollectionType>('general');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const collection = await knowledgeApi.createCollection({
        name: name.trim(),
        description: description.trim() || undefined,
        collection_type: type,
      });
      onCreated(collection);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create collection');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Create Collection</h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., AI Ethics Research"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this collection about?"
                rows={2}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(collectionTypeConfig) as CollectionType[]).map((t) => {
                  const config = collectionTypeConfig[t];
                  const Icon = config.icon;
                  return (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setType(t)}
                      className={`flex items-center gap-2 p-3 rounded-lg border transition-colors ${
                        type === t 
                          ? 'border-indigo-500 bg-indigo-50' 
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${config.color}`} />
                      <span className="text-sm capitalize">{t}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Utility functions
function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}
