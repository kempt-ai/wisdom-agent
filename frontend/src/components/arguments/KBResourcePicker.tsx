'use client';

import { useState, useMemo } from 'react';
import {
  Search, Loader2, Database, X, ChevronLeft, ChevronDown, ChevronRight,
  FileText, Quote, BarChart2, BookOpen, MessageSquare,
} from 'lucide-react';
import { knowledgeApi, SearchResult } from '@/lib/knowledge-api';
import {
  argumentsApi, ResourceParse, OutlineNode, OutlineResponse,
} from '@/lib/arguments-api';

// ─── Exported types ──────────────────────────────────────────────

/** Data returned when a resource (and optionally a parsed item) is selected */
export interface KBSelection {
  id: number;
  name: string;
  source_url?: string;
  resource_type: string;
  collection_name: string;
  /** Text to auto-fill into key_quote */
  selectedText?: string;
  /** Title/label of what was selected (for context) */
  selectedTitle?: string;
  /** Parsed resource ID (links back to a specific parse run) */
  parsedResourceId?: number;
  /** Outline node ID (e.g. "claim-71" or "evidence-98") for "View in parse" */
  outlineNodeId?: string;
  /** Node type from the outline: 'argument' or 'evidence' */
  outlineNodeType?: 'argument' | 'evidence';
  /** Supporting evidence items collected from children of a parent claim node */
  supportingQuotes?: Array<{
    quote_type: string;
    content: string;
    outline_node_id?: string;
  }>;
}

interface KBResourcePickerProps {
  onSelect: (selection: KBSelection) => void;
  onCancel: () => void;
}

// ─── Styling maps ────────────────────────────────────────────────

const CLAIM_TYPE_STYLES: Record<string, { label: string; cls: string }> = {
  factual:       { label: 'Factual',       cls: 'bg-blue-50 text-blue-700' },
  interpretive:  { label: 'Interpretive',  cls: 'bg-purple-50 text-purple-700' },
  prescriptive:  { label: 'Prescriptive',  cls: 'bg-amber-50 text-amber-700' },
};

const EVIDENCE_ICONS: Record<string, typeof Quote> = {
  quote: Quote,
  statistic: BarChart2,
  citation: BookOpen,
  example: MessageSquare,
  data: BarChart2,
  testimony: MessageSquare,
};

function evidenceTypeFromTitle(title: string): string {
  // titles look like "[quote]", "[statistic]", etc.
  const match = title.match(/\[(\w+)\]/);
  return match ? match[1] : 'example';
}

// ─── Filter helper ───────────────────────────────────────────────

function filterOutline(nodes: OutlineNode[], term: string): OutlineNode[] {
  if (!term) return nodes;
  const lower = term.toLowerCase();
  return nodes.reduce<OutlineNode[]>((acc, node) => {
    const titleMatch = node.title?.toLowerCase().includes(lower);
    const contentMatch = node.content?.toLowerCase().includes(lower);
    const filteredChildren = node.children ? filterOutline(node.children, term) : [];
    if (titleMatch || contentMatch || filteredChildren.length > 0) {
      acc.push({ ...node, children: filteredChildren.length > 0 ? filteredChildren : node.children });
    }
    return acc;
  }, []);
}

// ─── Collect nested evidence ────────────────────────────────────

/**
 * Recursively collect all evidence-type nodes from a node's subtree (flattened).
 * Walks into sub-claims to find evidence at any depth.
 */
function collectEvidenceChildren(node: OutlineNode): Array<{
  quote_type: string;
  content: string;
  outline_node_id: string;
}> {
  const results: Array<{ quote_type: string; content: string; outline_node_id: string }> = [];

  if (!node.children) return results;

  for (const child of node.children) {
    if (child.node_type === 'evidence') {
      results.push({
        quote_type: evidenceTypeFromTitle(child.title),
        content: child.content || child.title,
        outline_node_id: child.id,
      });
    }
    // Recurse into all children (sub-claims can have their own evidence)
    if (child.children && child.children.length > 0) {
      results.push(...collectEvidenceChildren(child));
    }
  }

  return results;
}

// ─── Outline tree node ──────────────────────────────────────────

