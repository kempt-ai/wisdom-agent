'use client';

import { useState, useEffect } from 'react';
import {
  Cpu,
  Zap,
  Star,
  Crown,
  DollarSign,
  Check,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ModelInfo {
  id: string;
  name: string;
  tier: string;
  description: string;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
  context_window: number;
  best_for: string[];
  provider?: string;
}

interface ProviderStatus {
  provider: string;
  enabled: boolean;
  available: boolean;
  is_active: boolean;
  current_model: string;
  model_info: ModelInfo | null;
  available_models: ModelInfo[];
}

interface ProvidersResponse {
  active_provider: string;
  providers: ProviderStatus[];
}

// Tier styling
const tierConfig: Record<string, { icon: typeof Zap; color: string; bgColor: string }> = {
  economy: { 
    icon: Zap, 
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20'
  },
  standard: { 
    icon: Star, 
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20'
  },
  premium: { 
    icon: Crown, 
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20'
  },
  free: { 
    icon: Sparkles, 
    color: 'text-stone-600 dark:text-stone-400',
    bgColor: 'bg-stone-50 dark:bg-stone-800/50'
  },
};

// Provider display names and colors
const providerConfig: Record<string, { name: string; color: string }> = {
  anthropic: { name: 'Anthropic Claude', color: 'text-orange-600' },
  openai: { name: 'OpenAI', color: 'text-green-600' },
  gemini: { name: 'Google Gemini', color: 'text-blue-600' },
  nebius: { name: 'Nebius', color: 'text-indigo-600' },
  local: { name: 'Local (Ollama)', color: 'text-stone-600' },
};

function formatCost(cost: number): string {
  if (cost === 0) return 'Free';
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  if (cost < 1) return `$${cost.toFixed(3)}`;
  return `$${cost.toFixed(2)}`;
}

function TierBadge({ tier }: { tier: string }) {
  const config = tierConfig[tier] || tierConfig.economy;
  const Icon = config.icon;
  
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
      config.bgColor,
      config.color
    )}>
      <Icon className="w-3 h-3" />
      {tier.charAt(0).toUpperCase() + tier.slice(1)}
    </span>
  );
}

