'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, Plus, Search, FileText, BookOpen, Link as LinkIcon,
  Upload, RefreshCw, Trash2, MoreVertical, Zap, CheckCircle,
  AlertCircle, Clock, ExternalLink, ChevronDown
} from 'lucide-react';
import { 
  knowledgeApi, Collection, ResourceSummary, Resource,
  IndexLevel, IndexStatus, ResourceType, IndexEstimate
} from '@/lib/knowledge-api';

// Resource type icons
const resourceTypeIcons: Record<ResourceType, any> = {
  document: FileText,
  fiction_book: BookOpen,
  nonfiction_book: BookOpen,
  article: FileText,
  learning_module: FileText,
};

// Index status config
const indexStatusConfig: Record<IndexStatus, { icon: any; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-slate-400', label: 'Not indexed' },
  indexing: { icon: RefreshCw, color: 'text-blue-500', label: 'Indexing...' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Indexed' },
  failed: { icon: AlertCircle, color: 'text-red-500', label: 'Failed' },
};

export default function CollectionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const collectionId = Number(params.id);

  const [collection, setCollection] = useState<Collection | null>(null);
  const [resources, setResources] = useState<ResourceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addMode, setAddMode] = useState<'url' | 'text' | 'upload'>('url');

  useEffect(() => {
    loadData();
  }, [collectionId]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [collectionData, resourcesData] = await Promise.all([
        knowledgeApi.getCollection(collectionId),
        knowledgeApi.listResources(collectionId),
      ]);
      setCollection(collectionData);
      setResources(resourcesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteResource(id: number, name: string) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await knowledgeApi.deleteResource(id);
      setResources(resources.filter(r => r.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete');
    }
  }

  function handleResourceAdded(resource: Resource) {
    setResources([
      {
        id: resource.id,
        name: resource.name,
        resource_type: resource.resource_type,
        token_count: resource.token_count,
        index_level: resource.index_level,
        index_status: resource.index_status,
        updated_at: resource.updated_at,
      },
      ...resources,
    ]);
    setShowAddModal(false);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-700">{error || 'Collection not found'}</p>
          <Link href="/knowledge" className="text-indigo-600 hover:underline mt-2 inline-block">
            ← Back to Knowledge Base
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link 
                href="/knowledge"
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">{collection.name}</h1>
                <p className="text-sm text-slate-500">
                  {collection.resource_count} resources · {formatTokens(collection.total_tokens)} tokens
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
              Add Resource
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Description */}
        {collection.description && (
          <p className="text-slate-600 mb-6">{collection.description}</p>
        )}

        {/* Empty State */}
        {resources.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-slate-700 mb-2">No resources yet</h2>
            <p className="text-slate-500 mb-6">
              Add your first resource to start building your knowledge.
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => { setAddMode('url'); setShowAddModal(true); }}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                <LinkIcon className="w-4 h-4" />
                Add from URL
              </button>
              <button
                onClick={() => { setAddMode('upload'); setShowAddModal(true); }}
                className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
              >
                <Upload className="w-4 h-4" />
                Upload File
              </button>
            </div>
          </div>
        )}

        {/* Resources List */}
        {resources.length > 0 && (
          <div className="space-y-3">
            {resources.map((resource) => (
              <ResourceCard
                key={resource.id}
                resource={resource}
                collectionId={collectionId}
                onDelete={() => handleDeleteResource(resource.id, resource.name)}
                onRefresh={loadData}
              />
            ))}
          </div>
        )}
      </main>

      {/* Add Resource Modal */}
      {showAddModal && (
        <AddResourceModal
          collectionId={collectionId}
          initialMode={addMode}
          onClose={() => setShowAddModal(false)}
          onAdded={handleResourceAdded}
        />
      )}
    </div>
  );
}

