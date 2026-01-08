'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, RefreshCw, AlertCircle, CheckCircle, XCircle,
  HelpCircle, ExternalLink, FileText, Scale, Heart, Brain,
  ChevronDown, ChevronUp
} from 'lucide-react';
import { getFactCheckReview, FactCheckResult } from '@/lib/api';

// Verdict badge config
const verdictConfig: Record<string, { color: string; bg: string; icon: any }> = {
  accurate: { color: 'text-green-700', bg: 'bg-green-100', icon: CheckCircle },
  mostly_accurate: { color: 'text-green-600', bg: 'bg-green-50', icon: CheckCircle },
  mixed: { color: 'text-yellow-700', bg: 'bg-yellow-100', icon: HelpCircle },
  mostly_inaccurate: { color: 'text-orange-700', bg: 'bg-orange-100', icon: AlertCircle },
  inaccurate: { color: 'text-red-700', bg: 'bg-red-100', icon: XCircle },
  unverifiable: { color: 'text-slate-600', bg: 'bg-slate-100', icon: HelpCircle },
  // Claim-level verdicts
  true: { color: 'text-green-700', bg: 'bg-green-100', icon: CheckCircle },
  mostly_true: { color: 'text-green-600', bg: 'bg-green-50', icon: CheckCircle },
  half_true: { color: 'text-yellow-700', bg: 'bg-yellow-100', icon: HelpCircle },
  mostly_false: { color: 'text-orange-700', bg: 'bg-orange-100', icon: AlertCircle },
  false: { color: 'text-red-700', bg: 'bg-red-100', icon: XCircle },
  not_a_claim: { color: 'text-slate-500', bg: 'bg-slate-100', icon: HelpCircle },
  // Wisdom verdicts
  serves_wisdom: { color: 'text-indigo-700', bg: 'bg-indigo-100', icon: Heart },
  mostly_wise: { color: 'text-indigo-600', bg: 'bg-indigo-50', icon: Heart },
  mostly_unwise: { color: 'text-orange-700', bg: 'bg-orange-100', icon: AlertCircle },
  serves_folly: { color: 'text-red-700', bg: 'bg-red-100', icon: XCircle },
  uncertain: { color: 'text-slate-600', bg: 'bg-slate-100', icon: HelpCircle },
};

// Status config
const statusConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'text-slate-500', label: 'Pending' },
  extracting: { color: 'text-blue-500', label: 'Extracting content...' },
  analyzing_claims: { color: 'text-blue-500', label: 'Analyzing claims...' },
  fact_checking: { color: 'text-blue-500', label: 'Fact checking...' },
  logic_analysis: { color: 'text-blue-500', label: 'Analyzing logic...' },
  wisdom_evaluation: { color: 'text-blue-500', label: 'Evaluating wisdom...' },
  completed: { color: 'text-green-600', label: 'Completed' },
  failed: { color: 'text-red-600', label: 'Failed' },
};

// Helper to build values assessment from individual properties
function buildValuesAssessment(wisdom: any) {
  const valueKeys = ['awareness', 'honesty', 'accuracy', 'competence', 'compassion', 'loving_kindness', 'joyful_sharing'];
  const values: Record<string, { score: number; notes: string }> = {};
  
  for (const key of valueKeys) {
    if (wisdom[key] && typeof wisdom[key] === 'object') {
      values[key] = {
        score: wisdom[key].score || 0,
        notes: wisdom[key].notes || ''
      };
    }
  }
  
  return Object.keys(values).length > 0 ? values : null;
}

