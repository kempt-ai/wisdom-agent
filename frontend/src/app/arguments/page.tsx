'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, GitBranch, FileText, ChevronRight, ChevronDown,
  CheckCircle, AlertCircle, RefreshCw, ExternalLink, Lightbulb,
  MessageSquare, BarChart3
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ArgumentNode {
  id: string;
  node_type: 'argument' | 'evidence';
  title: string;
  content: string;
  claim_type?: 'factual' | 'interpretive' | 'prescriptive' | null;
  verification_status?: string | null;
  source_url?: string | null;
  children: ArgumentNode[];
  metadata?: {
    context?: string;
    source_quote?: string | null;
    confidence?: number;
  };
}

interface ArgumentOutline {
  parsed_resource_id: number;
  resource_id: number;
  resource_name: string;
  main_thesis: string;
  summary: string;
  outline: ArgumentNode[];
  total_claims: number;
  total_evidence: number;
  verified_claims: number;
  parsed_at: string;
  sources_cited: string[];
}

// Claim type styling
const claimTypeConfig: Record<string, { color: string; bg: string; label: string }> = {
  factual: { color: 'text-blue-700', bg: 'bg-blue-100', label: 'Factual' },
  interpretive: { color: 'text-purple-700', bg: 'bg-purple-100', label: 'Interpretive' },
  prescriptive: { color: 'text-amber-700', bg: 'bg-amber-100', label: 'Prescriptive' },
};

export default function ArgumentsPage() {
  const searchParams = useSearchParams();
  const resourceId = searchParams.get('resource_id');

  const [outline, setOutline] = useState<ArgumentOutline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (resourceId) {
      loadOutline(Number(resourceId));
    } else {
      setLoading(false);
      setError('No resource specified');
    }
  }, [resourceId]);

  async function loadOutline(resId: number) {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/arguments/resource/${resId}/outline`);
      
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('This resource has not been parsed yet. Go back and index it first.');
        }
        throw new Error('Failed to load outline');
      }

      const data = await res.json();
      setOutline(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load outline');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
        <span className="ml-2 text-slate-600">Loading argument structure...</span>
      </div>
    );
  }

  if (error || !outline) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-700 mb-4">{error || 'Could not load outline'}</p>
          {resourceId && (
            <Link
              href={`/knowledge/resource/${resourceId}`}
              className="text-indigo-600 hover:underline"
            >
              ← Back to resource
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link
                href={`/knowledge/resource/${outline.resource_id}`}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-lg font-semibold text-slate-900 truncate max-w-lg">
                  {outline.resource_name}
                </h1>
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <GitBranch className="w-4 h-4" />
                  <span>Parsed Argument Structure</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Main Thesis Card */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white mb-6">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-6 h-6 flex-shrink-0 mt-1" />
            <div>
              <h2 className="text-sm font-medium text-indigo-100 uppercase tracking-wide mb-2">
                Main Thesis
              </h2>
              <p className="text-lg font-medium leading-relaxed">
                {outline.main_thesis}
              </p>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6">
          <h3 className="font-medium text-slate-900 mb-2 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-slate-400" />
            Summary
          </h3>
          <p className="text-slate-600">{outline.summary}</p>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-slate-200 p-4 text-center">
            <p className="text-2xl font-semibold text-slate-900">{outline.total_claims}</p>
            <p className="text-sm text-slate-500">Claims</p>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-4 text-center">
            <p className="text-2xl font-semibold text-slate-900">{outline.total_evidence}</p>
            <p className="text-sm text-slate-500">Evidence Items</p>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-4 text-center">
            <p className="text-2xl font-semibold text-slate-900">{outline.verified_claims}</p>
            <p className="text-sm text-slate-500">Verified</p>
          </div>
        </div>

        {/* Argument Tree */}
        <div className="bg-white rounded-lg border border-slate-200">
          <div className="px-4 py-3 border-b border-slate-200">
            <h3 className="font-medium text-slate-900 flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-slate-400" />
              Argument Structure
            </h3>
          </div>
          <div className="p-4">
            {outline.outline.length > 0 ? (
              <div className="space-y-3">
                {outline.outline.map((node) => (
                  <ArgumentNodeComponent key={node.id} node={node} depth={0} />
                ))}
              </div>
            ) : (
              <p className="text-slate-500 text-center py-8">
                No argument structure extracted
              </p>
            )}
          </div>
        </div>

        {/* Sources */}
        {outline.sources_cited.length > 0 && (
          <div className="bg-white rounded-lg border border-slate-200 mt-6">
            <div className="px-4 py-3 border-b border-slate-200">
              <h3 className="font-medium text-slate-900">Sources Cited</h3>
            </div>
            <div className="p-4">
              <ul className="space-y-2">
                {outline.sources_cited.map((source, idx) => (
                  <li key={idx} className="text-sm">
                    <a
                      href={source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:underline flex items-center gap-1"
                    >
                      {source}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Parsed Date */}
        <p className="text-sm text-slate-400 mt-6 text-center">
          Parsed on {new Date(outline.parsed_at).toLocaleDateString()} at{' '}
          {new Date(outline.parsed_at).toLocaleTimeString()}
        </p>
      </main>
    </div>
  );
}

// Recursive Argument Node Component
function ArgumentNodeComponent({ node, depth }: { node: ArgumentNode; depth: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  const isArgument = node.node_type === 'argument';
  const borderColor = isArgument ? 'border-indigo-300' : 'border-amber-300';
  const bgColor = isArgument ? 'bg-indigo-50' : 'bg-amber-50';

  const claimConfig = node.claim_type ? claimTypeConfig[node.claim_type] : null;

  return (
    <div className={`${depth > 0 ? 'ml-6' : ''}`}>
      <div
        className={`border-l-4 ${borderColor} ${bgColor} rounded-r-lg p-3 transition-all`}
      >
        {/* Header */}
        <div
          className="flex items-start gap-2 cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          {hasChildren && (
            <span className="mt-0.5 text-slate-400">
              {expanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </span>
          )}
          {!hasChildren && <span className="w-4" />}

          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-slate-900">{node.title}</h4>
              {claimConfig && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${claimConfig.bg} ${claimConfig.color}`}
                >
                  {claimConfig.label}
                </span>
              )}
              {node.verification_status === 'verified' && (
                <CheckCircle className="w-4 h-4 text-green-500" />
              )}
            </div>
            <p className="text-sm text-slate-600 mt-1">{node.content}</p>

            {/* Metadata */}
            {node.metadata?.context && (
              <p className="text-xs text-slate-400 mt-2 italic">
                Context: {node.metadata.context}
              </p>
            )}

            {/* Source URL */}
            {node.source_url && (
              <a
                href={node.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-600 hover:underline mt-1 inline-flex items-center gap-1"
                onClick={(e) => e.stopPropagation()}
              >
                Source <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="mt-2 space-y-2">
          {node.children.map((child) => (
            <ArgumentNodeComponent key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
