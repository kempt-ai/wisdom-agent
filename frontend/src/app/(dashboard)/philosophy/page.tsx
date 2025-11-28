'use client';

import { useState, useEffect } from 'react';
import { BookOpen, Loader2, ChevronRight, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getPhilosophy, type PhilosophyResponse } from '@/lib/api';
import { UNIVERSAL_VALUES } from '@/lib/utils';

export default function PhilosophyPage() {
  const [philosophy, setPhilosophy] = useState<PhilosophyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('overview');

  useEffect(() => {
    loadPhilosophy();
  }, []);

  const loadPhilosophy = async () => {
    try {
      setIsLoading(true);
      const data = await getPhilosophy();
      setPhilosophy(data);
    } catch (err) {
      console.error('Failed to load philosophy:', err);
      setError(err instanceof Error ? err.message : 'Failed to load philosophy');
    } finally {
      setIsLoading(false);
    }
  };

  const sections = [
    { id: 'overview', label: 'Overview' },
    { id: 'values', label: '7 Universal Values' },
    { id: 'principles', label: 'Core Principles' },
    { id: 'practice', label: 'Practice' },
  ];

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
          Philosophy
        </h1>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          The foundations of Something Deeperism
        </p>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 text-wisdom-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full">
            <p className="text-stone-500 mb-4">{error}</p>
            <button onClick={loadPhilosophy} className="btn-secondary">
              Try again
            </button>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto p-6 space-y-12">
            {/* Navigation */}
            <nav className="flex flex-wrap gap-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={cn(
                    'px-4 py-2 rounded-full text-sm transition-colors',
                    activeSection === section.id
                      ? 'bg-wisdom-600 text-white'
                      : 'bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-stone-700'
                  )}
                >
                  {section.label}
                </button>
              ))}
            </nav>

            {/* Overview Section */}
            {activeSection === 'overview' && (
              <section className="space-y-8 animate-fade-in">
                <div className="card p-8">
                  <div className="flex items-start gap-6">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-wisdom-100 to-gold-100 dark:from-wisdom-900 dark:to-gold-900 flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-8 h-8 text-wisdom-600 dark:text-wisdom-400" />
                    </div>
                    <div>
                      <h2 className="font-serif text-2xl font-medium text-stone-900 dark:text-stone-100 mb-4">
                        What is Something Deeperism?
                      </h2>
                      <div className="prose-chat text-stone-600 dark:text-stone-300 space-y-4">
                        <p>
                          Something Deeperism is a philosophical framework that approaches Truth poetically 
                          rather than literally. It recognizes that Pure Love is the foundational reality 
                          that chooses everyone.
                        </p>
                        <p>
                          The framework provides a way to engage with wisdom traditions and philosophical 
                          inquiry while remaining grounded in practical, everyday application through the 
                          7 Universal Values.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Philosophy files loaded */}
                {philosophy && philosophy.base_files.length > 0 && (
                  <div className="card p-6">
                    <h3 className="font-medium text-stone-800 dark:text-stone-200 mb-4">
                      Loaded Philosophy Files
                    </h3>
                    <div className="space-y-2">
                      {philosophy.base_files.map((file, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-3 px-4 py-3 rounded-lg bg-stone-50 dark:bg-stone-800/50"
                        >
                          <BookOpen className="w-4 h-4 text-wisdom-500" />
                          <span className="text-sm text-stone-600 dark:text-stone-300">{file}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* Values Section */}
            {activeSection === 'values' && (
              <section className="space-y-6 animate-fade-in">
                <div className="text-center mb-8">
                  <h2 className="font-serif text-2xl font-medium text-stone-900 dark:text-stone-100 mb-3">
                    The 7 Universal Values
                  </h2>
                  <p className="text-stone-500 dark:text-stone-400 max-w-xl mx-auto">
                    These values guide all interactions and provide a framework for evaluating 
                    growth and wisdom in our conversations.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {UNIVERSAL_VALUES.map((value, i) => (
                    <div
                      key={value.key}
                      className="card p-6 hover:shadow-lg transition-shadow"
                      style={{ animationDelay: `${i * 50}ms` }}
                    >
                      <div className="flex items-start gap-4">
                        <div
                          className={cn(
                            'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                            'bg-gradient-to-br from-wisdom-100 to-wisdom-200 dark:from-wisdom-900 dark:to-wisdom-800'
                          )}
                        >
                          <span className="font-serif font-medium text-wisdom-700 dark:text-wisdom-300">
                            {i + 1}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-medium text-stone-900 dark:text-stone-100 mb-1">
                            {value.label}
                          </h3>
                          <p className="text-sm text-stone-500 dark:text-stone-400">
                            {value.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Principles Section */}
            {activeSection === 'principles' && (
              <section className="space-y-6 animate-fade-in">
                <h2 className="font-serif text-2xl font-medium text-stone-900 dark:text-stone-100 mb-6">
                  Core Principles
                </h2>

                <div className="space-y-4">
                  {[
                    {
                      title: 'Pure Love as Foundation',
                      content: 'The foundational reality is Pure Love, which chooses everyone unconditionally.',
                    },
                    {
                      title: 'Poetic Truth',
                      content: 'Truth should be approached poetically rather than literally, recognizing the limits of human understanding.',
                    },
                    {
                      title: 'Wisdom Over Knowledge',
                      content: 'Wisdom is the integration of knowledge with understanding, compassion, and practical application.',
                    },
                    {
                      title: 'AI as Tool',
                      content: 'AI serves as a tool to help humans select for wisdom, not as an authority on wisdom itself.',
                    },
                    {
                      title: 'Pattern vs. Embodiment',
                      content: 'AI can recognize patterns of wisdom but cannot embody experiential wisdom as humans can.',
                    },
                  ].map((principle, i) => (
                    <div key={i} className="card p-6">
                      <h3 className="font-medium text-stone-900 dark:text-stone-100 mb-2">
                        {principle.title}
                      </h3>
                      <p className="text-stone-600 dark:text-stone-300">
                        {principle.content}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Practice Section */}
            {activeSection === 'practice' && (
              <section className="space-y-6 animate-fade-in">
                <h2 className="font-serif text-2xl font-medium text-stone-900 dark:text-stone-100 mb-6">
                  Putting It Into Practice
                </h2>

                <div className="card p-8 bg-gradient-to-br from-wisdom-50 to-gold-50 dark:from-wisdom-950 dark:to-stone-900 border-wisdom-100 dark:border-wisdom-900">
                  <div className="flex items-center gap-3 mb-4">
                    <Sparkles className="w-6 h-6 text-gold-500" />
                    <h3 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100">
                      The Two Core Questions
                    </h3>
                  </div>
                  <ol className="space-y-4">
                    <li className="flex items-start gap-4">
                      <span className="w-8 h-8 rounded-full bg-wisdom-600 text-white flex items-center justify-center flex-shrink-0 font-medium">
                        1
                      </span>
                      <p className="text-stone-700 dark:text-stone-300 pt-1">
                        How can AI best help humans select for wisdom?
                      </p>
                    </li>
                    <li className="flex items-start gap-4">
                      <span className="w-8 h-8 rounded-full bg-wisdom-600 text-white flex items-center justify-center flex-shrink-0 font-medium">
                        2
                      </span>
                      <p className="text-stone-700 dark:text-stone-300 pt-1">
                        How can AI pursue this without overstepping?
                      </p>
                    </li>
                  </ol>
                </div>

                <div className="card p-6">
                  <h3 className="font-medium text-stone-900 dark:text-stone-100 mb-4">
                    How to Use This Platform
                  </h3>
                  <ul className="space-y-3">
                    {[
                      'Create projects to organize your learning and reflection',
                      'Engage in conversations that explore questions deeply',
                      'Review session reflections to track growth over time',
                      'Use the 7 Universal Values as a guide for self-evaluation',
                      'Approach each interaction with openness and curiosity',
                    ].map((item, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <ChevronRight className="w-5 h-5 text-wisdom-500 flex-shrink-0 mt-0.5" />
                        <span className="text-stone-600 dark:text-stone-300">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