export default function FactCheckResultPage() {
  const params = useParams();
  const router = useRouter();
  const reviewId = Number(params.id);

  const [review, setReview] = useState<FactCheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedClaims, setExpandedClaims] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadReview();
  }, [reviewId]);

  async function loadReview() {
    setLoading(true);
    setError(null);
    try {
      const data = await getFactCheckReview(reviewId);
      setReview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review');
    } finally {
      setLoading(false);
    }
  }

  function toggleClaim(claimId: number) {
    const newExpanded = new Set(expandedClaims);
    if (newExpanded.has(claimId)) {
      newExpanded.delete(claimId);
    } else {
      newExpanded.add(claimId);
    }
    setExpandedClaims(newExpanded);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-slate-700 mb-2">{error || 'Review not found'}</p>
          <Link href="/" className="text-indigo-600 hover:underline">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const status = statusConfig[review.status] || statusConfig.pending;
  const isProcessing = !['completed', 'failed'].includes(review.status);

  // Build values assessment from API structure
  const valuesAssessment = review.wisdom_evaluation ? buildValuesAssessment(review.wisdom_evaluation) : null;

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
                <h1 className="text-xl font-semibold text-slate-900">
                  {review.title || 'Fact Check Review'}
                </h1>
                <p className="text-sm text-slate-500">
                  {review.source_type === 'url' && review.source_url ? (
                    <a 
                      href={review.source_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="hover:text-indigo-600 flex items-center gap-1"
                    >
                      {new URL(review.source_url).hostname}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    `${review.source_type} content`
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isProcessing && (
                <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
              )}
              <span className={`text-sm font-medium ${status.color}`}>
                {status.label}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overall Verdicts - FIXED: use correct API property names */}
        {review.status === 'completed' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <VerdictCard
              title="Factual Accuracy"
              verdict={review.overall_factual_verdict}
              icon={FileText}
            />
            <VerdictCard
              title="Logical Soundness"
              verdict={review.logic_analysis?.logic_quality_score !== undefined 
                ? (review.logic_analysis.logic_quality_score >= 0.7 ? 'mostly_accurate' 
                   : review.logic_analysis.logic_quality_score >= 0.4 ? 'mixed' 
                   : 'mostly_inaccurate')
                : undefined}
              icon={Brain}
            />
            <VerdictCard
              title="Wisdom Alignment"
              verdict={review.overall_wisdom_verdict}
              icon={Heart}
            />
          </div>
        )}

        {/* Claims Section */}
        {review.claims && review.claims.length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Scale className="w-5 h-5 text-indigo-600" />
              Extracted Claims ({review.claims.length})
            </h2>
            <div className="space-y-3">
              {review.claims.map((claim) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  expanded={expandedClaims.has(claim.id)}
                  onToggle={() => toggleClaim(claim.id)}
                />
              ))}
            </div>
          </section>
        )}

        {/* Logic Analysis - FIXED: use correct API property names */}
        {review.logic_analysis && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-indigo-600" />
              Logic Analysis
            </h2>
            <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-4">
              {/* Main Conclusion */}
              {review.logic_analysis.main_conclusion && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Main Conclusion</h3>
                  <p className="text-slate-600">{review.logic_analysis.main_conclusion}</p>
                </div>
              )}
              
              {/* Premises */}
              {review.logic_analysis.premises && review.logic_analysis.premises.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Key Premises</h3>
                  <ul className="list-disc list-inside text-slate-600 space-y-1">
                    {review.logic_analysis.premises.map((premise: string, i: number) => (
                      <li key={i}>{premise}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Fallacies - FIXED: fallacies_found is array of objects */}
              {review.logic_analysis.fallacies_found && review.logic_analysis.fallacies_found.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Fallacies Detected</h3>
                  <div className="space-y-3">
                    {review.logic_analysis.fallacies_found.map((fallacy: any, i: number) => (
                      <div key={i} className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <AlertCircle className="w-4 h-4 text-orange-600" />
                          <span className="font-medium text-orange-800">{fallacy.name}</span>
                          {fallacy.confidence && (
                            <span className="text-xs text-orange-600">
                              ({Math.round(fallacy.confidence * 100)}% confidence)
                            </span>
                          )}
                        </div>
                        {fallacy.description && (
                          <p className="text-sm text-orange-700 mb-1">{fallacy.description}</p>
                        )}
                        {fallacy.quote && (
                          <p className="text-xs text-orange-600 italic">"{fallacy.quote}"</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Validity Assessment */}
              {review.logic_analysis.validity_assessment && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Validity Assessment</h3>
                  <p className="text-slate-600">{review.logic_analysis.validity_assessment}</p>
                </div>
              )}

              {/* Soundness Assessment - FIXED: was overall_soundness */}
              {review.logic_analysis.soundness_assessment && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Soundness Assessment</h3>
                  <p className="text-slate-600">{review.logic_analysis.soundness_assessment}</p>
                </div>
              )}

              {/* Logic Quality Score */}
              {review.logic_analysis.logic_quality_score !== undefined && (
                <div className="pt-3 border-t border-slate-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">Logic Quality Score</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            review.logic_analysis.logic_quality_score >= 0.7 ? 'bg-green-500' :
                            review.logic_analysis.logic_quality_score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${review.logic_analysis.logic_quality_score * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-slate-600">
                        {Math.round(review.logic_analysis.logic_quality_score * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Wisdom Evaluation - FIXED: use correct API structure */}
        {review.wisdom_evaluation && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Heart className="w-5 h-5 text-indigo-600" />
              Wisdom Evaluation
            </h2>
            <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-6">
              {/* 7 Universal Values - FIXED: build from individual properties */}
              {valuesAssessment && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-3">7 Universal Values</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.entries(valuesAssessment).map(([value, assessment]) => (
                      <div key={value} className="p-3 bg-slate-50 rounded-lg">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-slate-700 capitalize font-medium">
                            {value.replace(/_/g, ' ')}
                          </span>
                          <div className="flex items-center gap-2">
                            <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${
                                  assessment.score >= 4 ? 'bg-green-500' :
                                  assessment.score >= 3 ? 'bg-indigo-500' :
                                  assessment.score >= 2 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${(assessment.score / 5) * 100}%` }}
                              />
                            </div>
                            <span className="text-sm text-slate-600 w-8">{assessment.score}/5</span>
                          </div>
                        </div>
                        {assessment.notes && (
                          <p className="text-xs text-slate-500 mt-1">{assessment.notes}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Something Deeperism Assessment - FIXED: was something_deeperism_alignment */}
              {review.wisdom_evaluation.something_deeperism_assessment && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Something Deeperism Assessment</h3>
                  <p className="text-slate-600">{review.wisdom_evaluation.something_deeperism_assessment}</p>
                </div>
              )}

              {/* Three Core Questions */}
              {(review.wisdom_evaluation.is_it_true || review.wisdom_evaluation.is_it_reasonable || review.wisdom_evaluation.does_it_serve_wisdom) && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-3">Three Core Questions</h3>
                  <div className="space-y-3">
                    {review.wisdom_evaluation.is_it_true && (
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <span className="text-sm font-medium text-blue-800">Is it True?</span>
                        <p className="text-sm text-blue-700 mt-1">{review.wisdom_evaluation.is_it_true}</p>
                      </div>
                    )}
                    {review.wisdom_evaluation.is_it_reasonable && (
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <span className="text-sm font-medium text-purple-800">Is it Reasonable?</span>
                        <p className="text-sm text-purple-700 mt-1">{review.wisdom_evaluation.is_it_reasonable}</p>
                      </div>
                    )}
                    {review.wisdom_evaluation.does_it_serve_wisdom && (
                      <div className="p-3 bg-indigo-50 rounded-lg">
                        <span className="text-sm font-medium text-indigo-800">Does it Serve Wisdom?</span>
                        <p className="text-sm text-indigo-700 mt-1">{review.wisdom_evaluation.does_it_serve_wisdom}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Final Reflection - FIXED: was overall_alignment */}
              {review.wisdom_evaluation.final_reflection && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Final Reflection</h3>
                  <p className="text-slate-600">{review.wisdom_evaluation.final_reflection}</p>
                </div>
              )}

              {/* Overall Wisdom Score */}
              {review.wisdom_evaluation.overall_wisdom_score !== undefined && (
                <div className="pt-3 border-t border-slate-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">Overall Wisdom Score</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            review.wisdom_evaluation.overall_wisdom_score >= 0.7 ? 'bg-green-500' :
                            review.wisdom_evaluation.overall_wisdom_score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${review.wisdom_evaluation.overall_wisdom_score * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-slate-600">
                        {Math.round(review.wisdom_evaluation.overall_wisdom_score * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Empty state for processing */}
        {isProcessing && (
          <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
            <RefreshCw className="w-12 h-12 text-indigo-400 mx-auto mb-4 animate-spin" />
            <h2 className="text-lg font-medium text-slate-700 mb-2">Analysis in Progress</h2>
            <p className="text-slate-500">
              This review is being processed. Results will appear here when complete.
            </p>
            <button
              onClick={loadReview}
              className="mt-4 px-4 py-2 text-indigo-600 hover:bg-indigo-50 rounded-lg"
            >
              Refresh Status
            </button>
          </div>
        )}

        {/* Empty state for no results */}
        {review.status === 'completed' && !review.claims?.length && !review.logic_analysis && !review.wisdom_evaluation && (
          <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
            <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-slate-700 mb-2">No Results Available</h2>
            <p className="text-slate-500">
              The analysis completed but no claims or evaluations were generated.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

// Verdict Card Component
function VerdictCard({ 
  title, 
  verdict, 
  icon: Icon 
}: { 
  title: string; 
  verdict?: string; 
  icon: any;
}) {
  const config = verdict ? verdictConfig[verdict.toLowerCase()] || verdictConfig.unverifiable : verdictConfig.unverifiable;
  const VerdictIcon = config.icon;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4 text-slate-400" />
        <span className="text-sm text-slate-500">{title}</span>
      </div>
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${config.bg}`}>
        <VerdictIcon className={`w-4 h-4 ${config.color}`} />
        <span className={`text-sm font-medium ${config.color} capitalize`}>
          {verdict?.replace(/_/g, ' ') || 'Pending'}
        </span>
      </div>
    </div>
  );
}

// Claim Card Component - FIXED: use fact_check_result nested properties
function ClaimCard({ 
  claim, 
  expanded, 
  onToggle 
}: { 
  claim: any;
  expanded: boolean;
  onToggle: () => void;
}) {
  // FIXED: verdict is inside fact_check_result
  const verdict = claim.fact_check_result?.verdict;
  const confidence = claim.fact_check_result?.confidence;
  const explanation = claim.fact_check_result?.explanation;
  const webSources = claim.fact_check_result?.web_sources;
  
  const config = verdict ? verdictConfig[verdict.toLowerCase()] || verdictConfig.unverifiable : verdictConfig.unverifiable;
  const VerdictIcon = config.icon;

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-start gap-4 text-left hover:bg-slate-50"
      >
        <div className={`p-1.5 rounded-full ${config.bg} mt-0.5`}>
          <VerdictIcon className={`w-4 h-4 ${config.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-slate-900">{claim.claim_text}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className={`text-xs font-medium ${config.color} capitalize`}>
              {verdict?.replace(/_/g, ' ') || 'Unverified'}
            </span>
            {confidence !== undefined && (
              <span className="text-xs text-slate-400">
                {Math.round(confidence * 100)}% confidence
              </span>
            )}
            {claim.claim_type && (
              <span className="text-xs text-slate-400 capitalize">
                {claim.claim_type}
              </span>
            )}
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
        )}
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 pt-0">
          <div className="ml-10 pl-4 border-l-2 border-slate-200 space-y-3">
            {/* Explanation */}
            {explanation && (
              <p className="text-sm text-slate-600">{explanation}</p>
            )}
            
            {/* Source Quote */}
            {claim.source_quote && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Original Quote:</p>
                <p className="text-sm text-slate-500 italic">"{claim.source_quote}"</p>
              </div>
            )}
            
            {/* Source Location */}
            {claim.source_location && (
              <p className="text-xs text-slate-400">Location: {claim.source_location}</p>
            )}

            {/* Providers Used */}
            {claim.fact_check_result?.providers_used && claim.fact_check_result.providers_used.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Verified by:</p>
                <div className="flex flex-wrap gap-1">
                  {claim.fact_check_result.providers_used.map((provider: string, i: number) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                      {provider}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Web Sources */}
            {webSources && webSources.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Sources:</p>
                <ul className="text-xs text-slate-500 space-y-1">
                  {webSources.map((source: any, i: number) => (
                    <li key={i}>
                      {source.url ? (
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:underline flex items-center gap-1"
                        >
                          {source.title || new URL(source.url).hostname}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        source.title || source
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
