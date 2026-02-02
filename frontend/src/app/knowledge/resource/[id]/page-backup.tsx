'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, FileText, BookOpen, Clock, CheckCircle,
  AlertCircle, RefreshCw, Zap, ExternalLink, Copy, Check,
  ListTree, Loader2, DollarSign
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Resource {
  id: number;
  name: string;
  description?: string;
  resource_type: string;
  collection_id: number;
  source_url?: string;
  token_count: number;
  index_level: string;
  index_status: string;
  created_at: string;
  updated_at: string;
}

interface ResourceContent {
  resource_id: number;
  name: string;
  content: string | null;
  token_count: number;
  message?: string;
}

interface ParseSummary {
  id: number;
  parse_level: string;
  parser_model: string;
  parsed_at: string;
  main_thesis: string | null;
  cost_dollars: number;
  claim_count: number;
}

interface ParseEstimate {
  resource_id: number;
  resource_name: string;
  token_count: number;
  estimated_parsing_tokens: number;
  estimated_cost_dollars: number;
  model_id: string;
  already_parsed: boolean;
}

interface ModelInfo {
  id: string;
  name: string;
  tier: string;
  description: string;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
  context_window: number;
  best_for: string[];
}

interface ProviderInfo {
  name: string;
  default_model: string;
  models: ModelInfo[];
}

interface ModelsResponse {
  active_provider: string;
  providers: ProviderInfo[];
  error?: string;
}

