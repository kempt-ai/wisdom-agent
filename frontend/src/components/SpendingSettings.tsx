'use client';

import { useState, useEffect } from 'react';
import {
  DollarSign,
  AlertTriangle,
  TrendingUp,
  PieChart,
  Save,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SpendingSummary {
  month_display: string;
  total_spent: number;
  limit: number;
  remaining: number;
  percentage_used: number;
  at_warning: boolean;
  warning_threshold_percent: number;
  transaction_count: number;
}

interface SpendingHistory {
  timestamp: string;
  amount: number;
  operation: string;
  model_id: string;
  input_tokens: number;
  output_tokens: number;
}

interface SpendingSettings {
  monthly_limit: number;
  warning_threshold: number;
}

export function SpendingSettingsSection() {
  const [summary, setSummary] = useState<SpendingSummary | null>(null);
  const [settings, setSettings] = useState<SpendingSettings | null>(null);
  const [history, setHistory] = useState<SpendingHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [newLimit, setNewLimit] = useState<string>('');
  const [newThreshold, setNewThreshold] = useState<string>('');

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch summary
      const summaryRes = await fetch(`${API_BASE}/spending/dashboard?user_id=1`);
      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }

      // Fetch settings
      const settingsRes = await fetch(`${API_BASE}/spending/settings?user_id=1`);
      if (settingsRes.ok) {
        const data = await settingsRes.json();
        setSettings(data);
        setNewLimit(data.monthly_limit.toString());
        setNewThreshold((data.warning_threshold * 100).toString());
      }

      // Fetch recent history
      const historyRes = await fetch(`${API_BASE}/spending/history?user_id=1&limit=10`);
      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data.transactions || []);
      }

      setError(null);
    } catch (err) {
      console.error('Failed to fetch spending data:', err);
      setError('Could not load spending data. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveLimit = async () => {
    const limit = parseFloat(newLimit);
    if (isNaN(limit) || limit < 0) {
      setError('Please enter a valid limit');
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/spending/settings/limit?user_id=1`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monthly_limit: limit }),
      });

      if (response.ok) {
        await fetchData();
        setError(null);
      } else {
        setError('Failed to update limit');
      }
    } catch (err) {
      setError('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveThreshold = async () => {
    const threshold = parseFloat(newThreshold) / 100;
    if (isNaN(threshold) || threshold < 0 || threshold > 1) {
      setError('Please enter a valid percentage (0-100)');
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/spending/settings/threshold?user_id=1`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold }),
      });

      if (response.ok) {
        await fetchData();
        setError(null);
      } else {
        setError('Failed to update threshold');
      }
    } catch (err) {
      setError('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-serif font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-2">
          <DollarSign className="w-5 h-5" />
          Spending & Budget
        </h2>
        <div className="h-48 bg-stone-100 dark:bg-stone-800 rounded-lg animate-pulse" />
      </div>
    );
  }

  const getBarColor = () => {
    if (!summary) return 'bg-emerald-500';
    if (summary.percentage_used >= 100) return 'bg-red-500';
    if (summary.at_warning) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  return (
    <div id="spending" className="space-y-6 scroll-mt-8">
      <h2 className="text-xl font-serif font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-2">
        <DollarSign className="w-5 h-5" />
        Spending & Budget
      </h2>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Current Month Summary */}
      {summary && (
        <div className="p-6 bg-white dark:bg-stone-800 rounded-xl border border-stone-200 dark:border-stone-700 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-stone-900 dark:text-stone-100">
              {summary.month_display}
            </h3>
            <button
              onClick={fetchData}
              className="p-2 text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Big number display */}
          <div className="flex items-baseline gap-2 mb-4">
            <span className="text-4xl font-bold text-stone-900 dark:text-stone-100">
              ${summary.total_spent.toFixed(2)}
            </span>
            <span className="text-lg text-stone-500 dark:text-stone-400">
              / ${summary.limit.toFixed(0)}
            </span>
          </div>

          {/* Progress bar */}
          <div className="h-3 bg-stone-200 dark:bg-stone-700 rounded-full overflow-hidden mb-2">
            <div
              className={cn("h-full rounded-full transition-all duration-500", getBarColor())}
              style={{ width: `${Math.min(summary.percentage_used, 100)}%` }}
            />
          </div>

          <div className="flex justify-between text-sm">
            <span className="text-stone-500 dark:text-stone-400">
              {summary.percentage_used.toFixed(1)}% used
            </span>
            <span className="text-stone-500 dark:text-stone-400">
              ${summary.remaining.toFixed(2)} remaining
            </span>
          </div>

          {summary.at_warning && (
            <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex items-center gap-2 text-amber-700 dark:text-amber-300">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm">
                You've used {summary.percentage_used.toFixed(0)}% of your monthly budget
              </span>
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-stone-200 dark:border-stone-700">
            <p className="text-sm text-stone-500 dark:text-stone-400">
              {summary.transaction_count} operations this month
            </p>
          </div>
        </div>
      )}

      {/* Budget Settings */}
      <div className="p-6 bg-white dark:bg-stone-800 rounded-xl border border-stone-200 dark:border-stone-700 shadow-sm space-y-6">
        <h3 className="font-medium text-stone-900 dark:text-stone-100">
          Budget Settings
        </h3>

        {/* Monthly Limit */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-stone-700 dark:text-stone-300">
            Monthly Spending Limit
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400">$</span>
              <input
                type="number"
                min="0"
                step="5"
                value={newLimit}
                onChange={(e) => setNewLimit(e.target.value)}
                className={cn(
                  "w-full pl-8 pr-4 py-2 rounded-lg border",
                  "bg-white dark:bg-stone-900",
                  "border-stone-300 dark:border-stone-600",
                  "text-stone-900 dark:text-stone-100",
                  "focus:ring-2 focus:ring-wisdom-500 focus:border-transparent"
                )}
              />
            </div>
            <button
              onClick={handleSaveLimit}
              disabled={saving}
              className={cn(
                "px-4 py-2 rounded-lg font-medium",
                "bg-wisdom-600 text-white",
                "hover:bg-wisdom-700",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-colors duration-150"
              )}
            >
              <Save className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            Operations that would exceed this limit will be blocked until you increase it
          </p>
        </div>

        {/* Warning Threshold */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-stone-700 dark:text-stone-300">
            Warning Threshold
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="number"
                min="0"
                max="100"
                step="5"
                value={newThreshold}
                onChange={(e) => setNewThreshold(e.target.value)}
                className={cn(
                  "w-full pl-4 pr-8 py-2 rounded-lg border",
                  "bg-white dark:bg-stone-900",
                  "border-stone-300 dark:border-stone-600",
                  "text-stone-900 dark:text-stone-100",
                  "focus:ring-2 focus:ring-wisdom-500 focus:border-transparent"
                )}
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400">%</span>
            </div>
            <button
              onClick={handleSaveThreshold}
              disabled={saving}
              className={cn(
                "px-4 py-2 rounded-lg font-medium",
                "bg-wisdom-600 text-white",
                "hover:bg-wisdom-700",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-colors duration-150"
              )}
            >
              <Save className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            You'll see a warning when spending reaches this percentage of your limit
          </p>
        </div>
      </div>

      {/* Recent Activity */}
      {history.length > 0 && (
        <div className="p-6 bg-white dark:bg-stone-800 rounded-xl border border-stone-200 dark:border-stone-700 shadow-sm">
          <h3 className="font-medium text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Recent Activity
          </h3>
          
          <div className="space-y-3">
            {history.slice(0, 5).map((tx, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between py-2 border-b border-stone-100 dark:border-stone-700 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium text-stone-700 dark:text-stone-300 capitalize">
                    {tx.operation.replace(/_/g, ' ')}
                  </p>
                  <p className="text-xs text-stone-500 dark:text-stone-400">
                    {tx.model_id} • {(tx.input_tokens + tx.output_tokens).toLocaleString()} tokens
                  </p>
                </div>
                <span className="text-sm font-medium text-stone-900 dark:text-stone-100">
                  ${tx.amount.toFixed(4)}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-stone-200 dark:border-stone-700">
            <a
              href="/settings/spending-history"
              className="text-sm text-wisdom-600 dark:text-wisdom-400 hover:underline"
            >
              View full history →
            </a>
          </div>
        </div>
      )}

      {/* Info box about how spending works */}
      <div className="p-6 bg-stone-50 dark:bg-stone-800/50 rounded-xl border border-stone-200 dark:border-stone-700">
        <h3 className="font-medium text-stone-900 dark:text-stone-100 mb-3 flex items-center gap-2">
          <PieChart className="w-4 h-4" />
          How Spending Works
        </h3>
        <div className="space-y-2 text-sm text-stone-600 dark:text-stone-400">
          <p>
            <strong>Chat conversations:</strong> Each message costs based on the model used and tokens processed.
          </p>
          <p>
            <strong>Knowledge Base indexing:</strong> Costs vary by index depth. Light indexing is cheapest; full indexing costs more but enables richer search.
          </p>
          <p>
            <strong>Fact checking:</strong> Uses tokens for claim extraction, search, and analysis.
          </p>
          <p className="mt-3 pt-3 border-t border-stone-200 dark:border-stone-700">
            💡 <strong>Tip:</strong> Using economy-tier models like Claude Haiku or Gemini Flash for routine tasks can save 80-90% compared to premium models.
          </p>
        </div>
      </div>
    </div>
  );
}
