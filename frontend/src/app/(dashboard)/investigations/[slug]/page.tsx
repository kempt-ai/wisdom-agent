'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  BookOpen,
  MessageSquareQuote,
  Scale,
  Clock,
  Pencil,
  Plus,
} from 'lucide-react';
import { argumentsApi, Investigation, Definition, ABClaim } from '@/lib/arguments-api';
import { InvestigationOverview } from '@/components/arguments/InvestigationOverview';
import { SlideOutPanel } from '@/components/arguments/SlideOutPanel';
import { DefinitionView } from '@/components/arguments/DefinitionView';
import { ClaimView } from '@/components/arguments/ClaimView';
import { InvestigationEditor } from '@/components/arguments/InvestigationEditor';
import { DefinitionEditor } from '@/components/arguments/DefinitionEditor';
import { ClaimEditor } from '@/components/arguments/ClaimEditor';

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  draft: { label: 'Draft', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  published: { label: 'Published', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  archived: { label: 'Archived', color: 'text-slate-500', bg: 'bg-slate-50 border-slate-200' },
};

export default function InvestigationDetailPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Slide-out panel state
  type PanelMode = 'definition' | 'claim' | 'edit-investigation' | 'add-definition' | 'edit-definition' | 'add-claim' | 'edit-claim';
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelType, setPanelType] = useState<PanelMode | null>(null);
  const [panelData, setPanelData] = useState<Definition | ABClaim | null>(null);
  const [panelLoading, setPanelLoading] = useState(false);
  const [panelError, setPanelError] = useState<string | null>(null);
  const overviewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (slug) loadData();
  }, [slug]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const data = await argumentsApi.getInvestigation(slug);
      setInvestigation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation');
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

  const closePanel = useCallback(() => {
    setPanelOpen(false);
    // Clear data after animation completes
    setTimeout(() => {
      setPanelData(null);
      setPanelType(null);
      setPanelError(null);
    }, 300);
  }, []);

  const openDefinition = useCallback(async (defSlug: string) => {
    setPanelType('definition');
    setPanelOpen(true);
    setPanelLoading(true);
    setPanelError(null);
    setPanelData(null);
    try {
      const def = await argumentsApi.getDefinition(slug, defSlug);
      setPanelData(def);
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : 'Failed to load definition');
    } finally {
      setPanelLoading(false);
    }
  }, [slug]);

  const openClaim = useCallback(async (claimSlug: string) => {
    setPanelType('claim');
    setPanelOpen(true);
    setPanelLoading(true);
    setPanelError(null);
    setPanelData(null);
    try {
      const claim = await argumentsApi.getClaim(slug, claimSlug);
      setPanelData(claim);
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : 'Failed to load claim');
    } finally {
      setPanelLoading(false);
    }
  }, [slug]);

  function openEditor(mode: PanelMode, data?: Definition | ABClaim) {
    setPanelType(mode);
    setPanelData(data || null);
    setPanelLoading(false);
    setPanelError(null);
    setPanelOpen(true);
  }

  /** Called after any editor saves — refresh investigation data and close panel */
  async function handleEditorSaved() {
    closePanel();
    await loadData();
  }

  // Intercept clicks on ab-definition and ab-claim links in the overview.
  // Must depend on `investigation` so the effect re-runs after data loads —
  // during the loading state the early return means overviewRef.current is null.
  useEffect(() => {
    const container = overviewRef.current;
    if (!container) return;

    function handleClick(e: MouseEvent) {
      const target = e.target as HTMLElement;
      const link = target.closest('a.ab-link') as HTMLAnchorElement | null;
      if (!link) return;

      e.preventDefault();
      const href = link.getAttribute('href') || '';

      if (link.classList.contains('ab-definition')) {
        // href format: "#def:slug"
        const defSlug = href.replace('#def:', '');
        if (defSlug) openDefinition(defSlug);
      } else if (link.classList.contains('ab-claim')) {
        // href format: "#claim:slug"
        const claimSlug = href.replace('#claim:', '');
        if (claimSlug) openClaim(claimSlug);
      }
    }

    container.addEventListener('click', handleClick);
    return () => container.removeEventListener('click', handleClick);
  }, [investigation, openDefinition, openClaim]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
        <span className="ml-2 text-slate-600">Loading investigation...</span>
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-700 mb-2">{error || 'Investigation not found'}</p>
          <Link href="/investigations" className="text-indigo-600 hover:underline">
            &larr; Back to Investigations
          </Link>
        </div>
      </div>
    );
  }

  const status = statusConfig[investigation.status] || statusConfig.draft;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Link
                href="/investigations"
                className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="text-sm">Investigations</span>
              </Link>
              <span className="text-slate-300">/</span>
              <Scale className="w-5 h-5 text-indigo-600" />
              <h1 className="text-lg font-semibold text-slate-900 truncate max-w-md">
                {investigation.title}
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => openEditor('edit-investigation')}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-500 border border-slate-200 rounded hover:bg-slate-50 hover:text-slate-700 transition-colors"
              >
                <Pencil className="w-3 h-3" />
                Edit
              </button>
              <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium border ${status.bg} ${status.color}`}>
                {status.label}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Meta info */}
        <div className="flex items-center gap-4 text-sm text-slate-500 mb-6">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4" />
            <span>Updated {formatDate(investigation.updated_at)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <BookOpen className="w-4 h-4 text-blue-500" />
            <span>{investigation.definitions.length} definition{investigation.definitions.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <MessageSquareQuote className="w-4 h-4 text-orange-500" />
            <span>{investigation.claims.length} claim{investigation.claims.length !== 1 ? 's' : ''}</span>
          </div>
        </div>

        {/* Overview content with colored links */}
        <div ref={overviewRef} className="bg-white rounded-lg border border-slate-200 p-8 mb-8">
          <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">Overview</h2>
          <InvestigationOverview
            overviewHtml={investigation.overview_html}
            className="prose prose-slate max-w-none"
          />
        </div>

        {/* Link legend */}
        <div className="bg-white rounded-lg border border-slate-200 p-4 mb-8">
          <h3 className="text-sm font-medium text-slate-500 mb-3">Link Colors</h3>
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-500"></span>
              <span className="text-slate-600">Definition</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-500"></span>
              <span className="text-slate-600">Claim</span>
            </div>
          </div>
        </div>

        {/* Definitions list */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-blue-500" />
              Definitions ({investigation.definitions.length})
            </h2>
            <button
              onClick={() => openEditor('add-definition')}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-600 border border-blue-200 rounded hover:bg-blue-50 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add Definition
            </button>
          </div>
          {investigation.definitions.length > 0 ? (
            <div className="space-y-2">
              {investigation.definitions.map((def) => (
                <div
                  key={def.id}
                  onClick={() => openDefinition(def.slug)}
                  className="bg-white rounded-lg border border-slate-200 p-4 hover:border-blue-300 transition-colors cursor-pointer"
                >
                  <h3 className="font-medium text-blue-600">{def.term}</h3>
                  <div
                    className="text-sm text-slate-600 mt-1 line-clamp-2"
                    dangerouslySetInnerHTML={{ __html: def.definition_html }}
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">No definitions yet.</p>
          )}
        </div>

        {/* Claims list */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <MessageSquareQuote className="w-5 h-5 text-orange-500" />
              Claims ({investigation.claims.length})
            </h2>
            <button
              onClick={() => openEditor('add-claim')}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-orange-600 border border-orange-200 rounded hover:bg-orange-50 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add Claim
            </button>
          </div>
          {investigation.claims.length > 0 ? (
            <div className="space-y-2">
              {investigation.claims.map((claim) => (
                <div
                  key={claim.id}
                  onClick={() => openClaim(claim.slug)}
                  className="bg-white rounded-lg border border-slate-200 p-4 hover:border-orange-300 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-medium text-orange-600">{claim.title}</h3>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 shrink-0">
                      {claim.status}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mt-1 line-clamp-2">{claim.claim_text}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                    <span>{claim.evidence.length} evidence</span>
                    <span>{claim.counterarguments.length} counterargument{claim.counterarguments.length !== 1 ? 's' : ''}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">No claims yet.</p>
          )}
        </div>
      </main>

      {/* Slide-out panel for views and editors */}
      <SlideOutPanel
        isOpen={panelOpen}
        onClose={closePanel}
        title={
          panelType === 'definition' ? 'Definition'
            : panelType === 'claim' ? 'Claim'
            : panelType === 'edit-investigation' ? 'Edit Investigation'
            : panelType === 'add-definition' ? 'New Definition'
            : panelType === 'edit-definition' ? 'Edit Definition'
            : panelType === 'add-claim' ? 'New Claim'
            : panelType === 'edit-claim' ? 'Edit Claim'
            : undefined
        }
      >
        {/* Loading state */}
        {panelLoading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-5 h-5 text-indigo-600 animate-spin" />
            <span className="ml-2 text-slate-500 text-sm">Loading...</span>
          </div>
        )}
        {panelError && (
          <div className="text-center py-12">
            <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
            <p className="text-sm text-slate-600">{panelError}</p>
          </div>
        )}

        {/* View: Definition */}
        {!panelLoading && !panelError && panelData && panelType === 'definition' && (
          <>
            <DefinitionView
              definition={panelData as Definition}
              onSeeAlsoClick={(defSlug) => openDefinition(defSlug)}
            />
            <div className="mt-6 pt-4 border-t border-slate-200">
              <button
                onClick={() => openEditor('edit-definition', panelData)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-500 border border-slate-200 rounded hover:bg-slate-50 transition-colors"
              >
                <Pencil className="w-3 h-3" />
                Edit Definition
              </button>
            </div>
          </>
        )}

        {/* View: Claim */}
        {!panelLoading && !panelError && panelData && panelType === 'claim' && (
          <>
            <ClaimView
              claim={panelData as ABClaim}
              onAddEvidence={() => loadData()}
            />
            <div className="mt-6 pt-4 border-t border-slate-200">
              <button
                onClick={() => openEditor('edit-claim', panelData)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-500 border border-slate-200 rounded hover:bg-slate-50 transition-colors"
              >
                <Pencil className="w-3 h-3" />
                Edit Claim
              </button>
            </div>
          </>
        )}

        {/* Editor: Investigation */}
        {panelType === 'edit-investigation' && (
          <InvestigationEditor
            investigation={investigation}
            onSaved={handleEditorSaved}
            onCancel={closePanel}
          />
        )}

        {/* Editor: New Definition */}
        {panelType === 'add-definition' && (
          <DefinitionEditor
            investigationSlug={slug}
            onSaved={handleEditorSaved}
            onCancel={closePanel}
          />
        )}

        {/* Editor: Edit Definition */}
        {panelType === 'edit-definition' && panelData && (
          <DefinitionEditor
            investigationSlug={slug}
            definition={panelData as Definition}
            onSaved={handleEditorSaved}
            onCancel={closePanel}
          />
        )}

        {/* Editor: New Claim */}
        {panelType === 'add-claim' && (
          <ClaimEditor
            investigationSlug={slug}
            onSaved={handleEditorSaved}
            onCancel={closePanel}
          />
        )}

        {/* Editor: Edit Claim */}
        {panelType === 'edit-claim' && panelData && (
          <ClaimEditor
            investigationSlug={slug}
            claim={panelData as ABClaim}
            onSaved={handleEditorSaved}
            onCancel={closePanel}
          />
        )}
      </SlideOutPanel>
    </div>
  );
}