function OutlineNodeRow({
  node, depth, onPick, filter, defaultExpanded,
}: {
  node: OutlineNode;
  depth: number;
  onPick: (node: OutlineNode) => void;
  filter: string;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const hasChildren = (node.children?.length ?? 0) > 0;
  const isEvidence = node.node_type === 'evidence';
  const evType = isEvidence ? evidenceTypeFromTitle(node.title) : null;
  const EvIcon = evType ? EVIDENCE_ICONS[evType] || MessageSquare : null;
  const typeStyle = node.claim_type ? CLAIM_TYPE_STYLES[node.claim_type] : null;

  return (
    <div>
      <div
        className={`group flex items-start gap-1.5 rounded-md transition-colors ${
          isEvidence
            ? 'py-1.5 px-2 hover:bg-slate-100'
            : 'py-2 px-2 hover:bg-indigo-50'
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {/* Expand/collapse toggle */}
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-0.5 p-0.5 text-slate-400 hover:text-slate-600 shrink-0"
          >
            {expanded
              ? <ChevronDown className="w-3.5 h-3.5" />
              : <ChevronRight className="w-3.5 h-3.5" />}
          </button>
        ) : (
          <span className="w-[18px] shrink-0" />
        )}

        {/* Icon */}
        {isEvidence && EvIcon ? (
          <EvIcon className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
        ) : (
          !isEvidence && <FileText className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
        )}

        {/* Content */}
        <div className="min-w-0 flex-1">
          {isEvidence ? (
            <>
              <span className="text-[10px] font-medium uppercase text-slate-400 tracking-wider">
                {evType}
              </span>
              <p className="text-xs text-slate-700 mt-0.5 line-clamp-3">{node.content}</p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-sm font-medium text-slate-900">{node.title}</span>
                {typeStyle && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${typeStyle.cls}`}>
                    {typeStyle.label}
                  </span>
                )}
              </div>
              {node.content && (
                <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{node.content}</p>
              )}
            </>
          )}
        </div>

        {/* Pick button */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onPick(node); }}
          className="opacity-0 group-hover:opacity-100 text-[10px] font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded shrink-0 transition-opacity mt-0.5"
        >
          Use
        </button>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="border-l border-slate-100" style={{ marginLeft: `${depth * 16 + 17}px` }}>
          {node.children!.map((child) => (
            <OutlineNodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              onPick={onPick}
              filter={filter}
              defaultExpanded={!!filter || depth < 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────

export function KBResourcePicker({ onSelect, onCancel }: KBResourcePickerProps) {
  // Step 1: Search
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);

  // Step 2: Outline browse
  const [resourceData, setResourceData] = useState<Omit<KBSelection, 'selectedText' | 'selectedTitle'> | null>(null);
  const [allParses, setAllParses] = useState<ResourceParse[]>([]);
  const [activeParse, setActiveParse] = useState<ResourceParse | null>(null);
  const [outline, setOutline] = useState<OutlineResponse | null>(null);
  const [loadingOutline, setLoadingOutline] = useState(false);
  const [filter, setFilter] = useState('');

  const filteredOutline = useMemo(
    () => (outline ? filterOutline(outline.outline, filter) : []),
    [outline, filter],
  );

  // ── Search ──

  async function handleSearch() {
    const trimmed = query.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const response = await knowledgeApi.search(trimmed, { limit: 10 });
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  // ── Select resource ──

  async function handleSelectResource(result: SearchResult) {
    setLoadingId(result.resource_id);
    setError(null);
    try {
      const resource = await knowledgeApi.getResource(result.resource_id);
      const resData = {
        id: resource.id,
        name: resource.name,
        source_url: resource.source_url,
        resource_type: resource.resource_type,
        collection_name: result.collection_name,
      };

      const parsesResponse = await argumentsApi.getResourceParses(resource.id);
      if (parsesResponse.parses.length > 0) {
        const sorted = [...parsesResponse.parses].sort((a, b) => {
          const order: Record<string, number> = { full: 3, standard: 2, light: 1 };
          return (order[b.parse_level] || 0) - (order[a.parse_level] || 0);
        });
        setResourceData(resData);
        setAllParses(sorted);
        await loadOutline(sorted[0]);
      } else {
        onSelect(resData);
      }
    } catch (err) {
      setError('Failed to load resource details');
      setLoadingId(null);
    }
  }

  async function loadOutline(parse: ResourceParse) {
    setActiveParse(parse);
    setLoadingOutline(true);
    setFilter('');
    try {
      const data = await argumentsApi.getOutline(parse.id);
      setOutline(data);
    } catch {
      setError('Failed to load outline');
    } finally {
      setLoadingOutline(false);
    }
  }

  // ── Select an outline node ──

  function handlePickNode(node: OutlineNode) {
    if (!resourceData) return;

    // Collect supporting evidence from children if this is a parent claim
    const supportingQuotes =
      node.node_type === 'argument' && node.children && node.children.length > 0
        ? collectEvidenceChildren(node)
        : undefined;

    onSelect({
      ...resourceData,
      selectedText: node.content || node.title,
      selectedTitle: node.node_type === 'evidence'
        ? `[${evidenceTypeFromTitle(node.title)}]`
        : node.title,
      // Parse tracking for "View in parse" feature
      parsedResourceId: activeParse?.id,
      outlineNodeId: node.id,
      outlineNodeType: node.node_type,
      supportingQuotes: supportingQuotes && supportingQuotes.length > 0 ? supportingQuotes : undefined,
    });
  }

  function handleUseWithoutContent() {
    if (!resourceData) return;
    onSelect(resourceData);
  }

  function handleBackToSearch() {
    setResourceData(null);
    setAllParses([]);
    setActiveParse(null);
    setOutline(null);
    setLoadingId(null);
    setFilter('');
  }

  // ──────────────────────────────────────────────
  // Step 2: Outline browse view
  // ──────────────────────────────────────────────
  if (resourceData) {
    return (
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handleBackToSearch}
            className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-800"
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>
          <button type="button" onClick={onCancel} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Resource info */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-2.5">
          <div className="text-sm font-medium text-indigo-900 truncate">{resourceData.name}</div>
          {outline?.main_thesis && (
            <p className="text-xs text-indigo-700 mt-1 line-clamp-2">{outline.main_thesis}</p>
          )}
        </div>

        {/* Parse selector + filter row */}
        <div className="flex gap-2">
          {allParses.length > 1 && (
            <select
              value={activeParse?.id ?? ''}
              onChange={(e) => {
                const p = allParses.find((x) => x.id === Number(e.target.value));
                if (p) loadOutline(p);
              }}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {allParses.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.parse_level.charAt(0).toUpperCase() + p.parse_level.slice(1)} ({p.claim_count} claims)
                </option>
              ))}
            </select>
          )}
          <div className="flex-1 relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter claims & evidence..."
              className="w-full rounded-md border border-slate-300 pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Outline tree */}
        {loadingOutline ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading outline...
          </div>
        ) : (
          <>
            <p className="text-[11px] text-slate-400">
              Hover any item and click <span className="font-medium text-indigo-500">Use</span> to auto-fill evidence fields.
            </p>
            <div className="max-h-80 overflow-y-auto border border-slate-200 rounded-lg py-1">
              {filteredOutline.length > 0 ? (
                filteredOutline.map((node) => (
                  <OutlineNodeRow
                    key={node.id}
                    node={node}
                    depth={0}
                    onPick={handlePickNode}
                    filter={filter}
                    defaultExpanded={!!filter || true}
                  />
                ))
              ) : (
                <p className="text-xs text-slate-400 text-center py-4">
                  {filter ? 'No matches' : 'No outline data'}
                </p>
              )}
            </div>

            <button
              type="button"
              onClick={handleUseWithoutContent}
              className="w-full text-center px-3 py-2 text-sm text-slate-500 hover:text-slate-700 border border-dashed border-slate-300 rounded-lg hover:border-slate-400 transition-colors"
            >
              Use without parsed content
            </button>
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  // ──────────────────────────────────────────────
  // Step 1: Search view
  // ──────────────────────────────────────────────
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <Database className="w-4 h-4" />
          Search Knowledge Base
        </div>
        <button type="button" onClick={onCancel} className="p-1 text-slate-400 hover:text-slate-600 rounded">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleSearch();
            }
          }}
          placeholder="Search for resources..."
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          autoFocus
        />
        <button
          type="button"
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {results.length > 0 && (
        <div className="space-y-1.5 max-h-60 overflow-y-auto">
          {results.map((result) => (
            <button
              key={result.resource_id}
              type="button"
              onClick={() => handleSelectResource(result)}
              disabled={loadingId === result.resource_id}
              className="w-full text-left p-3 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors disabled:opacity-50"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm text-slate-900 truncate">{result.resource_name}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-slate-500">{result.collection_name}</span>
                    <span className="text-xs text-slate-300">|</span>
                    <span className="text-xs text-slate-500">{result.resource_type}</span>
                  </div>
                  {result.matched_text && (
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{result.matched_text}</p>
                  )}
                </div>
                {loadingId === result.resource_id ? (
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-500 shrink-0 mt-0.5" />
                ) : (
                  <span className="text-xs text-indigo-600 font-medium shrink-0 mt-0.5">Select</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {searched && !loading && results.length === 0 && !error && (
        <p className="text-sm text-slate-500 text-center py-3">No resources found</p>
      )}
    </div>
  );
}