function ModelCard({ 
  model, 
  isSelected, 
  onSelect,
  disabled = false 
}: { 
  model: ModelInfo; 
  isSelected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}) {
  const tierCfg = tierConfig[model.tier] || tierConfig.economy;
  
  return (
    <button
      onClick={onSelect}
      disabled={disabled}
      className={cn(
        "w-full p-4 rounded-lg border text-left transition-all duration-150",
        isSelected
          ? "border-wisdom-500 bg-wisdom-50 dark:bg-wisdom-900/20 ring-2 ring-wisdom-500"
          : "border-stone-200 dark:border-stone-700 hover:border-stone-300 dark:hover:border-stone-600",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-stone-900 dark:text-stone-100 truncate">
              {model.name}
            </h4>
            <TierBadge tier={model.tier} />
            {isSelected && (
              <span className="flex items-center gap-1 text-wisdom-600 dark:text-wisdom-400">
                <Check className="w-4 h-4" />
              </span>
            )}
          </div>
          
          {/* Description */}
          <p className="text-sm text-stone-500 dark:text-stone-400 mb-2">
            {model.description}
          </p>
          
          {/* Best for tags */}
          <div className="flex flex-wrap gap-1 mb-2">
            {model.best_for.slice(0, 3).map((use, idx) => (
              <span 
                key={idx}
                className="text-xs px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400"
              >
                {use}
              </span>
            ))}
          </div>
        </div>
        
        {/* Cost */}
        <div className="text-right flex-shrink-0">
          <div className="flex items-center gap-1 text-stone-400">
            <DollarSign className="w-3 h-3" />
            <span className="text-xs">per 1M tokens</span>
          </div>
          <div className="text-sm font-medium text-stone-700 dark:text-stone-300">
            In: {formatCost(model.input_cost_per_1m)}
          </div>
          <div className="text-sm font-medium text-stone-700 dark:text-stone-300">
            Out: {formatCost(model.output_cost_per_1m)}
          </div>
        </div>
      </div>
    </button>
  );
}

function ProviderSection({
  provider,
  isActive,
  onSetActive,
  onSelectModel,
}: {
  provider: ProviderStatus;
  isActive: boolean;
  onSetActive: () => void;
  onSelectModel: (modelId: string) => void;
}) {
  const [expanded, setExpanded] = useState(isActive);
  const config = providerConfig[provider.provider] || { name: provider.provider, color: 'text-stone-600' };
  
  if (!provider.available) {
    return (
      <div className="p-4 rounded-lg border border-stone-200 dark:border-stone-700 opacity-60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-stone-400" />
            <div>
              <h3 className={cn("font-medium", config.color)}>{config.name}</h3>
              <p className="text-sm text-stone-500">No API key configured</p>
            </div>
          </div>
          <span className="text-xs text-stone-400 px-2 py-1 rounded bg-stone-100 dark:bg-stone-800">
            Unavailable
          </span>
        </div>
      </div>
    );
  }
  
  return (
    <div className={cn(
      "rounded-lg border transition-all duration-150",
      isActive 
        ? "border-wisdom-500 bg-wisdom-50/50 dark:bg-wisdom-900/10" 
        : "border-stone-200 dark:border-stone-700"
    )}>
      {/* Provider Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <Cpu className={cn("w-5 h-5", config.color)} />
          <div>
            <div className="flex items-center gap-2">
              <h3 className={cn("font-medium", config.color)}>{config.name}</h3>
              {isActive && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-wisdom-100 dark:bg-wisdom-900/30 text-wisdom-700 dark:text-wisdom-300">
                  Active
                </span>
              )}
            </div>
            <p className="text-sm text-stone-500 dark:text-stone-400">
              Current: {provider.model_info?.name || provider.current_model}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {!isActive && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSetActive();
              }}
              className="text-xs px-3 py-1.5 rounded-lg bg-wisdom-600 text-white hover:bg-wisdom-700 transition-colors"
            >
              Set Active
            </button>
          )}
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-stone-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-stone-400" />
          )}
        </div>
      </button>
      
      {/* Models List */}
      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          <div className="border-t border-stone-200 dark:border-stone-700 pt-4 mb-3">
            <p className="text-sm text-stone-500 dark:text-stone-400 mb-3">
              Select a model for {config.name}:
            </p>
          </div>
          
          {provider.available_models.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              isSelected={provider.current_model === model.id}
              onSelect={() => onSelectModel(model.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ModelSelector() {
  const [data, setData] = useState<ProvidersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/models/providers`);
      if (response.ok) {
        const result = await response.json();
        setData(result);
        setError(null);
      } else {
        setError('Failed to load providers');
      }
    } catch (err) {
      console.error('Failed to fetch providers:', err);
      setError('Could not connect to backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSetActiveProvider = async (provider: string) => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/models/providers/active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });
      
      if (response.ok) {
        await fetchData();
      } else {
        setError('Failed to set active provider');
      }
    } catch (err) {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSelectModel = async (provider: string, modelId: string) => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/models/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId, provider }),
      });
      
      if (response.ok) {
        await fetchData();
      } else {
        setError('Failed to select model');
      }
    } catch (err) {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-serif font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-2">
          <Cpu className="w-5 h-5" />
          AI Model Selection
        </h2>
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 bg-stone-100 dark:bg-stone-800 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-serif font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-2">
          <Cpu className="w-5 h-5" />
          AI Model Selection
        </h2>
        <button
          onClick={fetchData}
          disabled={loading}
          className="p-2 text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-300">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Tier Legend */}
      <div className="p-4 bg-stone-50 dark:bg-stone-800/50 rounded-lg">
        <h3 className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">
          Model Tiers
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(tierConfig).map(([tier, cfg]) => {
            const Icon = cfg.icon;
            return (
              <div key={tier} className="flex items-center gap-2">
                <Icon className={cn("w-4 h-4", cfg.color)} />
                <div>
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300 capitalize">
                    {tier}
                  </span>
                  <p className="text-xs text-stone-500">
                    {tier === 'economy' && 'Fast & cheap'}
                    {tier === 'standard' && 'Balanced'}
                    {tier === 'premium' && 'Most capable'}
                    {tier === 'free' && 'Local/free'}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Provider Sections */}
      {data && (
        <div className="space-y-4">
          {data.providers
            .sort((a, b) => {
              // Sort: active first, then available, then unavailable
              if (a.is_active) return -1;
              if (b.is_active) return 1;
              if (a.available && !b.available) return -1;
              if (!a.available && b.available) return 1;
              return 0;
            })
            .map((provider) => (
              <ProviderSection
                key={provider.provider}
                provider={provider}
                isActive={provider.is_active}
                onSetActive={() => handleSetActiveProvider(provider.provider)}
                onSelectModel={(modelId) => handleSelectModel(provider.provider, modelId)}
              />
            ))}
        </div>
      )}

      {/* Cost Saving Tips */}
      <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
        <h3 className="font-medium text-emerald-800 dark:text-emerald-300 mb-2 flex items-center gap-2">
          <Zap className="w-4 h-4" />
          Cost-Saving Tips
        </h3>
        <ul className="text-sm text-emerald-700 dark:text-emerald-400 space-y-1">
          <li>• Use <strong>Economy</strong> models for routine tasks like summaries and simple questions</li>
          <li>• Reserve <strong>Standard</strong> models for complex analysis and writing</li>
          <li>• Use <strong>Premium</strong> only when you need the deepest reasoning</li>
          <li>• <strong>Local models</strong> are free but require your own hardware</li>
        </ul>
      </div>

      {saving && (
        <div className="fixed bottom-4 right-4 px-4 py-2 bg-stone-800 text-white rounded-lg shadow-lg flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Saving...
        </div>
      )}
    </div>
  );
}
