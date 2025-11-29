'use client';

import { useState, useEffect } from 'react';
import {
  Settings,
  Cpu,
  Check,
  AlertCircle,
  Loader2,
  Server,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getProviders, setActiveProvider, getHealth, type HealthResponse } from '@/lib/api';

interface ProviderDetails {
  name: string;
  model: string;
  enabled: boolean;
  available: boolean;
  max_tokens: number;
}

interface ProvidersResponse {
  active: string;
  available: string[];
  configured: string[];
  details: Record<string, ProviderDetails>;
}

export default function SettingsPage() {
  const [providersData, setProvidersData] = useState<ProvidersResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activatingProvider, setActivatingProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setIsLoading(true);
      const [provData, healthData] = await Promise.all([
        getProviders().catch((err) => {
          console.error('Failed to load providers:', err);
          return null;
        }),
        getHealth().catch(() => null),
      ]);
      setProvidersData(provData as ProvidersResponse);
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateProvider = async (providerId: string) => {
    try {
      setActivatingProvider(providerId);
      await setActiveProvider(providerId);
      // Reload providers to get updated state
      const updatedProviders = await getProviders();
      setProvidersData(updatedProviders as ProvidersResponse);
    } catch (err) {
      console.error('Failed to activate provider:', err);
      setError(err instanceof Error ? err.message : 'Failed to activate provider');
    } finally {
      setActivatingProvider(null);
    }
  };

  // Get providers list from the details object
  const providers = providersData?.details 
    ? Object.entries(providersData.details).map(([id, details]) => ({
        id,
        name: details.name,
        model: details.model,
        enabled: id === providersData.active,
        available: details.available,
        api_key_set: providersData.configured.includes(id),
      }))
    : [];

  return (
    <div className="h-full flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900">
        <h1 className="font-serif text-xl font-medium text-stone-900 dark:text-stone-100">
          Settings
        </h1>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          Configure your Wisdom Agent experience
        </p>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-wisdom-500 animate-spin" />
          </div>
        ) : (
          <div className="max-w-2xl mx-auto space-y-8">
            {/* System Status */}
            <section>
              <h2 className="font-medium text-stone-800 dark:text-stone-200 mb-4 flex items-center gap-2">
                <Server className="w-5 h-5" />
                System Status
              </h2>
              <div className="card p-6">
                {health ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                      <div>
                        <p className="font-medium text-stone-800 dark:text-stone-200">
                          Backend Connected
                        </p>
                        <p className="text-sm text-stone-500 dark:text-stone-400">
                          Version {health.version || '0.1.0'}
                        </p>
                      </div>
                    </div>
                    <span className="text-sm text-green-600 dark:text-green-400">
                      {health.status}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <div>
                      <p className="font-medium text-stone-800 dark:text-stone-200">
                        Backend Disconnected
                      </p>
                      <p className="text-sm text-stone-500 dark:text-stone-400">
                        Unable to connect to the server
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* LLM Providers */}
            <section>
              <h2 className="font-medium text-stone-800 dark:text-stone-200 mb-4 flex items-center gap-2">
                <Cpu className="w-5 h-5" />
                LLM Providers
              </h2>

              {error && (
                <div className="mb-4 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                    <AlertCircle className="w-5 h-5" />
                    <p className="text-sm">{error}</p>
                  </div>
                </div>
              )}

              {providers.length === 0 ? (
                <div className="card p-6 text-center">
                  <p className="text-stone-500 dark:text-stone-400">
                    No LLM providers configured. Add API keys to your .env file.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {providers.map((provider) => (
                    <div
                      key={provider.id}
                      className={cn(
                        'card p-4 flex items-center justify-between',
                        'transition-colors duration-200',
                        provider.enabled && 'border-wisdom-200 dark:border-wisdom-800 bg-wisdom-50/50 dark:bg-wisdom-900/10'
                      )}
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={cn(
                            'w-10 h-10 rounded-xl flex items-center justify-center',
                            provider.enabled
                              ? 'bg-wisdom-100 dark:bg-wisdom-900/50'
                              : 'bg-stone-100 dark:bg-stone-800'
                          )}
                        >
                          <Cpu
                            className={cn(
                              'w-5 h-5',
                              provider.enabled
                                ? 'text-wisdom-600 dark:text-wisdom-400'
                                : 'text-stone-500'
                            )}
                          />
                        </div>
                        <div>
                          <p className="font-medium text-stone-800 dark:text-stone-200 capitalize">
                            {provider.name}
                          </p>
                          <p className="text-sm text-stone-500 dark:text-stone-400">
                            {provider.model}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {!provider.available && (
                          <span className="px-2 py-1 rounded-full text-xs bg-stone-100 dark:bg-stone-800 text-stone-500">
                            Not available
                          </span>
                        )}
                        {provider.enabled ? (
                          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm bg-wisdom-100 dark:bg-wisdom-900/50 text-wisdom-700 dark:text-wisdom-300">
                            <Check className="w-4 h-4" />
                            Active
                          </span>
                        ) : (
                          <button
                            onClick={() => handleActivateProvider(provider.id)}
                            disabled={!provider.available || activatingProvider === provider.id}
                            className={cn(
                              'px-3 py-1.5 rounded-lg text-sm transition-colors',
                              provider.available
                                ? 'bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-stone-700'
                                : 'bg-stone-50 dark:bg-stone-900 text-stone-400 cursor-not-allowed'
                            )}
                          >
                            {activatingProvider === provider.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              'Activate'
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">
                Active provider: <span className="font-medium capitalize">{providersData?.active || 'None'}</span>
              </p>
            </section>

            {/* About */}
            <section>
              <h2 className="font-medium text-stone-800 dark:text-stone-200 mb-4 flex items-center gap-2">
                <Settings className="w-5 h-5" />
                About
              </h2>
              <div className="card p-6">
                <h3 className="font-serif text-lg font-medium text-stone-900 dark:text-stone-100 mb-2">
                  Wisdom Agent
                </h3>
                <p className="text-sm text-stone-600 dark:text-stone-300 mb-4">
                  An AI companion for growing in wisdom through Something Deeperism philosophy.
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="px-2 py-1 rounded-full text-xs bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400">
                    v0.1.0
                  </span>
                  <span className="px-2 py-1 rounded-full text-xs bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400">
                    Open Source
                  </span>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
