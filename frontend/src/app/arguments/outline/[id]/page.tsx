'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, ChevronDown, ChevronRight, FileText, Quote,
  BarChart2, MessageSquare, CheckCircle, AlertCircle,
  Clock, ExternalLink, Cpu
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface OutlineNode {
  id: string;
  node_type: 'argument' | 'claim' | 'evidence';
  title: string;
  content?: string;
  claim_type?: 'factual' | 'interpretive' | 'prescriptive';
  verification_status?: 'verified' | 'disputed' | 'unverified';
  source_url?: string;
  children?: OutlineNode[];
  metadata?: Record<string, any>;
}

interface ParsedOutline {
  parsed_resource_id: number;
  resource_id: number;
  resource_name: string;
  main_thesis?: string;
  summary?: string;
  outline: OutlineNode[];
  total_claims: number;
  total_evidence: number;
  verified_claims: number;
  parsed_at: string;
  sources_cited: string[];
  // Model info (added)
  parser_model?: string;
  parse_level?: string;
}

interface ParsedResource {
  id: number;
  resource_id: number;
  parser_model: string;
  parser_version: string;
  parse_level?: string;
  parsing_cost_dollars: number;
  parsed_at: string;
}

// Icon mapping for evidence types
const evidenceIcons: Record<string, any> = {
  statistic: BarChart2,
  quote: Quote,
  citation: FileText,
  example: MessageSquare,
  data: BarChart2,
  testimony: MessageSquare,
};

// Claim type colors
const claimTypeColors: Record<string, string> = {
  factual: 'bg-blue-50 text-blue-700 border-blue-200',
  interpretive: 'bg-purple-50 text-purple-700 border-purple-200',
  prescriptive: 'bg-amber-50 text-amber-700 border-amber-200',
};

/** Returns true if `node` or any of its descendants has the given id */
function containsNodeId(node: OutlineNode, id: string): boolean {
  if (node.id === id) return true;
  return (node.children || []).some((child) => containsNodeId(child, id));
}

