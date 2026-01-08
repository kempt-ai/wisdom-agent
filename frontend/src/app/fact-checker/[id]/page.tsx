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
  // Logic verdicts (derived from score)
  sound: { color: 'text-green-700', bg: 'bg-green-100', icon: CheckCircle },
  mostly_sound: { color: 'text-green-600', bg: 'bg-green-50', icon: CheckCircle },
  some_issues: { color: 'text-yellow-700', bg: 'bg-yellow-100', icon: HelpCircle },
  problematic: { color: 'text-orange-700', bg: 'bg-orange-100', icon: AlertCircle },
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

// Helper to derive logic verdict from score
function getLogicVerdict(logicAnalysis: any): string {
  if (!logicAnalysis?.logic_quality_score) return 'uncertain';
  const score = logicAnalysis.logic_quality_score;
  if (score >= 0.85) return 'sound';
  if (score >= 0.7) return 'mostly_sound';
  if (score >= 0.5) return 'some_issues';
  return 'problematic';
}

// Helper to extract values assessment from wisdom evaluation
function getValuesAssessment(wisdomEval: any): Record<string, { score: number; notes?: string }> | null {
  if (!wisdomEval) return null;
  
  const valueKeys = ['awareness', 'honesty', 'accuracy', 'competence', 'compassion', 'loving_kindness', 'joyful_sharing'];
  const assessment: Record<string, { score: number; notes?: string }> = {};
  
  let hasValues = false;
  for (const key of valueKeys) {
    if (wisdomEval[key] && typeof wisdomEval[key].score === 'number') {
      assessment[key] = wisdomEval[key];
      hasValues = true;
    }
  }
  
  return hasValues ? assessment : null;
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

  // Derive values for display from actual API field names
  const factualVerdict = (review as any).overall_factual_verdict || (review as any).factual_verdict;
  const wisdomVerdict = (review as any).overall_wisdom_verdict || (review as any).wisdom_verdict;
  const logicVerdict = getLogicVerdict((review as any).logic_analysis);
  const valuesAssessment = getValuesAssessment((review as any).wisdom_evaluation);

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
        {/* Overall Verdicts */}
        {review.status === 'completed' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <VerdictCard
              title="Factual Accuracy"
              verdict={factualVerdict}
              icon={FileText}
            />
            <VerdictCard
              title="Logical Soundness"
              verdict={logicVerdict}
              icon={Brain}
            />
            <VerdictCard
              title="Wisdom Alignment"
              verdict={wisdomVerdict}
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

        {/* Logic Analysis */}
        {review.logic_analysis && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-indigo-600" />
              Logic Analysis
            </h2>
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              {/* Main conclusion (was argument_structure) */}
              {((review.logic_analysis as any).main_conclusion || (review.logic_analysis as any).argument_structure) && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Main Conclusion</h3>
                  <p className="text-slate-600">
                    {(review.logic_analysis as any).main_conclusion || (review.logic_analysis as any).argument_structure}
                  </p>
                </div>
              )}
              {/* Fallacies (handle both old and new format) */}
              {((review.logic_analysis as any).fallacies_found?.length > 0 || (review.logic_analysis as any).fallacies_detected?.length > 0) && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Fallacies Detected</h3>
                  <ul className="list-disc list-inside text-slate-600 space-y-1">
                    {((review.logic_analysis as any).fallacies_found || (review.logic_analysis as any).fallacies_detected || []).map((fallacy: any, i: number) => (
                      <li key={i}>
                        {typeof fallacy === 'string' ? fallacy : (
                          <>
                            <strong>{fallacy.name}</strong>
                            {fallacy.description && `: ${fallacy.description}`}
                            {fallacy.quote && <span className="text-slate-400 italic ml-2">"{fallacy.quote}"</span>}
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Soundness assessment (was overall_soundness) */}
              {((review.logic_analysis as any).soundness_assessment || (review.logic_analysis as any).overall_soundness) && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Overall Assessment</h3>
                  <p className="text-slate-600">
                    {(review.logic_analysis as any).soundness_assessment || (review.logic_analysis as any).overall_soundness}
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Wisdom Evaluation */}
        {review.wisdom_evaluation && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Heart className="w-5 h-5 text-indigo-600" />
              Wisdom Evaluation
            </h2>
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              {/* Values assessment - handle both formats */}
              {(valuesAssessment || (review.wisdom_evaluation as any).values_assessment) && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-slate-700 mb-3">7 Universal Values</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.entries(valuesAssessment || (review.wisdom_evaluation as any).values_assessment).map(([value, assessment]: [string, any]) => (
                      <div key={value} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                        <span className="text-slate-700 capitalize">{value.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-indigo-500 rounded-full"
                              style={{ width: `${(assessment.score / 5) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-slate-600 w-8">{assessment.score}/5</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Something Deeperism assessment (handle both field names) */}
              {((review.wisdom_evaluation as any).something_deeperism_assessment || (review.wisdom_evaluation as any).something_deeperism_alignment) && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Something Deeperism Alignment</h3>
                  <p className="text-slate-600">
                    {(review.wisdom_evaluation as any).something_deeperism_assessment || (review.wisdom_evaluation as any).something_deeperism_alignment}
                  </p>
                </div>
              )}
              {/* Final reflection / overall alignment (handle both field names) */}
              {((review.wisdom_evaluation as any).final_reflection || (review.wisdom_evaluation as any).overall_alignment) && (
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">Overall Wisdom Assessment</h3>
                  <p className="text-slate-600">
                    {(review.wisdom_evaluation as any).final_reflection || (review.wisdom_evaluation as any).overall_alignment}
                  </p>
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

// Claim Card Component
function ClaimCard({ 
  claim, 
  expanded, 
  onToggle 
}: { 
  claim: any;
  expanded: boolean;
  onToggle: () => void;
}) {
  // Handle both old format (claim.verdict) and new format (claim.fact_check_result.verdict)
  const verdict = claim.fact_check_result?.verdict || claim.verdict;
  const confidence = claim.fact_check_result?.confidence || claim.confidence;
  const explanation = claim.fact_check_result?.explanation || claim.explanation;
  const sources = claim.fact_check_result?.web_sources || claim.sources || [];
  
  const config = verdictConfig[verdict?.toLowerCase()] || verdictConfig.unverifiable;
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
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
        )}
      </button>
      
      {expanded && explanation && (
        <div className="px-4 pb-4 pt-0">
          <div className="ml-10 pl-4 border-l-2 border-slate-200">
            <p className="text-sm text-slate-600">{explanation}</p>
            {sources && sources.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-slate-500 mb-1">Sources:</p>
                <ul className="text-xs text-slate-500 space-y-1">
                  {sources.map((source: any, i: number) => {
                    const url = typeof source === 'string' ? source : source.url;
                    const title = typeof source === 'string' ? null : source.title;
                    return (
                      <li key={i}>
                        {url?.startsWith('http') ? (
                          <a 
                            href={url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:underline flex items-center gap-1"
                          >
                            {title || new URL(url).hostname}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          title || url || source
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
