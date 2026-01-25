'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, FileText, BookOpen, Clock, CheckCircle,
  AlertCircle, RefreshCw, Zap, ExternalLink, Copy, Check
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

  useEffect(() => {
    loadResource();
  }, [resourceId]);

  async function loadResource() {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch metadata and content in parallel
      const [metaRes, contentRes] = await Promise.all([
        fetch(`${API_BASE}/api/knowledge/resources/${resourceId}`),
        fetch(`${API_BASE}/api/knowledge/resources/${resourceId}/content`)
      ]);

      if (!metaRes.ok) {
        throw new Error('Resource not found');
      }

      const metaData = await metaRes.json();
      const contentData = await contentRes.json();

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

        {/* Actions Section */}
        {resource.index_status === 'completed' && (
          <div className="mt-6 bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-medium text-slate-900 mb-3">Analysis</h3>
            <p className="text-sm text-slate-600 mb-4">
              This resource has been indexed. You can view its parsed structure or run further analysis.
            </p>
            <div className="flex gap-3">
              <Link
                href={`/arguments?resource_id=${resource.id}`}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                <Zap className="w-4 h-4" />
                View Parsed Outline
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