function OutlineNodeComponent({
  node,
  depth = 0,
  highlightId,
}: {
  node: OutlineNode;
  depth?: number;
  highlightId?: string;
}) {
  const hasChildren = node.children && node.children.length > 0;
  const isHighlighted = !!highlightId && node.id === highlightId;
  const ancestorOfHighlight = !!highlightId && !isHighlighted && containsNodeId(node, highlightId);

  // Auto-expand if this node contains the highlighted target
  const [expanded, setExpanded] = useState(depth < 2 || ancestorOfHighlight);

  // Fade-out highlight: start lit, turn off after 2.5 s
  const [lit, setLit] = useState(isHighlighted);
  const nodeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isHighlighted) return;
    // Scroll into view after a brief tick so the tree has rendered
    const scrollTimer = setTimeout(() => {
      nodeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 150);
    // Fade out after 2.5 s
    const fadeTimer = setTimeout(() => setLit(false), 2500);
    return () => { clearTimeout(scrollTimer); clearTimeout(fadeTimer); };
  }, [isHighlighted]);

  const EvidenceIcon = node.node_type === 'evidence'
    ? evidenceIcons[node.title.replace(/[\[\]]/g, '').toLowerCase()] || FileText
    : null;

  return (
    <div className={`${depth > 0 ? 'ml-4 border-l-2 border-slate-100 pl-4' : ''}`}>
      <div
        ref={isHighlighted ? nodeRef : undefined}
        className={`flex items-start gap-2 py-2 rounded-lg transition-colors duration-1000 ${
          hasChildren ? 'cursor-pointer' : ''
        } ${lit ? 'bg-amber-50 ring-2 ring-amber-300 px-2' : ''}`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand/collapse toggle */}
        {hasChildren && (
          <button className="mt-1 text-slate-400 hover:text-slate-600">
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        )}
        {!hasChildren && <div className="w-4" />}

        {/* Node content */}
        <div className="flex-1">
          {node.node_type === 'evidence' ? (
            <div className={`flex items-start gap-2 rounded-lg p-3 ${lit ? 'bg-amber-50' : 'bg-slate-50'}`}>
              {EvidenceIcon && <EvidenceIcon className="w-4 h-4 text-slate-400 mt-0.5" />}
              <div>
                <span className="text-xs text-slate-500 uppercase">{node.title}</span>
                <p className="text-sm text-slate-700">{node.content}</p>
                {node.source_url && (
                  <a
                    href={node.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-600 hover:underline flex items-center gap-1 mt-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Source <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-slate-900">{node.title}</span>
                {node.claim_type && (
                  <span className={`px-2 py-0.5 rounded text-xs border ${claimTypeColors[node.claim_type]}`}>
                    {node.claim_type}
                  </span>
                )}
                {node.verification_status === 'verified' && (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                )}
                {node.verification_status === 'disputed' && (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
              </div>
              {node.content && node.content !== node.title && (
                <p className="text-sm text-slate-600 mt-1">{node.content}</p>
              )}
              {node.metadata?.context && (
                <p className="text-xs text-slate-400 mt-1 italic">{node.metadata.context}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="mt-1">
          {node.children!.map((child, i) => (
            <OutlineNodeComponent key={child.id || i} node={child} depth={depth + 1} highlightId={highlightId} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function OutlinePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const parsedId = Number(params.id);
  const highlightId = searchParams.get('highlight') ?? undefined;
  
  const [outline, setOutline] = useState<ParsedOutline | null>(null);
  const [parseMeta, setParseMeta] = useState<ParsedResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    loadOutline();
  }, [parsedId]);
  
  async function loadOutline() {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch outline directly using the parsed resource ID
      // This endpoint returns the outline for THIS SPECIFIC parse
      const outlineRes = await fetch(
        `${API_BASE}/api/arguments/parsed/${parsedId}/outline`
      );
      
      if (!outlineRes.ok) {
        if (outlineRes.status === 404) {
          throw new Error('Parsed resource not found');
        }
        throw new Error('Failed to load outline');
      }
      
      const outlineData = await outlineRes.json();
      setOutline(outlineData);
      
      // The outline response now includes parser_model and parse_level
      setParseMeta({
        id: outlineData.parsed_resource_id,
        resource_id: outlineData.resource_id,
        parser_model: outlineData.parser_model || 'unknown',
        parser_version: '',
        parse_level: outlineData.parse_level || 'standard',
        parsing_cost_dollars: 0,
        parsed_at: outlineData.parsed_at
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load outline');
    } finally {
      setLoading(false);
    }
  }
  
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }
  
  if (error || !outline) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-700 mb-4">{error || 'Outline not found'}</p>
          <Link href="/knowledge" className="text-indigo-600 hover:underline">
            ← Knowledge Base
          </Link>
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
            <div className="flex items-center gap-2">
              <Link
                href={`/knowledge/resource/${outline.resource_id}`}
                className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="text-sm">Resource</span>
              </Link>
              <span className="text-slate-300">/</span>
              <div>
                <h1 className="text-lg font-semibold text-slate-900 truncate max-w-md">
                  {outline.resource_name}
                </h1>
                <div className="flex items-center gap-3 text-sm text-slate-500">
                  <span>{outline.total_claims} claims</span>
                  <span>·</span>
                  <span>{outline.total_evidence} evidence</span>
                  {outline.verified_claims > 0 && (
                    <>
                      <span>·</span>
                      <span className="text-green-600">{outline.verified_claims} verified</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            
            {/* Model info badge */}
            {parseMeta && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-full text-sm">
                <Cpu className="w-4 h-4 text-slate-400" />
                <span className="text-slate-600">
                  {parseMeta.parser_model.split('/').pop()?.split('-').slice(0, 3).join('-')}
                </span>
                {parseMeta.parse_level && (
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    parseMeta.parse_level === 'full' ? 'bg-purple-100 text-purple-700' :
                    parseMeta.parse_level === 'light' ? 'bg-green-100 text-green-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {parseMeta.parse_level}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </header>
      
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Highlight banner */}
        {highlightId && (
          <div className="mb-4 flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            <span className="font-medium">Linked from evidence</span>
            <span className="text-amber-600">— the highlighted node is scrolled into view below.</span>
          </div>
        )}

        {/* Thesis & Summary */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
          {outline.main_thesis && (
            <div className="mb-4">
              <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2">
                Main Thesis
              </h2>
              <p className="text-lg text-slate-900">{outline.main_thesis}</p>
            </div>
          )}
          
          {outline.summary && (
            <div>
              <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2">
                Summary
              </h2>
              <p className="text-slate-700">{outline.summary}</p>
            </div>
          )}
        </div>
        
        {/* Argument Outline */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">
            Argument Structure
          </h2>
          
          {outline.outline.length > 0 ? (
            <div className="space-y-2">
              {outline.outline.map((node, i) => (
                <OutlineNodeComponent key={node.id || i} node={node} highlightId={highlightId} />
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-center py-8">
              No arguments extracted from this resource.
            </p>
          )}
        </div>
        
        {/* Sources Cited */}
        {outline.sources_cited && outline.sources_cited.length > 0 && (
          <div className="mt-6 bg-white rounded-lg border border-slate-200 p-6">
            <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">
              Sources Cited
            </h2>
            <ul className="space-y-2">
              {outline.sources_cited.map((source, i) => (
                <li key={i}>
                  <a 
                    href={source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-indigo-600 hover:underline flex items-center gap-1"
                  >
                    {source}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Metadata footer */}
        <div className="mt-6 flex items-center justify-between text-sm text-slate-400">
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            Parsed {new Date(outline.parsed_at).toLocaleString()}
          </div>
          <Link
            href={`/knowledge/resource/${outline.resource_id}`}
            className="text-indigo-600 hover:underline"
          >
            View original resource →
          </Link>
        </div>
      </main>
    </div>
  );
}
