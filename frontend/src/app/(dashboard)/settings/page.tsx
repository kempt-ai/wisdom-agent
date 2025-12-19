'use client';

import { useState, useEffect } from 'react';
import { getHealth, getProviders, setActiveProvider, type HealthResponse } from '@/lib/api';

interface ProviderInfo {
  id: string;
  name: string;
  model: string;
  enabled: boolean;
  available: boolean;
  max_tokens: number;
  api_key_set: boolean;
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [activeProviderId, setActiveProviderId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const healthData = await getHealth().catch(() => null);
      setHealth(healthData);
      
      const data = await getProviders().catch(() => null);
      
      if (data && typeof data === 'object') {
        const active = (data as any).active || '';
        const available = (data as any).available || [];
        const details = (data as any).details || {};
        
        setActiveProviderId(active);
        
        const providerArray: ProviderInfo[] = Object.entries(details).map(([id, info]: [string, any]) => ({
          id,
          name: info.name || id,
          model: info.model || 'Default',
          enabled: info.enabled || false,
          available: available.includes(id),
          max_tokens: info.max_tokens || 4096,
          api_key_set: available.includes(id)
        }));
        
        setProviders(providerArray);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (providerId: string) => {
    try {
      setActivating(providerId);
      setError(null);
      setSuccess(null);
      await setActiveProvider(providerId);
      setSuccess(`Switched to ${providerId} successfully!`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate provider');
    } finally {
      setActivating(null);
    }
  };

  const activeProvider = providers.find(p => p.id === activeProviderId);

  if (loading) {
    return (
      <div className="p-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl font-serif font-semibold text-stone-900 mb-2">Settings</h1>
          <p className="text-stone-500 mb-8">Configure your Wisdom Agent experience</p>
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin w-8 h-8 border-2 border-stone-300 border-t-amber-500 rounded-full"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-serif font-semibold text-stone-900 mb-2">Settings</h1>
        <p className="text-stone-500 mb-8">Configure your Wisdom Agent experience</p>

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
            {success}
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <section className="mb-8">
          <h2 className="text-lg font-semibold text-stone-800 mb-4">System Status</h2>
          <div className="bg-white border border-stone-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-stone-800">Backend Connection</p>
                <p className="text-sm text-stone-500">{health ? 'API server is running' : 'Unable to connect'}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${health?.status === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {health?.status === 'healthy' ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-lg font-semibold text-stone-800 mb-4">Choose Your AI Provider</h2>
          
          {activeProvider && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                Currently using: {activeProvider.name} ({activeProvider.model})
              </p>
            </div>
          )}

          <div className="bg-white border border-stone-200 rounded-lg divide-y">
            {providers.map((provider) => {
              const isActive = provider.id === activeProviderId;
              return (
                <div key={provider.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-stone-800 capitalize">{provider.name}</p>
                    <p className="text-sm text-stone-500">Model: {provider.model}</p>
                  </div>
                  <button
                    onClick={() => handleActivate(provider.id)}
                    disabled={isActive || !provider.api_key_set}
                    className={`px-4 py-2 rounded-lg text-sm font-medium ${
                      isActive ? 'bg-green-100 text-green-700' 
                      : !provider.api_key_set ? 'bg-stone-100 text-stone-400'
                      : 'bg-amber-500 hover:bg-amber-600 text-white'
                    }`}
                  >
                    {isActive ? 'Active' : !provider.api_key_set ? 'No API Key' : 'Use This'}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-stone-800 mb-4">About</h2>
          <div className="bg-white border border-stone-200 rounded-lg p-4">
            <p className="font-medium text-stone-800">Wisdom Agent</p>
            <p className="text-sm text-stone-500 mt-1">An AI system designed to help individuals and groups grow in wisdom.</p>
          </div>
        </section>
      </div>
    </div>
  );
}