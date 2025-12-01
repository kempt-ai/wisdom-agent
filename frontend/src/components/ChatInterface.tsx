'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { 
  sendMessage, 
  startSession as apiStartSession,
  addMessageToSession,
  endSession as apiEndSession,
  type Message,
  type SessionEndResult,
} from '@/lib/api';
import { cn, formatTime } from '@/lib/utils';
import { Sparkles, AlertCircle, RefreshCw, StopCircle, X, FileText, Star } from 'lucide-react';

interface ChatInterfaceProps {
  sessionId?: string;
  projectId?: string;
  initialMessages?: Message[];
  systemPrompt?: string;
  className?: string;
}

interface DisplayMessage extends Message {
  timestamp: string;
  id: string;
}

interface SessionReport {
  summary?: string;
  reflection?: {
    text: string;
    scores: Record<string, number>;
  };
}

export function ChatInterface({
  sessionId: initialSessionId,
  projectId,
  initialMessages = [],
  systemPrompt,
  className,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>(
    initialMessages.map((m, i) => ({
      ...m,
      timestamp: formatTime(new Date()),
      id: `initial-${i}`,
    }))
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [showEndSessionModal, setShowEndSessionModal] = useState(false);
  const [isEndingSession, setIsEndingSession] = useState(false);
  const [sessionReport, setSessionReport] = useState<SessionReport | null>(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Start a session when first message is sent
  const startSession = async (): Promise<number | null> => {
    try {
      const session = await apiStartSession(
        projectId ? parseInt(projectId) : 1,
        1, // user_id
        undefined, // title - auto-generated
        'general'
      );
      setSessionId(session.session_id);
      return session.session_id;
    } catch (err) {
      console.error('Failed to start session:', err);
      return null;
    }
  };

  // Save message to session
  const saveMessage = async (currentSessionId: number, role: string, content: string) => {
    try {
      await addMessageToSession(currentSessionId, role, content, true);
    } catch (err) {
      console.error('Failed to save message:', err);
    }
  };

  const handleSend = async (content: string) => {
    // Start session if needed
    let currentSessionId = sessionId;
    if (!currentSessionId && messages.length === 0) {
      currentSessionId = await startSession();
    }

    // Add user message
    const userMessage: DisplayMessage = {
      role: 'user',
      content,
      timestamp: formatTime(new Date()),
      id: `user-${Date.now()}`,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    // Save user message to session
    if (currentSessionId) {
      await saveMessage(currentSessionId, 'user', content);
    }

    try {
      // Prepare messages for API (without display metadata)
      const apiMessages: Message[] = [
        ...messages.map(({ role, content }) => ({ role, content })),
        { role: 'user', content },
      ];

      // Send to backend
      const response = await sendMessage(apiMessages, systemPrompt);

      // Add assistant response
      const assistantMessage: DisplayMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: formatTime(new Date()),
        id: `assistant-${Date.now()}`,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Save assistant message to session
      if (currentSessionId) {
        await saveMessage(currentSessionId, 'assistant', response.response);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (messages.length > 0) {
      const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user');
      if (lastUserMessage) {
        // Remove the last user message and retry
        setMessages((prev) => prev.slice(0, -1));
        handleSend(lastUserMessage.content);
      }
    }
  };

  const handleEndSession = async () => {
    if (!sessionId) {
      // No session to end, just clear messages
      setMessages([]);
      setShowEndSessionModal(false);
      return;
    }

    setIsEndingSession(true);
    setError(null);

    try {
      const result = await apiEndSession(sessionId, true, true);
      
      // Store the report
      setSessionReport({
        summary: result.summary?.summary_text,
        reflection: result.reflection ? {
          text: result.reflection.reflection_text,
          scores: result.reflection.scores,
        } : undefined,
      });
      
      // Show the report modal
      setShowEndSessionModal(false);
      setShowReportModal(true);
    } catch (err) {
      console.error('Error ending session:', err);
      setError(err instanceof Error ? err.message : 'Failed to end session');
    } finally {
      setIsEndingSession(false);
    }
  };

  const handleCloseReport = () => {
    setShowReportModal(false);
    setSessionReport(null);
    setMessages([]);
    setSessionId(null);
  };

  // Format scores for display
  const formatScores = (scores: Record<string, number>) => {
    const valueOrder = [
      'Awareness',
      'Honesty',
      'Accuracy',
      'Competence',
      'Compassion',
      'Loving-kindness',
      'Joyful-sharing',
    ];
    
    return valueOrder.map((value) => ({
      name: value,
      score: scores[value] || 0,
    }));
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6 scrollbar-hide">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-wisdom-100 to-gold-100 dark:from-wisdom-900 dark:to-gold-900 flex items-center justify-center mb-6">
              <Sparkles className="w-8 h-8 text-wisdom-600 dark:text-wisdom-400" />
            </div>
            <h2 className="text-2xl font-serif font-medium text-stone-800 dark:text-stone-200 mb-3">
              Begin Your Journey
            </h2>
            <p className="text-stone-500 dark:text-stone-400 max-w-md text-balance">
              I'm here to help you grow in wisdom through the lens of Something Deeperism. 
              What would you like to explore today?
            </p>
            <div className="mt-8 flex flex-wrap gap-3 justify-center">
              {[
                'What is Something Deeperism?',
                'Help me understand the 7 Universal Values',
                'I want to learn about wisdom',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSend(suggestion)}
                  className={cn(
                    'px-4 py-2 rounded-full text-sm',
                    'bg-stone-100 dark:bg-stone-800',
                    'text-stone-600 dark:text-stone-300',
                    'hover:bg-wisdom-100 dark:hover:bg-wisdom-900/30',
                    'hover:text-wisdom-700 dark:hover:text-wisdom-300',
                    'transition-colors duration-200'
                  )}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                timestamp={message.timestamp}
              />
            ))}
            {isLoading && (
              <ChatMessage
                role="assistant"
                content=""
                isLoading
              />
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-6 mb-4 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              <button
                onClick={handleRetry}
                className="mt-2 flex items-center gap-2 text-sm text-red-600 dark:text-red-400 hover:underline"
              >
                <RefreshCw className="w-4 h-4" />
                Retry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input area with End Session button */}
      <div className="p-6 border-t border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-stone-950">
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <ChatInput
              onSend={handleSend}
              isLoading={isLoading}
              placeholder="Share your thoughts or ask a question..."
            />
          </div>
          
          {/* End Session Button */}
          {messages.length > 0 && (
            <button
              onClick={() => setShowEndSessionModal(true)}
              disabled={isLoading}
              className={cn(
                'px-4 py-3 rounded-xl flex items-center gap-2',
                'bg-stone-200 dark:bg-stone-700',
                'text-stone-700 dark:text-stone-200',
                'hover:bg-gold-100 dark:hover:bg-gold-900/30',
                'hover:text-gold-700 dark:hover:text-gold-300',
                'transition-colors duration-200',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              title="End Session"
            >
              <StopCircle className="w-5 h-5" />
              <span className="hidden sm:inline">End Session</span>
            </button>
          )}
        </div>
      </div>

      {/* End Session Confirmation Modal */}
      {showEndSessionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-stone-900 rounded-2xl max-w-md w-full p-6 shadow-xl">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gold-100 dark:bg-gold-900/30 flex items-center justify-center">
                  <StopCircle className="w-5 h-5 text-gold-600 dark:text-gold-400" />
                </div>
                <h3 className="text-lg font-serif font-medium text-stone-900 dark:text-stone-100">
                  End Session?
                </h3>
              </div>
              <button
                onClick={() => setShowEndSessionModal(false)}
                className="text-stone-400 hover:text-stone-600 dark:hover:text-stone-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-stone-600 dark:text-stone-400 mb-6">
              This will save your conversation, generate a summary, and create a 7 Universal Values reflection report. Are you ready to conclude this session?
            </p>
            
            <div className="flex gap-3">
              <button
                onClick={() => setShowEndSessionModal(false)}
                disabled={isEndingSession}
                className={cn(
                  'flex-1 px-4 py-2 rounded-xl',
                  'bg-stone-100 dark:bg-stone-800',
                  'text-stone-700 dark:text-stone-300',
                  'hover:bg-stone-200 dark:hover:bg-stone-700',
                  'transition-colors duration-200',
                  'disabled:opacity-50'
                )}
              >
                Cancel
              </button>
              <button
                onClick={handleEndSession}
                disabled={isEndingSession}
                className={cn(
                  'flex-1 px-4 py-2 rounded-xl',
                  'bg-wisdom-600 dark:bg-wisdom-500',
                  'text-white',
                  'hover:bg-wisdom-700 dark:hover:bg-wisdom-600',
                  'transition-colors duration-200',
                  'disabled:opacity-50 flex items-center justify-center gap-2'
                )}
              >
                {isEndingSession ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4" />
                    End & Generate Report
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session Report Modal */}
      {showReportModal && sessionReport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white dark:bg-stone-900 rounded-2xl max-w-2xl w-full p-6 shadow-xl my-8">
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-wisdom-100 dark:bg-wisdom-900/30 flex items-center justify-center">
                  <Star className="w-5 h-5 text-wisdom-600 dark:text-wisdom-400" />
                </div>
                <h3 className="text-lg font-serif font-medium text-stone-900 dark:text-stone-100">
                  Session Complete
                </h3>
              </div>
              <button
                onClick={handleCloseReport}
                className="text-stone-400 hover:text-stone-600 dark:hover:text-stone-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Summary Section */}
            {sessionReport.summary && (
              <div className="mb-6">
                <h4 className="text-sm font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide mb-3">
                  Session Summary
                </h4>
                <div className="p-4 rounded-xl bg-stone-50 dark:bg-stone-800 text-stone-700 dark:text-stone-300 text-sm leading-relaxed">
                  {sessionReport.summary}
                </div>
              </div>
            )}

            {/* 7 Values Scores */}
            {sessionReport.reflection?.scores && (
              <div className="mb-6">
                <h4 className="text-sm font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wide mb-3">
                  7 Universal Values Assessment
                </h4>
                <div className="grid gap-2">
                  {formatScores(sessionReport.reflection.scores).map(({ name, score }) => (
                    <div key={name} className="flex items-center gap-3">
                      <span className="text-sm text-stone-600 dark:text-stone-400 w-32">
                        {name}
                      </span>
                      <div className="flex-1 h-2 bg-stone-200 dark:bg-stone-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-wisdom-500 dark:bg-wisdom-400 rounded-full transition-all duration-500"
                          style={{ width: `${(score / 10) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-stone-700 dark:text-stone-300 w-8 text-right">
                        {score}/10
                      </span>
                    </div>
                  ))}
                  {sessionReport.reflection.scores.overall && (
                    <div className="flex items-center gap-3 mt-2 pt-2 border-t border-stone-200 dark:border-stone-700">
                      <span className="text-sm font-medium text-stone-700 dark:text-stone-300 w-32">
                        Overall
                      </span>
                      <div className="flex-1 h-2 bg-stone-200 dark:bg-stone-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gold-500 dark:bg-gold-400 rounded-full transition-all duration-500"
                          style={{ width: `${(sessionReport.reflection.scores.overall / 10) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-gold-600 dark:text-gold-400 w-8 text-right">
                        {sessionReport.reflection.scores.overall.toFixed(1)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Close Button */}
            <button
              onClick={handleCloseReport}
              className={cn(
                'w-full px-4 py-3 rounded-xl',
                'bg-wisdom-600 dark:bg-wisdom-500',
                'text-white font-medium',
                'hover:bg-wisdom-700 dark:hover:bg-wisdom-600',
                'transition-colors duration-200'
              )}
            >
              Start New Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
