'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Search,
  Link as LinkIcon,
  FileText,
  Loader2,
  ChevronRight,
  Sparkles,
  Scale,
  Brain,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  createFactCheckReview,
  browseFactChecks,
  type FactCheckSummary,
} from '@/lib/api';

export default function FactCheckerPage() {
  // Input state
  const [content, setContent] = useState('');
  const [sourceType, setSourceType] = useState<'text' | 'url'>('text');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<number | null>(null);

  // Browse state
  const [reviews, setReviews] = useState<FactCheckSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  // Cost estimation state
  const [isEstimating, setIsEstimating] = useState(false);
  const [costEstimate, setCostEstimate] = useState<any>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [showCostModal, setShowCostModal] = useState(false);

  // Load recent reviews
  useEffect(() => {
    loadReviews();
  }, []);

  const loadReviews = async () => {
    setIsLoading(true);
    try {
      const result = await browseFactChecks({ limit: 20 });
      setReviews(result.reviews || []);
    } catch (err) {
      console.error('Failed to load reviews:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Estimate cost before submitting
  const handleEstimateCost = async () => {
    if (!content.trim()) return;
    
    setIsEstimating(true);
    setCostEstimate(null);
    setSubmitError(null);
    
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${API_URL}/api/reviews/estimate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: sourceType,
          source_content: sourceType === 'text' ? content : undefined,
          source_url: sourceType === 'url' ? content : undefined,
        }),
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          // Endpoint not available, submit directly
          handleSubmit();
          return;
        }
        throw new Error('Failed to estimate cost');
      }
      
      const data = await response.json();
      setCostEstimate(data);
      setSelectedModel(data.recommended?.model_id || null);
      setSelectedProvider(data.recommended?.provider || null);
      setShowCostModal(true);
    } catch (err) {
      console.error('Estimate error:', err);
      // Fall back to direct submit
      handleSubmit();
    } finally {
      setIsEstimating(false);
    }
  };

  // Submit with selected model
  const handleConfirmAnalysis = async () => {
    setShowCostModal(false);
    
    if (!content.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const result = await createFactCheckReview(sourceType, content, {
        modelOverride: selectedModel || undefined,
        providerOverride: selectedProvider || undefined,
      });
      setSubmitSuccess(result.id);
      setContent('');
      setCostEstimate(null);
      loadReviews();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    if (!content.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const result = await createFactCheckReview(sourceType, content);
      setSubmitSuccess(result.id);
      setContent('');
      // Reload the list
      loadReviews();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getVerdictIcon = (verdict?: string) => {
    switch (verdict?.toLowerCase()) {
      case 'true':
      case 'accurate':
      case 'aligned':
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'mixed':
      case 'partially_accurate':
      case 'partially_aligned':
        return <AlertTriangle className="w-5 h-5 text-amber-500" />;
      case 'false':
      case 'inaccurate':
      case 'misaligned':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-stone-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="px-2 py-1 text-xs rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300">
            Completed
          </span>
        );
      case 'processing':
        return (
          <span className="px-2 py-1 text-xs rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            Processing
          </span>
        );
      case 'failed':
        return (
          <span className="px-2 py-1 text-xs rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
            Failed
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 text-xs rounded-full bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400">
            {status}
          </span>
        );
    }
  };

  const filteredReviews = reviews.filter(
    (r) =>
      !searchQuery ||
      r.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.source_url?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-stone-950">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-100 to-emerald-200 dark:from-emerald-900 dark:to-emerald-800 flex items-center justify-center">
              <CheckCircle className="w-7 h-7 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-semibold text-stone-900 dark:text-stone-100">
                Fact Checker
              </h1>
              <p className="text-stone-500 dark:text-stone-400">
                Analyze claims for facts, logic, and wisdom alignment
              </p>
            </div>
          </div>
        </div>

        {/* Analysis Types Info */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="card p-4">
            <div className="flex items-center gap-3 mb-2">
              <Search className="w-5 h-5 text-blue-500" />
              <h3 className="font-medium text-stone-900 dark:text-stone-100">Factual Accuracy</h3>
            </div>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Verifies claims against trusted sources and fact-checking databases
            </p>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3 mb-2">
              <Brain className="w-5 h-5 text-purple-500" />
              <h3 className="font-medium text-stone-900 dark:text-stone-100">Logical Soundness</h3>
            </div>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Analyzes argument structure and detects logical fallacies
            </p>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-3 mb-2">
              <Sparkles className="w-5 h-5 text-wisdom-500" />
              <h3 className="font-medium text-stone-900 dark:text-stone-100">Wisdom Alignment</h3>
            </div>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Evaluates alignment with the 7 Universal Values and Something Deeperism
            </p>
          </div>
        </div>

        {/* Input Section */}
        <div className="card p-6 mb-8">
          <h2 className="text-lg font-serif font-medium text-stone-900 dark:text-stone-100 mb-4">
            New Fact Check
          </h2>

          {/* Type selector */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setSourceType('text')}
              className={cn(
                'flex-1 px-4 py-3 rounded-xl flex items-center justify-center gap-2 transition-colors',
                sourceType === 'text'
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-2 border-emerald-300 dark:border-emerald-700'
                  : 'bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 border-2 border-transparent hover:bg-stone-200'
              )}
            >
              <FileText className="w-5 h-5" />
              Text / Claim
            </button>
            <button
              onClick={() => setSourceType('url')}
              className={cn(
                'flex-1 px-4 py-3 rounded-xl flex items-center justify-center gap-2 transition-colors',
                sourceType === 'url'
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-2 border-emerald-300 dark:border-emerald-700'
                  : 'bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 border-2 border-transparent hover:bg-stone-200'
              )}
            >
              <LinkIcon className="w-5 h-5" />
              URL / Article
            </button>
          </div>

          {/* Input */}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={
              sourceType === 'url'
                ? 'Paste the URL of an article to analyze...'
                : 'Enter a claim or paste text to fact-check...'
            }
            className={cn(
              'w-full h-40 px-4 py-3 rounded-xl resize-none',
              'bg-stone-50 dark:bg-stone-800',
              'border border-stone-200 dark:border-stone-700',
              'text-stone-900 dark:text-stone-100',
              'placeholder:text-stone-400 dark:placeholder:text-stone-500',
              'focus:outline-none focus:ring-2 focus:ring-emerald-500/50',
              'transition-colors'
            )}
          />

          {/* Error message */}
          {submitError && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
              {submitError}
            </div>
          )}

          {/* Success message */}
          {submitSuccess && (
            <div className="mt-4 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-sm flex items-center justify-between">
              <span>Analysis started successfully!</span>
              <Link
                href={`/fact-checker/${submitSuccess}`}
                className="flex items-center gap-1 underline hover:no-underline"
              >
                View Results <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          {/* Submit button */}
          <button
            onClick={handleEstimateCost}
            disabled={isSubmitting || isEstimating || !content.trim()}
            className={cn(
              'mt-4 w-full px-6 py-3 rounded-xl',
              'bg-emerald-600 dark:bg-emerald-500',
              'text-white font-medium',
              'hover:bg-emerald-700 dark:hover:bg-emerald-600',
              'transition-colors duration-200',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center justify-center gap-2'
            )}
          >
            {isEstimating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Estimating Cost...
              </>
            ) : isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Starting Analysis...
              </>
            ) : (
              <>
                <Scale className="w-5 h-5" />
                Analyze for Facts, Logic & Wisdom
              </>
            )}
          </button>
        </div>

        {/* Recent Reviews Section */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-serif font-medium text-stone-900 dark:text-stone-100">
              Recent Fact Checks
            </h2>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className={cn(
                  'pl-9 pr-4 py-2 rounded-lg text-sm',
                  'bg-stone-100 dark:bg-stone-800',
                  'border border-stone-200 dark:border-stone-700',
                  'text-stone-900 dark:text-stone-100',
                  'placeholder:text-stone-400',
                  'focus:outline-none focus:ring-2 focus:ring-emerald-500/50'
                )}
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
            </div>
          ) : filteredReviews.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-12 h-12 mx-auto mb-4 text-stone-300 dark:text-stone-600" />
              <p className="text-stone-500 dark:text-stone-400">
                {searchQuery ? 'No matching fact checks found' : 'No fact checks yet. Start your first analysis above!'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredReviews.map((review) => (
                <Link
                  key={review.id}
                  href={`/fact-checker/${review.id}`}
                  className="block no-underline"
                >
                  <div
                    className={cn(
                      'p-4 rounded-xl border border-stone-200 dark:border-stone-700',
                      'hover:border-emerald-300 dark:hover:border-emerald-700',
                      'hover:bg-stone-50 dark:hover:bg-stone-800/50',
                      'transition-colors duration-200'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {review.source_type === 'url' ? (
                            <LinkIcon className="w-4 h-4 text-stone-400" />
                          ) : (
                            <FileText className="w-4 h-4 text-stone-400" />
                          )}
                          <h3 className="font-medium text-stone-900 dark:text-stone-100 truncate">
                            {review.title || review.source_url || 'Untitled Analysis'}
                          </h3>
                        </div>
                        <p className="text-sm text-stone-500 dark:text-stone-400">
                          {new Date(review.created_at).toLocaleDateString()} at{' '}
                          {new Date(review.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 ml-4">
                        {review.status === 'completed' && (
                          <div className="flex items-center gap-2">
                            {getVerdictIcon(review.factual_verdict)}
                            {getVerdictIcon(review.wisdom_verdict)}
                          </div>
                        )}
                        {getStatusBadge(review.status)}
                        <ChevronRight className="w-5 h-5 text-stone-400" />
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
      {/* Cost Estimate Modal */}
      {showCostModal && costEstimate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-stone-900 rounded-xl max-w-lg w-full max-h-[80vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between p-4 border-b border-stone-200 dark:border-stone-700">
              <h3 className="font-medium text-stone-900 dark:text-stone-100">
                Cost Estimate
              </h3>
              <button
                onClick={() => setShowCostModal(false)}
                className="p-1 hover:bg-stone-100 dark:hover:bg-stone-800 rounded"
              >
                ✕
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="bg-stone-50 dark:bg-stone-800 rounded-lg p-3 text-sm">
                <p className="text-stone-600 dark:text-stone-400">
                  Content: ~{costEstimate.content_tokens?.toLocaleString()} tokens
                </p>
                <p className="text-stone-600 dark:text-stone-400">
                  Estimated claims: ~{costEstimate.estimated_claims}
                </p>
              </div>

              <div>
                <p className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-2">
                  Select Model:
                </p>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {costEstimate.estimates_by_model?.map((est: any) => (
                    <button
                      key={est.model_id}
                      onClick={() => {
                        setSelectedModel(est.model_id);
                        setSelectedProvider(est.provider);
                      }}
                      className={cn(
                        'w-full p-3 rounded-lg text-left transition-colors',
                        selectedModel === est.model_id
                          ? 'bg-emerald-100 dark:bg-emerald-900/30 border-2 border-emerald-500'
                          : 'bg-stone-100 dark:bg-stone-800 border-2 border-transparent hover:bg-stone-200'
                      )}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="font-medium text-stone-900 dark:text-stone-100">
                            {est.model_name}
                          </span>
                          {costEstimate.recommended?.model_id === est.model_id && (
                            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                              ⭐ Recommended
                            </span>
                          )}
                          <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-stone-200 dark:bg-stone-700 text-stone-600 dark:text-stone-400">
                            {est.tier}
                          </span>
                        </div>
                        <span className="font-mono text-emerald-600 dark:text-emerald-400">
                          ${est.estimated_cost?.toFixed(4)}
                        </span>
                      </div>
                      <p className="text-xs text-stone-500 mt-1">
                        {est.provider} • {est.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3 p-4 border-t border-stone-200 dark:border-stone-700">
              <button
                onClick={() => setShowCostModal(false)}
                className="flex-1 px-4 py-2 rounded-lg bg-stone-200 dark:bg-stone-700 text-stone-700 dark:text-stone-200"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAnalysis}
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 rounded-lg bg-emerald-600 text-white font-medium hover:bg-emerald-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Analyzing...' : `Analyze ($${costEstimate.estimates_by_model?.find((e: any) => e.model_id === selectedModel)?.estimated_cost?.toFixed(4) || '0.00'})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
