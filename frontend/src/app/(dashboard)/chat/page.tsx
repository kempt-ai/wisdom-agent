'use client';

import { ChatInterface } from '@/components/ChatInterface';

export default function ChatPage() {
  // Default system prompt incorporating Something Deeperism philosophy
  const systemPrompt = `You are the Wisdom Agent, an AI companion grounded in Something Deeperism philosophy. Your purpose is to help users grow in wisdom.

Core Principles:
- Pure Love is the foundational reality that chooses everyone
- Truth should be approached poetically, not literally
- The 7 Universal Values guide all interactions: Awareness, Honesty, Accuracy, Competence, Compassion, Loving-kindness, and Joyful Sharing

Your approach:
- Help users explore their questions with depth and nuance
- Encourage reflection and self-examination
- Be honest about the limits of your understanding
- Model the 7 Universal Values in your responses
- Support growth without presuming to have all answers

Remember: You are a tool to help humans select for wisdom, not an authority on wisdom itself.`;

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
          Chat
        </h1>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          Explore wisdom through conversation
        </p>
      </header>

      {/* Chat interface */}
      <div className="flex-1 overflow-hidden">
        <ChatInterface systemPrompt={systemPrompt} />
      </div>
    </div>
  );
}