// Index status display config
const indexStatusConfig: Record<string, { icon: any; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-slate-400', label: 'Not indexed' },
  indexing: { icon: RefreshCw, color: 'text-blue-500', label: 'Indexing...' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Indexed' },
  failed: { icon: AlertCircle, color: 'text-red-500', label: 'Failed' },
};

export default function ResourceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const resourceId = Number(params.id);

  const [resource, setResource] = useState<Resource | null>(null);

  const [content, setContent] = useState<ResourceContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  
  // Parse-related state
  const [parses, setParses] = useState<ParseSummary[]>([]);
  const [selectedLevel, setSelectedLevel] = useState<string>('standard');
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [estimate, setEstimate] = useState<ParseEstimate | null>(null);
  const [showContent, setShowContent] = useState(false);
  const [estimating, setEstimating] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    loadResource();
    loadAvailableModels();
  }, [resourceId]);

  async function loadAvailableModels() {
    try {
      const response = await fetch(`${API_BASE}/api/arguments/models`);
      if (response.ok) {
        const data: ModelsResponse = await response.json();
        if (data.providers && data.providers.length > 0) {
          setProviders(data.providers);
          // Set defaults from active provider
          const activeProvider = data.providers.find(p => p.name === data.active_provider) || data.providers[0];
          setSelectedProvider(activeProvider.name);
          setSelectedModel(activeProvider.default_model);
        }
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  }

    async function loadResource() {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch metadata, content, and existing parses in parallel
      const [metaRes, contentRes, parsesRes] = await Promise.all([
        fetch(`${API_BASE}/api/knowledge/resources/${resourceId}`),
        fetch(`${API_BASE}/api/knowledge/resources/${resourceId}/content`),
        fetch(`${API_BASE}/api/arguments/resource/${resourceId}/parses`)
      ]);

      if (!metaRes.ok) {
        throw new Error('Resource not found');
      }

      const metaData = await metaRes.json();
      const contentData = await contentRes.json();
      
      // Parses might not exist yet, that's ok
      if (parsesRes.ok) {
        const parsesData = await parsesRes.json();
        setParses(parsesData.parses || []);
      }

      setResource(metaData);
      setContent(contentData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load resource');
    } finally {
      setLoading(false);
    }
  }

  async function copyContent() {
    if (!content?.content) return;
    
    try {
      await navigator.clipboard.writeText(content.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
} catch (err) {
      console.error('Failed to copy:', err);
    }
  }

  // Fetch cost estimate when model or level changes
  useEffect(() => {
    if (resource && content?.content && selectedModel) {
      fetchEstimate();
    }
  }, [selectedModel, selectedLevel, resource?.id]);

  async function fetchEstimate() {
    if (!resource) return;
    
    setEstimating(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/arguments/parse/estimate?resource_id=${resourceId}&model_id=${encodeURIComponent(selectedModel)}`,
        { method: 'POST' }
      );
      
      if (response.ok) {
        const data = await response.json();
        setEstimate(data);
      }
    } catch (err) {
      console.error('Failed to fetch estimate:', err);
    } finally {
      setEstimating(false);
    }
  }

  async function parseResource() {
    setParsing(true);
    setParseError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/arguments/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_id: resourceId,
          parse_level: selectedLevel,
          model_id: selectedModel,
          force_reparse: false,
          extract_claims: true
        })
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || 'Parsing failed');
      }
      
      if (!result.success) {
        if (result.error_message?.includes('Already parsed')) {
          setParseError(`Already parsed at ${selectedLevel} level. Use a different level or view existing.`);
        } else {
          throw new Error(result.error_message || 'Parsing failed');
        }
      } else {
        // Reload parses list
        const parsesRes = await fetch(`${API_BASE}/api/arguments/resource/${resourceId}/parses`);
        if (parsesRes.ok) {
          const parsesData = await parsesRes.json();
          setParses(parsesData.parses || []);
        }
        setParseError(null);
      }
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Failed to parse resource');
    } finally {
      setParsing(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
        <span className="ml-2 text-slate-600">Loading resource...</span>
      </div>
    );
  }

  if (error || !resource) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-700 mb-4">{error || 'Resource not found'}</p>
          <button
            onClick={() => router.back()}
            className="text-indigo-600 hover:underline"
          >
            ← Go back
          </button>
        </div>
      </div>
    );
  }

  const statusConfig = indexStatusConfig[resource.index_status] || indexStatusConfig.pending;
  const StatusIcon = statusConfig.icon;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-lg font-semibold text-slate-900 truncate max-w-md">
                  {resource.name}
                </h1>
                <div className="flex items-center gap-3 text-sm text-slate-500">
                  <span className="capitalize">{resource.resource_type.replace('_', ' ')}</span>
                  <span>·</span>
                  <span>{resource.token_count.toLocaleString()} tokens</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Index Status Badge */}
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
                resource.index_status === 'completed' ? 'bg-green-50' : 'bg-slate-100'
              }`}>
                <StatusIcon className={`w-4 h-4 ${statusConfig.color} ${
                  resource.index_status === 'indexing' ? 'animate-spin' : ''
                }`} />
                <span className={statusConfig.color}>{statusConfig.label}</span>
              </div>

              {/* Copy Button */}
              {content?.content && (
                <button
                  onClick={copyContent}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
                  title="Copy content"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 text-green-500" />
                      <span className="text-green-600">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span className="hidden sm:inline">Copy</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Metadata Card */}
        <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Collection</span>
              <Link 
                href={`/knowledge/${resource.collection_id}`}
                className="block text-indigo-600 hover:underline truncate"
              >
                View collection →
              </Link>
            </div>
            <div>
              <span className="text-slate-500">Type</span>
              <p className="text-slate-900 capitalize">{resource.resource_type.replace('_', ' ')}</p>
            </div>
            <div>
              <span className="text-slate-500">Index Level</span>
              <p className="text-slate-900 capitalize">{resource.index_level || 'None'}</p>
            </div>
            <div>
              <span className="text-slate-500">Created</span>
              <p className="text-slate-900">{new Date(resource.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          {resource.source_url && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <span className="text-sm text-slate-500">Source URL</span>
              <a 
                href={resource.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-indigo-600 hover:underline text-sm"
              >
                {resource.source_url}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {resource.description && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <span className="text-sm text-slate-500">Description</span>
              <p className="text-slate-700">{resource.description}</p>
            </div>
          )}
        </div>

        {/* Content Section */}
        <div className="bg-white rounded-lg border border-slate-200">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
            <h2 className="font-medium text-slate-900">Content</h2>
            {content?.token_count && (
              <span className="text-sm text-slate-500">
                {content.token_count.toLocaleString()} tokens
              </span>
            )}
          </div>
          
          <div className="p-4">
            {content?.content ? (
              <div className="prose prose-slate max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 bg-slate-50 p-4 rounded-lg overflow-x-auto">
                  {content.content}
                </pre>
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p>{content?.message || 'No content available'}</p>
              </div>
            )}
          </div>
        </div>

        {/* Argument Parsing Section */}
        <div className="mt-6 bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-medium text-slate-900 mb-3 flex items-center gap-2">
            <ListTree className="w-5 h-5 text-indigo-600" />
            Argument Parsing
          </h3>
          
          {/* Existing Parses */}
          {parses.length > 0 && (
            <div className="mb-4">
              <p className="text-sm text-slate-600 mb-2">Existing parses:</p>
              <div className="space-y-2">
                {parses.map((parse) => (
                  <Link
                    key={parse.id}
                    href={`/arguments/outline/${parse.id}`}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        parse.parse_level === 'full' ? 'bg-purple-100 text-purple-700' :
                        parse.parse_level === 'light' ? 'bg-green-100 text-green-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {parse.parse_level}
                      </span>
                      <span className="text-sm text-slate-700">
                        {parse.claim_count} claims
                      </span>
                      <span className="text-xs text-slate-400">
                        {parse.parser_model.split('-').slice(0, 2).join('-')}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {new Date(parse.parsed_at).toLocaleDateString()}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
          
          {/* Parse Controls */}
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              disabled={parsing}
            >
              <option value="light">Light (quick overview)</option>
              <option value="standard">Standard (balanced)</option>
              <option value="full">Full (comprehensive)</option>
            </select>
            
            {/* Provider Selection */}
            <select
              value={selectedProvider}
              onChange={(e) => {
                const newProvider = e.target.value;
                setSelectedProvider(newProvider);
                // Set default model for new provider
                const provider = providers.find(p => p.name === newProvider);
                if (provider) {
                  setSelectedModel(provider.default_model);
                }
              }}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              disabled={parsing || providers.length === 0}
            >
              {providers.map((provider) => (
                <option key={provider.name} value={provider.name}>
                  {provider.name.charAt(0).toUpperCase() + provider.name.slice(1)}
                </option>
              ))}
            </select>
            
            {/* Model Selection */}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[180px]"
              disabled={parsing || !selectedProvider}
            >
              {providers
                .find(p => p.name === selectedProvider)
                ?.models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.tier})
                  </option>
                ))}
            </select>
            
            <button
              onClick={parseResource}
              disabled={parsing || !content?.content || !selectedModel}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {parsing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Parsing...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Parse Arguments
                </>
              )}
            </button>
          </div>
          
          {/* Cost Estimate */}
          {estimate && (
            <div className="mt-3 flex items-center gap-2 text-sm">
              <DollarSign className="w-4 h-4 text-slate-400" />
              <span className="text-slate-600">
                Estimated cost: <span className="font-medium text-slate-900">
                  ${estimate.estimated_cost_dollars.toFixed(4)}
                </span>
                <span className="text-slate-400 ml-2">
                  (~{estimate.estimated_parsing_tokens.toLocaleString()} tokens)
                </span>
              </span>
              {estimating && <Loader2 className="w-3 h-3 animate-spin text-slate-400" />}
            </div>
          )}
          
          {/* Parse Error/Status */}
          {parseError && (
            <p className="mt-2 text-sm text-amber-600">{parseError}</p>
          )}
          
          {!content?.content && (
            <p className="mt-2 text-sm text-slate-500">
              No content available to parse. Try refreshing the resource.
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
