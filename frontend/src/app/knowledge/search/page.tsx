'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { 
  ArrowLeft, Search, FileText, BookOpen, Layers,
  Clock, ExternalLink, Database
} from 'lucide-react';
import { 
  knowledgeApi, SearchResponse, SearchResult, ResourceType, CollectionSummary 
} from '@/lib/knowledge-api';

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

// Resource type icons
const resourceTypeIcons: Record<ResourceType, any> = {
  document: FileText,
  fiction_book: BookOpen,
  nonfiction_book: BookOpen,
  article: FileText,
  learning_module: FileText,
};

export default function KnowledgeSearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const debouncedQuery = useDebounce(query, 300);

  // Load collections for filter
  useEffect(() => {
    knowledgeApi.listCollections().then(setCollections).catch(console.error);
  }, []);

  // Search when query changes
  useEffect(() => {
    if (debouncedQuery.trim().length >= 2) {
      performSearch();
    } else {
      setResults(null);
      setSearched(false);
    }
  }, [debouncedQuery, selectedCollections]);

  async function performSearch() {
    setLoading(true);
    try {
      const response = await knowledgeApi.search(debouncedQuery, {
        collection_ids: selectedCollections.length > 0 ? selectedCollections : undefined,
        limit: 20,
      });
      setResults(response);
      setSearched(true);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  }

  function toggleCollection(id: number) {
    if (selectedCollections.includes(id)) {
      setSelectedCollections(selectedCollections.filter(c => c !== id));
    } else {
      setSelectedCollections([...selectedCollections, id]);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4 h-16">
            <Link 
              href="/knowledge"
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search your knowledge base..."
                className="w-full pl-10 pr-4 py-2 bg-slate-100 border border-transparent rounded-lg focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-colors"
                autoFocus
              />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Collection Filters */}
        {collections.length > 0 && (
          <div className="mb-6">
            <p className="text-sm font-medium text-slate-700 mb-2">Filter by collection:</p>
            <div className="flex flex-wrap gap-2">
              {collections.map((collection) => (
                <button
                  key={collection.id}
                  onClick={() => toggleCollection(collection.id)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                    selectedCollections.includes(collection.id)
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-700 hover:border-slate-300'
                  }`}
                >
                  {collection.name}
                </button>
              ))}
              {selectedCollections.length > 0 && (
                <button
                  onClick={() => setSelectedCollections([])}
                  className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>
        )}

        {/* Initial State */}
        {!searched && !loading && (
          <div className="text-center py-16">
            <Database className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h2 className="text-xl font-medium text-slate-700 mb-2">Search your knowledge</h2>
            <p className="text-slate-500">
              Enter at least 2 characters to search across your collections
            </p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-slate-500 mt-3">Searching...</p>
          </div>
        )}

        {/* Results */}
        {results && !loading && (
          <div>
            {/* Results Header */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-slate-600">
                {results.total_results} result{results.total_results !== 1 ? 's' : ''} for "{results.query}"
              </p>
              <p className="text-sm text-slate-400">
                {results.search_time_ms.toFixed(0)}ms
              </p>
            </div>

            {/* No Results */}
            {results.total_results === 0 && (
              <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
                <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-700 mb-2">No results found</h3>
                <p className="text-slate-500">
                  Try different keywords or broaden your search
                </p>
              </div>
            )}

            {/* Results List */}
            {results.total_results > 0 && (
              <div className="space-y-3">
                {results.results.map((result, idx) => (
                  <SearchResultCard key={`${result.resource_id}-${idx}`} result={result} />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// Search Result Card
function SearchResultCard({ result }: { result: SearchResult }) {
  const Icon = resourceTypeIcons[result.resource_type] || FileText;

  return (
    <Link
      href={`/knowledge/${result.collection_id}`}
      className="block bg-white rounded-lg border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all p-4"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 bg-slate-100 rounded-lg mt-0.5">
          <Icon className="w-4 h-4 text-slate-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-slate-900 truncate">{result.resource_name}</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            in <span className="text-indigo-600">{result.collection_name}</span>
          </p>
          
          {/* Matched Text */}
          {result.matched_text && (
            <p className="text-sm text-slate-600 mt-2 line-clamp-2">
              ...{result.matched_text}...
            </p>
          )}
        </div>

        {/* Relevance Score */}
        <div className="text-right">
          <div className="inline-flex items-center px-2 py-1 bg-slate-100 rounded text-xs text-slate-600">
            {Math.round(result.relevance_score * 100)}% match
          </div>
        </div>
      </div>
    </Link>
  );
}
