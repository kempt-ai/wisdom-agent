'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  isLoading = false,
  disabled = false,
  placeholder = 'Type your message...',
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isLoading && !disabled) {
      onSend(trimmedMessage);
      setMessage('');
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="relative">
      <div
        className={cn(
          'flex items-end gap-3 p-3',
          'bg-white dark:bg-stone-900 rounded-2xl',
          'border border-stone-200 dark:border-stone-700',
          'shadow-soft transition-shadow duration-200',
          'focus-within:ring-2 focus-within:ring-wisdom-500 focus-within:border-transparent'
        )}
      >
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent',
            'text-stone-900 dark:text-stone-100',
            'placeholder:text-stone-400 dark:placeholder:text-stone-500',
            'focus:outline-none',
            'min-h-[44px] max-h-[200px] py-3 px-1',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        />
        <button
          onClick={handleSubmit}
          disabled={!message.trim() || isLoading || disabled}
          className={cn(
            'flex-shrink-0 w-11 h-11 rounded-xl',
            'flex items-center justify-center',
            'transition-all duration-200',
            message.trim() && !isLoading && !disabled
              ? 'bg-wisdom-600 text-white hover:bg-wisdom-700 active:scale-95'
              : 'bg-stone-100 dark:bg-stone-800 text-stone-400',
            'disabled:cursor-not-allowed'
          )}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
      <p className="mt-2 text-xs text-center text-stone-400 dark:text-stone-500">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
