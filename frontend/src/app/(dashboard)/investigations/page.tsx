'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  RefreshCw,
  BookOpen,
  MessageSquareQuote,
  AlertCircle,
  Scale,
  Plus,
} from 'lucide-react';
import { argumentsApi, InvestigationSummary } from '@/lib/arguments-api';
import { SlideOutPanel } from '@/components/arguments/SlideOutPanel';
import { InvestigationEditor } from '@/components/arguments/InvestigationEditor';

// Status badge config
const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  draft: { label: 'Draft', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  published: { label: 'Published', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  archived: { label: 'Archived', color: 'text-slate-500', bg: 'bg-slate-50 border-slate-200' },
};

export default function InvestigationsListPage() {
  const router = useRouter();
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const data = await argumentsApi.listInvestigations();
      setInvestigations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load investigations');
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Scale className="w-6 h-6 text-indigo-600" />
              <h1 className="text-xl font-semibold text-slate-900">Investigations</h1>
            </div>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Investigation
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
            <span className="ml-2 text-slate-600">Loading investigations...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <p className="text-red-700">{error}</p>
            </div>
            <button onClick={loadData} className="mt-2 text-red-600 hover:text-red-800 underline text-sm">
              Try again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && investigations.length === 0 && (
          <div className="text-center py-12">
            <Scale className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h2 className="text-xl font-medium text-slate-700 mb-2">No investigations yet</h2>
            <p className="text-slate-500 mb-6">
              Create your first investigation to start building structured arguments.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Investigation
            </button>
          </div>
        )}

        {/* Investigation Cards */}
        {!loading && investigations.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {investigations.map((inv) => {
              const status = statusConfig[inv.status] || statusConfig.draft;
              return (
                <Link
                  key={inv.id}
                  href={`/investigations/${inv.slug}`}
                  className="block no-underline group"
                >
                  <div className="bg-white rounded-lg border border-slate-200 p-5 hover:border-indigo-300 hover:shadow-md transition-all duration-200 group-hover:-translate-y-0.5">
                    {/* Title & Status */}
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <h3 className="text-lg font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
                        {inv.title}
                      </h3>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${status.bg} ${status.color} shrink-0`}>
                        {status.label}
                      </span>
                    </div>

                    {/* Stats */}
                    <div className="flex items-center gap-4 text-sm text-slate-500 mb-3">
                      <div className="flex items-center gap-1.5">
                        <BookOpen className="w-4 h-4 text-blue-500" />
                        <span>{inv.definition_count} definition{inv.definition_count !== 1 ? 's' : ''}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <MessageSquareQuote className="w-4 h-4 text-orange-500" />
                        <span>{inv.claim_count} claim{inv.claim_count !== 1 ? 's' : ''}</span>
                      </div>
                    </div>

                    {/* Date */}
                    <p className="text-xs text-slate-400">
                      Updated {formatDate(inv.updated_at)}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>

      {/* Create investigation panel */}
      <SlideOutPanel
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Investigation"
      >
        <InvestigationEditor
          onSaved={(inv) => {
            setShowCreate(false);
            router.push(`/investigations/${inv.slug}`);
          }}
          onCancel={() => setShowCreate(false)}
        />
      </SlideOutPanel>
    </div>
  );
}
