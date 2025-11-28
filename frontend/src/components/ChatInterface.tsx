'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { sendMessage, type Message } from '@/lib/api';
import { cn, formatTime } from '@/lib/utils';
import { Sparkles, AlertCircle, RefreshCw } from 'lucide-react';

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

export function ChatInterface({
  sessionId,
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (content: string) => {
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

      {/* Input area */}
      <div className="p-6 border-t border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-stone-950">
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          placeholder="Share your thoughts or ask a question..."
        />
      </div>
    </div>
  );
}
