'use client';

import { cn } from '@/lib/utils';
import { Sparkles, User } from 'lucide-react';

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  isLoading?: boolean;
}

export function ChatMessage({ role, content, timestamp, isLoading }: ChatMessageProps) {
  const isUser = role === 'user';

  return (
    <div
      className={cn(
        'flex gap-4 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-wisdom-600'
            : 'bg-gradient-to-br from-gold-400 to-gold-600'
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Sparkles className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-5 py-4',
          isUser
            ? 'bg-wisdom-600 text-white'
            : 'bg-white dark:bg-stone-800 border border-stone-100 dark:border-stone-700'
        )}
      >
        {isLoading ? (
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-stone-400 rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-stone-400 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-stone-400 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-sm text-stone-500 dark:text-stone-400">Thinking...</span>
          </div>
        ) : (
          <div className={cn('prose-chat', isUser ? 'text-white' : 'text-stone-800 dark:text-stone-200')}>
            {content.split('\n').map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>
        )}

        {timestamp && (
          <div
            className={cn(
              'mt-2 text-xs',
              isUser ? 'text-wisdom-200' : 'text-stone-400 dark:text-stone-500'
            )}
          >
            {timestamp}
          </div>
        )}
      </div>
    </div>
  );
}
