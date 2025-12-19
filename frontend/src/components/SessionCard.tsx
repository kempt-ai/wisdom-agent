'use client';

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  MessageSquare,
  FileText,
  Sparkles,
  Calendar,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getSessionTranscript,
  getSessionSummary,
  getSessionReflection,
} from '@/lib/api';

interface SessionCardProps {
  session: {
    id: number;
    title?: string;
    summary?: string;
    created_at: string;
    updated_at: string;
    message_count: number;
    has_reflection: boolean;
    project_id?: number;
  };
  defaultExpanded?: boolean;
}

type TabType = 'transcript' | 'summary' | 'reflection';

export function SessionCard({ session, defaultExpanded = false }: SessionCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [activeTab, setActiveTab] = useState<TabType | null>(null);
  const [content, setContent] = useState<{
    transcript?: string;
    summary?: string;
    reflection?: {
      overall_score?: number;
      values_scores: Record<string, number>;
      analysis: string;
      recommendations?: string[];
    };
  }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const loadContent = async (tab: TabType) => {
    if (content[tab]) {
      setActiveTab(tab);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      switch (tab) {
        case 'transcript':
          const transcriptData = await getSessionTranscript(session.id);
          setContent((prev) => ({ ...prev, transcript: transcriptData.transcript }));
          break;
        case 'summary':
          const summaryData = await getSessionSummary(session.id);
          setContent((prev) => ({ ...prev, summary: summaryData.summary }));
          break;
        case 'reflection':
          const reflectionData = await getSessionReflection(session.id);
          setContent((prev) => ({ ...prev, reflection: reflectionData }));
          break;
      }
      setActiveTab(tab);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load content');
    } finally {
      setIsLoading(false);
    }
  };

  const renderValuesScores = (scores: Record<string, number>) => {
    const valueNames: Record<string, string> = {
      awareness: 'Awareness',
      honesty: 'Honesty',
      accuracy: 'Accuracy',
      competence: 'Competence',
      compassion: 'Compassion',
      loving_kindness: 'Loving-kindness',
      joyful_sharing: 'Joyful-sharing',
    };

    return (
      <div className="grid grid-cols-2 gap-2 mt-3">
        {Object.entries(scores).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-sm text-stone-600">
              {valueNames[key] || key}
            </span>
            <div className="flex items-center gap-2">
              <div className="w-20 h-2 bg-stone-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-wisdom-500 rounded-full transition-all"
                  style={{ width: `${(value / 10) * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium text-wisdom-700 w-6">
                {value}
              </span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="border border-stone-200 rounded-lg bg-white overflow-hidden hover:border-wisdom-300 transition-colors">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-stone-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-stone-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-stone-400" />
          )}
          <div className="text-left">
            <h3 className="font-medium text-stone-800">
              {session.title || `Session ${session.id}`}
            </h3>
            {session.summary && (
              <p className="text-sm text-stone-500 line-clamp-1 mt-0.5">
                {session.summary}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm text-stone-500">
          <span className="flex items-center gap-1">
            <MessageSquare className="w-3.5 h-3.5" />
            {session.message_count}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            {formatDate(session.created_at)}
          </span>
          {session.has_reflection && (
            <span className="flex items-center gap-1 text-gold-600">
              <Sparkles className="w-3.5 h-3.5" />
              Reflected
            </span>
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-stone-100">
          {/* Tab Buttons */}
          <div className="flex gap-2 px-4 py-2 bg-stone-50">
            <button
              onClick={() => loadContent('transcript')}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md transition-colors flex items-center gap-1.5',
                activeTab === 'transcript'
                  ? 'bg-wisdom-100 text-wisdom-700'
                  : 'text-stone-600 hover:bg-stone-100'
              )}
            >
              <FileText className="w-3.5 h-3.5" />
              Transcript
            </button>
            <button
              onClick={() => loadContent('summary')}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md transition-colors flex items-center gap-1.5',
                activeTab === 'summary'
                  ? 'bg-wisdom-100 text-wisdom-700'
                  : 'text-stone-600 hover:bg-stone-100'
              )}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Summary
            </button>
            {session.has_reflection && (
              <button
                onClick={() => loadContent('reflection')}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-md transition-colors flex items-center gap-1.5',
                  activeTab === 'reflection'
                    ? 'bg-gold-100 text-gold-700'
                    : 'text-stone-600 hover:bg-stone-100'
                )}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Reflection
              </button>
            )}
          </div>

          {/* Tab Content */}
          {activeTab && (
            <div className="px-4 py-3 max-h-96 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin w-6 h-6 border-2 border-wisdom-500 border-t-transparent rounded-full" />
                </div>
              ) : error ? (
                <div className="text-red-500 text-sm py-4">{error}</div>
              ) : (
                <>
                  {activeTab === 'transcript' && content.transcript && (
                    <pre className="text-sm text-stone-700 whitespace-pre-wrap font-mono bg-stone-50 p-3 rounded-lg">
                      {content.transcript}
                    </pre>
                  )}

                  {activeTab === 'summary' && content.summary && (
                    <div className="text-sm text-stone-700 prose prose-stone max-w-none">
                      {content.summary}
                    </div>
                  )}

                  {activeTab === 'reflection' && content.reflection && (
                    <div>
                      {content.reflection.overall_score !== undefined && (
                        <div className="flex items-center gap-2 mb-4">
                          <span className="text-sm font-medium text-stone-600">
                            Overall Score:
                          </span>
                          <span className="text-lg font-semibold text-wisdom-600">
                            {content.reflection.overall_score}/10
                          </span>
                        </div>
                      )}

                      <h4 className="text-sm font-medium text-stone-700 mb-2">
                        7 Universal Values
                      </h4>
                      {renderValuesScores(content.reflection.values_scores)}

                      <div className="mt-4 pt-4 border-t border-stone-100">
                        <h4 className="text-sm font-medium text-stone-700 mb-2">
                          Analysis
                        </h4>
                        <p className="text-sm text-stone-600">
                          {content.reflection.analysis}
                        </p>
                      </div>

                      {content.reflection.recommendations &&
                        content.reflection.recommendations.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-stone-100">
                            <h4 className="text-sm font-medium text-stone-700 mb-2">
                              Recommendations
                            </h4>
                            <ul className="list-disc list-inside text-sm text-stone-600 space-y-1">
                              {content.reflection.recommendations.map((rec, i) => (
                                <li key={i}>{rec}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SessionCard;
