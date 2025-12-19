'use client';

/**
 * SessionList - Browse past wisdom sessions
 * 
 * Displays a list of sessions for a project, allowing users to
 * view session details, summaries, and reflections.
 * 
 * Created: Week 3 Day 4 - Session Browsing Feature
 */

import React, { useState, useEffect } from 'react';
import { getSessions, getSession, getSessionMessages, getSessionSummary, getSessionReflection } from '@/lib/api';
import type { Session, Message } from '@/lib/api';

interface SessionListProps {
  projectId: number;
  onSelectSession?: (sessionId: number) => void;
}

interface SessionDetail {
  session: Session;
  messages: Message[];
  summary?: {
    summary_text: string;
    key_topics?: string[];
    learning_outcomes?: string[];
  };
  reflection?: {
    reflection_text: string;
    scores: Record<string, number>;
    insights?: string[];
    growth_areas?: string[];
  };
}

export default function SessionList({ projectId, onSelectSession }: SessionListProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Load sessions on mount or when projectId changes
  useEffect(() => {
    loadSessions();
  }, [projectId]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSessions(projectId);
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const loadSessionDetail = async (sessionId: number) => {
    try {
      setLoadingDetail(true);
      
      // Load session info
      const session = await getSession(sessionId);
      
      // Load messages
      const messagesResponse = await getSessionMessages(sessionId);
      const messages = messagesResponse.messages || [];
      
      // Try to load summary (may not exist)
      let summary;
      try {
        summary = await getSessionSummary(sessionId);
      } catch {
        // Summary doesn't exist yet
      }
      
      // Try to load reflection (may not exist)
      let reflection;
      try {
        reflection = await getSessionReflection(sessionId);
      } catch {
        // Reflection doesn't exist yet
      }
      
      setSelectedSession({
        session,
        messages,
        summary,
        reflection
      });
      
      if (onSelectSession) {
        onSelectSession(sessionId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session details');
    } finally {
      setLoadingDetail(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderScoreBar = (value: number, label: string) => {
    const percentage = Math.round(value * 100);
    return (
      <div className="mb-2">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">{label}</span>
          <span className="text-gray-800 font-medium">{percentage}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-amber-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-500">
        <div className="animate-spin inline-block w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full mb-2"></div>
        <p>Loading sessions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-500">
        <p className="mb-2">Error: {error}</p>
        <button 
          onClick={loadSessions}
          className="text-blue-600 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>No sessions yet.</p>
        <p className="text-sm mt-1">Start a conversation to create your first session!</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Session List */}
      <div className={`${selectedSession ? 'w-1/3 border-r' : 'w-full'} overflow-y-auto`}>
        <div className="p-3 border-b bg-gray-50">
          <h3 className="font-semibold text-gray-800">Past Sessions</h3>
          <p className="text-sm text-gray-500">{sessions.length} session{sessions.length !== 1 ? 's' : ''}</p>
        </div>
        
        <div className="divide-y">
          {sessions.map((session) => (
            <button
              key={session.session_id}
              onClick={() => loadSessionDetail(session.session_id)}
              className={`w-full p-3 text-left hover:bg-gray-50 transition-colors ${
                selectedSession?.session.session_id === session.session_id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
              }`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className="font-medium text-gray-800">
                  {session.title || `Session #${session.session_number}`}
                </span>
                <span className="text-xs text-gray-400">
                  {session.message_count} msgs
                </span>
              </div>
              <div className="text-sm text-gray-500">
                {formatDate(session.started_at)}
              </div>
              <div className="flex gap-2 mt-1">
                {session.has_summary && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                    Summary
                  </span>
                )}
                {session.has_reflection && (
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                    Reflection
                  </span>
                )}
                {session.ended_at && (
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    Completed
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Session Detail Panel */}
      {selectedSession && (
        <div className="w-2/3 overflow-y-auto">
          {loadingDetail ? (
            <div className="p-8 text-center text-gray-500">
              <div className="animate-spin inline-block w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full mb-2"></div>
              <p>Loading session details...</p>
            </div>
          ) : (
            <div className="p-4">
              {/* Header */}
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-800">
                    {selectedSession.session.title || `Session #${selectedSession.session.session_number}`}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {formatDate(selectedSession.session.started_at)}
                    {selectedSession.session.ended_at && ` — ${formatDate(selectedSession.session.ended_at)}`}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedSession(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {/* Summary Section */}
              {selectedSession.summary && (
                <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200">
                  <h3 className="font-semibold text-green-800 mb-2">📝 Summary</h3>
                  <p className="text-gray-700 whitespace-pre-wrap">
                    {selectedSession.summary.summary_text}
                  </p>
                  {selectedSession.summary.key_topics && selectedSession.summary.key_topics.length > 0 && (
                    <div className="mt-3">
                      <span className="text-sm font-medium text-green-700">Key Topics: </span>
                      <span className="text-sm text-gray-600">
                        {selectedSession.summary.key_topics.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Reflection Section */}
              {selectedSession.reflection && (
                <div className="mb-6 p-4 bg-amber-50 rounded-lg border border-amber-200">
                  <h3 className="font-semibold text-amber-800 mb-2">🌟 7 Universal Values Reflection</h3>
                  <p className="text-gray-700 whitespace-pre-wrap mb-4">
                    {selectedSession.reflection.reflection_text}
                  </p>
                  
                  {/* Values Scores */}
                  <div className="mt-4">
                    <h4 className="text-sm font-semibold text-amber-700 mb-3">Values Alignment</h4>
                    {Object.entries(selectedSession.reflection.scores)
                      .filter(([key]) => key !== 'overall')
                      .map(([key, value]) => renderScoreBar(value as number, key))}
                    
                    {selectedSession.reflection.scores.overall !== undefined && (
                      <div className="mt-4 pt-3 border-t border-amber-200">
                        {renderScoreBar(selectedSession.reflection.scores.overall, 'Overall')}
                      </div>
                    )}
                  </div>

                  {/* Growth Areas */}
                  {selectedSession.reflection.growth_areas && selectedSession.reflection.growth_areas.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-semibold text-amber-700 mb-2">Areas for Growth</h4>
                      <ul className="list-disc list-inside text-sm text-gray-600">
                        {selectedSession.reflection.growth_areas.map((area, i) => (
                          <li key={i}>{area}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Conversation Transcript */}
              <div className="mb-4">
                <h3 className="font-semibold text-gray-800 mb-3">💬 Conversation</h3>
                <div className="space-y-3 max-h-96 overflow-y-auto p-3 bg-gray-50 rounded-lg">
                  {selectedSession.messages.length === 0 ? (
                    <p className="text-gray-500 text-sm">No messages in this session.</p>
                  ) : (
                    selectedSession.messages.map((msg, index) => (
                      <div 
                        key={index}
                        className={`p-3 rounded-lg ${
                          msg.role === 'user' 
                            ? 'bg-blue-100 ml-8' 
                            : msg.role === 'assistant'
                            ? 'bg-white border mr-8'
                            : 'bg-gray-200 text-sm italic'
                        }`}
                      >
                        <div className="text-xs text-gray-500 mb-1 capitalize">
                          {msg.role}
                        </div>
                        <div className="text-gray-800 whitespace-pre-wrap">
                          {msg.content}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