// Resource Card Component
function ResourceCard({ 
  resource, 
  collectionId,
  onDelete, 
  onRefresh 
}: { 
  resource: ResourceSummary;
  collectionId: number;
  onDelete: () => void;
  onRefresh: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [showIndexModal, setShowIndexModal] = useState(false);
  const [indexing, setIndexing] = useState(false);

  const Icon = resourceTypeIcons[resource.resource_type] || FileText;
  const statusConfig = indexStatusConfig[resource.index_status];
  const StatusIcon = statusConfig.icon;

  return (
    <>
      <div className="bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-colors">
        <div className="p-4 flex items-center gap-4">
          {/* Icon */}
          <div className="p-2 bg-slate-100 rounded-lg">
            <Icon className="w-5 h-5 text-slate-600" />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-slate-900 truncate">{resource.name}</h3>
            <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
              <span>{formatTokens(resource.token_count)} tokens</span>
              <span>·</span>
              <span className="capitalize">{resource.resource_type.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Index Status */}
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-1 text-sm ${statusConfig.color}`}>
              <StatusIcon className={`w-4 h-4 ${resource.index_status === 'indexing' ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{statusConfig.label}</span>
            </div>

            {/* Index Button */}
            {resource.index_status !== 'indexing' && (
              <button
                onClick={() => setShowIndexModal(true)}
                className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg"
                title="Index resource"
              >
                <Zap className="w-4 h-4" />
              </button>
            )}

            {/* Menu */}
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                <MoreVertical className="w-4 h-4" />
              </button>
              {showMenu && (
                <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-10">
                  <button
                    onClick={() => { setShowMenu(false); onRefresh(); }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </button>
                  <button
                    onClick={() => { setShowMenu(false); onDelete(); }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Index Level Badge */}
        {resource.index_level !== 'none' && (
          <div className="px-4 pb-3">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
              resource.index_level === 'full' ? 'bg-purple-100 text-purple-700' :
              resource.index_level === 'standard' ? 'bg-blue-100 text-blue-700' :
              'bg-slate-100 text-slate-700'
            }`}>
              {resource.index_level} index
            </span>
          </div>
        )}
      </div>

      {/* Index Modal */}
      {showIndexModal && (
        <IndexResourceModal
          resourceId={resource.id}
          resourceName={resource.name}
          tokenCount={resource.token_count}
          currentLevel={resource.index_level}
          onClose={() => setShowIndexModal(false)}
          onIndexed={onRefresh}
        />
      )}
    </>
  );
}

// Add Resource Modal
function AddResourceModal({ 
  collectionId, 
  initialMode = 'url',
  onClose, 
  onAdded 
}: {
  collectionId: number;
  initialMode?: 'url' | 'text' | 'upload';
  onClose: () => void;
  onAdded: (resource: Resource) => void;
}) {
  const [mode, setMode] = useState<'url' | 'text' | 'upload'>(initialMode);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // URL mode state
  const [url, setUrl] = useState('');
  const [urlPreview, setUrlPreview] = useState<any>(null);
  const [previewing, setPreviewing] = useState(false);

  // Text mode state
  const [name, setName] = useState('');
  const [content, setContent] = useState('');

  // Upload mode state
  const [file, setFile] = useState<File | null>(null);

  async function handlePreviewUrl() {
    if (!url.trim()) return;
    
    setPreviewing(true);
    setUrlPreview(null);
    setError('');
    
    try {
      const preview = await knowledgeApi.previewUrl(url.trim());
      setUrlPreview(preview);
      if (!preview.success) {
        setError(preview.error_message || 'Failed to fetch URL');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSubmit() {
    setLoading(true);
    setError('');

    try {
      let resource: Resource;

      if (mode === 'url') {
        if (!url.trim()) {
          setError('URL is required');
          setLoading(false);
          return;
        }
        const result = await knowledgeApi.addResourceFromUrl(collectionId, {
          url: url.trim(),
          name: urlPreview?.title || undefined,
        });
        resource = result.resource;
      } else if (mode === 'text') {
        if (!name.trim() || !content.trim()) {
          setError('Name and content are required');
          setLoading(false);
          return;
        }
        resource = await knowledgeApi.addResourceText(collectionId, {
          name: name.trim(),
          content: content.trim(),
        });
      } else {
        if (!file) {
          setError('Please select a file');
          setLoading(false);
          return;
        }
        resource = await knowledgeApi.uploadResource(collectionId, file);
      }

      onAdded(resource);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add resource');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">Add Resource</h2>

          {/* Mode Tabs */}
          <div className="flex gap-1 p-1 bg-slate-100 rounded-lg mb-6">
            <ModeTab 
              active={mode === 'url'} 
              onClick={() => setMode('url')}
              icon={LinkIcon}
              label="From URL"
            />
            <ModeTab 
              active={mode === 'text'} 
              onClick={() => setMode('text')}
              icon={FileText}
              label="Paste Text"
            />
            <ModeTab 
              active={mode === 'upload'} 
              onClick={() => setMode('upload')}
              icon={Upload}
              label="Upload"
            />
          </div>

          {/* URL Mode */}
          {mode === 'url' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  URL
                </label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/article"
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    onClick={handlePreviewUrl}
                    disabled={previewing || !url.trim()}
                    className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 disabled:opacity-50"
                  >
                    {previewing ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Preview'}
                  </button>
                </div>
              </div>

              {/* URL Preview */}
              {urlPreview && urlPreview.success && (
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <h4 className="font-medium text-slate-900">{urlPreview.title || 'Untitled'}</h4>
                  {urlPreview.author && (
                    <p className="text-sm text-slate-600 mt-1">By {urlPreview.author}</p>
                  )}
                  <div className="flex gap-4 mt-2 text-sm text-slate-500">
                    <span>{urlPreview.word_count.toLocaleString()} words</span>
                    <span>{urlPreview.token_estimate?.toLocaleString()} tokens</span>
                  </div>
                  {urlPreview.content_preview && (
                    <p className="text-sm text-slate-600 mt-3 line-clamp-3">
                      {urlPreview.content_preview}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Text Mode */}
          {mode === 'text' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Document title"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Content *
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste your content here..."
                  rows={8}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
                {content && (
                  <p className="text-sm text-slate-500 mt-1">
                    ~{Math.ceil(content.length / 4).toLocaleString()} tokens
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Upload Mode */}
          {mode === 'upload' && (
            <div className="space-y-4">
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  file ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300 hover:border-slate-400'
                }`}
              >
                <input
                  type="file"
                  accept=".txt,.md,.pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className={`w-8 h-8 mx-auto mb-2 ${file ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {file ? (
                    <p className="text-indigo-600 font-medium">{file.name}</p>
                  ) : (
                    <>
                      <p className="text-slate-600">Click to upload or drag and drop</p>
                      <p className="text-sm text-slate-400 mt-1">TXT, MD, PDF</p>
                    </>
                  )}
                </label>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Adding...' : 'Add Resource'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Mode Tab Component
function ModeTab({ active, onClick, icon: Icon, label }: {
  active: boolean;
  onClick: () => void;
  icon: any;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
        active 
          ? 'bg-white text-slate-900 shadow-sm' 
          : 'text-slate-600 hover:text-slate-900'
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}

// Index Resource Modal
function IndexResourceModal({
  resourceId,
  resourceName,
  tokenCount,
  currentLevel,
  onClose,
  onIndexed,
}: {
  resourceId: number;
  resourceName: string;
  tokenCount: number;
  currentLevel: IndexLevel;
  onClose: () => void;
  onIndexed: () => void;
}) {
  const [level, setLevel] = useState<IndexLevel>('standard');
  const [estimate, setEstimate] = useState<IndexEstimate | null>(null);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadEstimate();
  }, [level]);

  async function loadEstimate() {
    setLoading(true);
    setError('');
    try {
      const est = await knowledgeApi.getIndexEstimate(resourceId, level);
      setEstimate(est);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get estimate');
    } finally {
      setLoading(false);
    }
  }

  async function handleIndex() {
    if (!estimate?.can_afford) {
      setError('Insufficient budget');
      return;
    }

    setIndexing(true);
    setError('');

    try {
      await knowledgeApi.indexResource(resourceId, level, true);
      onIndexed();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Indexing failed');
    } finally {
      setIndexing(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Index Resource</h2>
          <p className="text-slate-600 text-sm mb-6">{resourceName}</p>

          {/* Level Selection */}
          <div className="space-y-3 mb-6">
            <IndexLevelOption
              level="light"
              selected={level === 'light'}
              onClick={() => setLevel('light')}
              description="Summary + key quotes"
              tokenRatio="~5%"
            />
            <IndexLevelOption
              level="standard"
              selected={level === 'standard'}
              onClick={() => setLevel('standard')}
              description="Structured breakdown + search"
              tokenRatio="~20%"
            />
            <IndexLevelOption
              level="full"
              selected={level === 'full'}
              onClick={() => setLevel('full')}
              description="Complete analysis + characters"
              tokenRatio="~120%"
            />
          </div>

          {/* Estimate */}
          {loading && (
            <div className="flex items-center justify-center py-4">
              <RefreshCw className="w-5 h-5 text-indigo-600 animate-spin" />
            </div>
          )}

          {estimate && !loading && (
            <div className="bg-slate-50 rounded-lg p-4 mb-6">
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Estimated cost</span>
                <span className="text-xl font-semibold text-slate-900">
                  ${estimate.estimated_cost.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between items-center mt-2 text-sm">
                <span className="text-slate-500">Budget remaining</span>
                <span className={estimate.can_afford ? 'text-green-600' : 'text-red-600'}>
                  ${estimate.budget_remaining.toFixed(2)}
                </span>
              </div>
              {!estimate.can_afford && (
                <p className="text-sm text-red-600 mt-2">
                  {estimate.warning_message || 'Insufficient budget'}
                </p>
              )}
            </div>
          )}

          {error && (
            <p className="text-sm text-red-600 mb-4">{error}</p>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleIndex}
              disabled={indexing || loading || !estimate?.can_afford}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {indexing ? 'Indexing...' : 'Index Now'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Index Level Option
function IndexLevelOption({
  level,
  selected,
  onClick,
  description,
  tokenRatio,
}: {
  level: IndexLevel;
  selected: boolean;
  onClick: () => void;
  description: string;
  tokenRatio: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors ${
        selected
          ? 'border-indigo-500 bg-indigo-50'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="text-left">
        <p className={`font-medium capitalize ${selected ? 'text-indigo-700' : 'text-slate-900'}`}>
          {level}
        </p>
        <p className="text-sm text-slate-500">{description}</p>
      </div>
      <span className={`text-sm ${selected ? 'text-indigo-600' : 'text-slate-400'}`}>
        {tokenRatio}
      </span>
    </button>
  );
}

// Utility functions
function formatTokens(tokens: number): string {
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
  return tokens.toString();
}
