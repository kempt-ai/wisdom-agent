"""
Wisdom Agent - Spending Service

Tracks token usage and costs across all LLM operations.
Provides spending limits, warnings, and cost estimates.

Created: December 26, 2025
"""

import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Model capability/cost tiers."""
    ECONOMY = "economy"      # Haiku, Flash, cheap models
    STANDARD = "standard"    # Sonnet, Pro, balanced models
    PREMIUM = "premium"      # Opus, most capable models


@dataclass
class ModelPricing:
    """Pricing information for a specific model."""
    provider: str
    model_id: str
    display_name: str
    tier: ModelTier
    input_cost_per_1m: float   # Cost per 1M input tokens
    output_cost_per_1m: float  # Cost per 1M output tokens
    description: str
    best_for: List[str]
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for given token counts."""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_1m
        return round(input_cost + output_cost, 6)


@dataclass
class SpendingCheck:
    """Result of checking if spending is allowed."""
    allowed: bool
    current_spending: float
    estimated_cost: float
    projected_total: float
    limit: float
    remaining: float
    at_warning: bool       # True if at/above warning threshold
    over_limit: bool       # True if would exceed limit
    message: str           # Human-readable status message


@dataclass
class CostEstimate:
    """Detailed cost estimate for an operation."""
    operation: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    model_used: str
    model_tier: ModelTier
    alternatives: List[Dict[str, Any]]  # Other models that could do this
    

@dataclass
class SpendingSummary:
    """Monthly spending summary for a user."""
    user_id: int
    month: str              # "2025-12"
    total_spent: float
    limit: float
    remaining: float
    percentage_used: float
    warning_threshold: float
    at_warning: bool
    transaction_count: int
    breakdown_by_operation: Dict[str, float]
    breakdown_by_model: Dict[str, float]


# ============================================================================
# MODEL PRICING DATABASE
# ============================================================================
# Prices as of late 2024 - should be updated periodically
# All prices in USD per 1 million tokens

MODEL_PRICING: Dict[str, ModelPricing] = {
    # Anthropic Claude Models
    "claude-3-haiku-20240307": ModelPricing(
        provider="anthropic",
        model_id="claude-3-haiku-20240307",
        display_name="Claude 3 Haiku",
        tier=ModelTier.ECONOMY,
        input_cost_per_1m=0.25,
        output_cost_per_1m=1.25,
        description="Fast and efficient for simple tasks",
        best_for=["Simple summaries", "Basic extraction", "Quick responses"]
    ),
    "claude-3-5-haiku-20241022": ModelPricing(
        provider="anthropic",
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        tier=ModelTier.ECONOMY,
        input_cost_per_1m=1.00,
        output_cost_per_1m=5.00,
        description="Improved Haiku with better reasoning",
        best_for=["Routine indexing", "Summaries", "Classification"]
    ),
    "claude-3-5-sonnet-20241022": ModelPricing(
        provider="anthropic",
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        tier=ModelTier.STANDARD,
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        description="Best balance of capability and cost",
        best_for=["Character extraction", "Analysis", "Complex summaries"]
    ),
    "claude-sonnet-4-20250514": ModelPricing(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        tier=ModelTier.STANDARD,
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        description="Latest Sonnet with improved capabilities",
        best_for=["General analysis", "Writing", "Code"]
    ),
    "claude-3-opus-20240229": ModelPricing(
        provider="anthropic",
        model_id="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        tier=ModelTier.PREMIUM,
        input_cost_per_1m=15.00,
        output_cost_per_1m=75.00,
        description="Most capable, best for complex reasoning",
        best_for=["Deep analysis", "Nuanced understanding", "Philosophy"]
    ),
    
    # Google Gemini Models
    "gemini-1.5-flash": ModelPricing(
        provider="google",
        model_id="gemini-1.5-flash",
        display_name="Gemini 1.5 Flash",
        tier=ModelTier.ECONOMY,
        input_cost_per_1m=0.075,
        output_cost_per_1m=0.30,
        description="Very fast and affordable",
        best_for=["Bulk processing", "Simple tasks", "Speed-critical"]
    ),
    "gemini-1.5-pro": ModelPricing(
        provider="google",
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        tier=ModelTier.STANDARD,
        input_cost_per_1m=1.25,
        output_cost_per_1m=5.00,
        description="Capable with long context window",
        best_for=["Long documents", "Multi-turn analysis"]
    ),
    
    # OpenAI Models
    "gpt-4o-mini": ModelPricing(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        tier=ModelTier.ECONOMY,
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        description="Affordable GPT-4 class model",
        best_for=["General tasks", "Quick responses"]
    ),
    "gpt-4o": ModelPricing(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        tier=ModelTier.STANDARD,
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        description="Powerful multimodal model",
        best_for=["Complex reasoning", "Vision tasks"]
    ),
    
    # Nebius (typically running open-source models)
    "nebius-default": ModelPricing(
        provider="nebius",
        model_id="nebius-default",
        display_name="Nebius (Llama/Mixtral)",
        tier=ModelTier.ECONOMY,
        input_cost_per_1m=0.20,
        output_cost_per_1m=0.20,
        description="Open-source models via Nebius",
        best_for=["Cost-sensitive tasks", "Experimentation"]
    ),
    
    # Local Ollama (free but uses compute)
    "ollama-local": ModelPricing(
        provider="ollama",
        model_id="ollama-local",
        display_name="Local Ollama",
        tier=ModelTier.ECONOMY,
        input_cost_per_1m=0.0,
        output_cost_per_1m=0.0,
        description="Free local models (uses your hardware)",
        best_for=["Privacy-sensitive", "Offline use", "Unlimited testing"]
    ),
}

# Default model for each provider
DEFAULT_MODELS = {
    "anthropic": "claude-3-5-sonnet-20241022",
    "google": "gemini-1.5-pro",
    "openai": "gpt-4o",
    "nebius": "nebius-default",
    "ollama": "ollama-local",
}


class SpendingService:
    """
    Manages spending tracking, limits, and cost estimation.
    
    This service:
    - Tracks all token spending per user per month
    - Enforces spending limits with warnings
    - Provides cost estimates before operations
    - Recommends cheaper alternatives when appropriate
    """
    
    DEFAULT_MONTHLY_LIMIT = 20.00       # $20/month default
    DEFAULT_WARNING_THRESHOLD = 0.80    # Warn at 80%
    
    def __init__(self, data_dir: Path):
        """
        Initialize the spending service.
        
        Args:
            data_dir: Directory for storing spending data
        """
        self.data_dir = data_dir
        self.spending_dir = data_dir / "spending"
        self.spending_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for user settings
        self._user_settings_cache: Dict[int, Dict] = {}
        
        logger.info("SpendingService initialized")
    
    # ========================================================================
    # USER SETTINGS
    # ========================================================================
    
    def _get_user_settings_path(self, user_id: int) -> Path:
        """Get path to user's spending settings file."""
        return self.spending_dir / f"user_{user_id}_settings.json"
    
    def _get_user_history_path(self, user_id: int, month: str) -> Path:
        """Get path to user's spending history for a month."""
        return self.spending_dir / f"user_{user_id}_{month}_history.json"
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Get spending settings for a user."""
        if user_id in self._user_settings_cache:
            return self._user_settings_cache[user_id]
        
        settings_path = self._get_user_settings_path(user_id)
        
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        else:
            # Create default settings
            settings = {
                "user_id": user_id,
                "monthly_limit": self.DEFAULT_MONTHLY_LIMIT,
                "warning_threshold": self.DEFAULT_WARNING_THRESHOLD,
                "preferred_tier": "standard",  # economy, standard, premium
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._save_user_settings(user_id, settings)
        
        self._user_settings_cache[user_id] = settings
        return settings
    
    def _save_user_settings(self, user_id: int, settings: Dict):
        """Save user settings to disk."""
        settings["updated_at"] = datetime.now().isoformat()
        settings_path = self._get_user_settings_path(user_id)
        
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        self._user_settings_cache[user_id] = settings
    
    def update_spending_limit(self, user_id: int, new_limit: float) -> Dict:
        """
        Update a user's monthly spending limit.
        
        Args:
            user_id: The user ID
            new_limit: New monthly limit in dollars
            
        Returns:
            Updated settings dict
        """
        if new_limit < 0:
            raise ValueError("Spending limit cannot be negative")
        
        settings = self.get_user_settings(user_id)
        settings["monthly_limit"] = new_limit
        self._save_user_settings(user_id, settings)
        
        logger.info(f"User {user_id} spending limit updated to ${new_limit:.2f}")
        return settings
    
    def update_warning_threshold(self, user_id: int, threshold: float) -> Dict:
        """
        Update warning threshold (0.0 to 1.0).
        
        Args:
            user_id: The user ID
            threshold: Percentage (0.0-1.0) at which to warn
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        settings = self.get_user_settings(user_id)
        settings["warning_threshold"] = threshold
        self._save_user_settings(user_id, settings)
        
        return settings
    
    # ========================================================================
    # SPENDING TRACKING
    # ========================================================================
    
    def _get_current_month(self) -> str:
        """Get current month string (YYYY-MM)."""
        return date.today().strftime("%Y-%m")
    
    def _load_monthly_history(self, user_id: int, month: str) -> Dict:
        """Load spending history for a specific month."""
        history_path = self._get_user_history_path(user_id, month)
        
        if history_path.exists():
            with open(history_path, 'r') as f:
                return json.load(f)
        
        return {
            "user_id": user_id,
            "month": month,
            "total_spent": 0.0,
            "transaction_count": 0,
            "transactions": [],
            "by_operation": {},
            "by_model": {},
        }
    
    def _save_monthly_history(self, user_id: int, month: str, history: Dict):
        """Save monthly history to disk."""
        history_path = self._get_user_history_path(user_id, month)
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_current_spending(self, user_id: int) -> float:
        """Get total spending for current month."""
        month = self._get_current_month()
        history = self._load_monthly_history(user_id, month)
        return history["total_spent"]
    
    def record_spending(
        self,
        user_id: int,
        amount: float,
        operation: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        details: Optional[Dict] = None
    ) -> Dict:
        """
        Record a spending transaction.
        
        Args:
            user_id: The user ID
            amount: Cost in dollars
            operation: Type of operation (e.g., "chat", "indexing", "summary")
            model_id: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            details: Optional additional details
            
        Returns:
            Updated history dict
        """
        month = self._get_current_month()
        history = self._load_monthly_history(user_id, month)
        
        # Create transaction record
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "operation": operation,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "details": details or {},
        }
        
        # Update totals
        history["total_spent"] = round(history["total_spent"] + amount, 6)
        history["transaction_count"] += 1
        history["transactions"].append(transaction)
        
        # Update breakdowns
        history["by_operation"][operation] = round(
            history["by_operation"].get(operation, 0) + amount, 6
        )
        history["by_model"][model_id] = round(
            history["by_model"].get(model_id, 0) + amount, 6
        )
        
        self._save_monthly_history(user_id, month, history)
        
        logger.debug(
            f"Recorded ${amount:.4f} for user {user_id} "
            f"({operation} with {model_id})"
        )
        
        return history
    
    # ========================================================================
    # SPENDING CHECKS & ESTIMATES
    # ========================================================================
    
    def check_can_spend(
        self,
        user_id: int,
        estimated_cost: float
    ) -> SpendingCheck:
        """
        Check if a user can afford an operation.
        
        Args:
            user_id: The user ID
            estimated_cost: Estimated cost of the operation
            
        Returns:
            SpendingCheck with approval status and details
        """
        settings = self.get_user_settings(user_id)
        current = self.get_current_spending(user_id)
        
        limit = settings["monthly_limit"]
        threshold = settings["warning_threshold"]
        
        projected = current + estimated_cost
        remaining = limit - current
        
        at_warning = (current / limit) >= threshold if limit > 0 else False
        over_limit = projected > limit
        
        # Determine message
        if over_limit:
            message = (
                f"This operation (${estimated_cost:.2f}) would exceed your "
                f"monthly limit. You've spent ${current:.2f} of ${limit:.2f}."
            )
        elif at_warning:
            message = (
                f"Warning: You've used {(current/limit)*100:.0f}% of your "
                f"monthly budget (${current:.2f} of ${limit:.2f})."
            )
        else:
            message = f"${remaining:.2f} remaining this month."
        
        return SpendingCheck(
            allowed=not over_limit,
            current_spending=current,
            estimated_cost=estimated_cost,
            projected_total=projected,
            limit=limit,
            remaining=remaining,
            at_warning=at_warning,
            over_limit=over_limit,
            message=message,
        )
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        operation: str = "general"
    ) -> CostEstimate:
        """
        Estimate cost for an operation.
        
        Args:
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens  
            model_id: Specific model (or None for provider default)
            provider: Provider name if model_id not specified
            operation: Type of operation for context
            
        Returns:
            CostEstimate with cost and alternatives
        """
        # Determine which model to use
        if model_id and model_id in MODEL_PRICING:
            pricing = MODEL_PRICING[model_id]
        elif provider and provider in DEFAULT_MODELS:
            model_id = DEFAULT_MODELS[provider]
            pricing = MODEL_PRICING[model_id]
        else:
            # Fall back to Claude Sonnet as default
            model_id = "claude-3-5-sonnet-20241022"
            pricing = MODEL_PRICING[model_id]
        
        estimated_cost = pricing.estimate_cost(input_tokens, output_tokens)
        
        # Find alternatives
        alternatives = self._find_alternatives(
            input_tokens, output_tokens, model_id, operation
        )
        
        return CostEstimate(
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=estimated_cost,
            model_used=pricing.display_name,
            model_tier=pricing.tier,
            alternatives=alternatives,
        )
    
    def _find_alternatives(
        self,
        input_tokens: int,
        output_tokens: int,
        current_model: str,
        operation: str
    ) -> List[Dict[str, Any]]:
        """Find alternative models with their costs."""
        alternatives = []
        current_pricing = MODEL_PRICING.get(current_model)
        
        if not current_pricing:
            return alternatives
        
        current_cost = current_pricing.estimate_cost(input_tokens, output_tokens)
        
        for model_id, pricing in MODEL_PRICING.items():
            if model_id == current_model:
                continue
            
            cost = pricing.estimate_cost(input_tokens, output_tokens)
            savings = current_cost - cost
            savings_percent = (savings / current_cost * 100) if current_cost > 0 else 0
            
            alternatives.append({
                "model_id": model_id,
                "display_name": pricing.display_name,
                "provider": pricing.provider,
                "tier": pricing.tier.value,
                "estimated_cost": cost,
                "savings": savings,
                "savings_percent": round(savings_percent, 1),
                "description": pricing.description,
                "best_for": pricing.best_for,
            })
        
        # Sort by cost (cheapest first)
        alternatives.sort(key=lambda x: x["estimated_cost"])
        
        return alternatives
    
    # ========================================================================
    # SUMMARIES & REPORTING
    # ========================================================================
    
    def get_spending_summary(self, user_id: int, month: Optional[str] = None) -> SpendingSummary:
        """
        Get detailed spending summary for a user.
        
        Args:
            user_id: The user ID
            month: Month to summarize (defaults to current)
            
        Returns:
            SpendingSummary with all details
        """
        if month is None:
            month = self._get_current_month()
        
        settings = self.get_user_settings(user_id)
        history = self._load_monthly_history(user_id, month)
        
        total = history["total_spent"]
        limit = settings["monthly_limit"]
        remaining = max(0, limit - total)
        percentage = (total / limit * 100) if limit > 0 else 0
        
        return SpendingSummary(
            user_id=user_id,
            month=month,
            total_spent=total,
            limit=limit,
            remaining=remaining,
            percentage_used=round(percentage, 1),
            warning_threshold=settings["warning_threshold"],
            at_warning=percentage >= (settings["warning_threshold"] * 100),
            transaction_count=history["transaction_count"],
            breakdown_by_operation=history["by_operation"],
            breakdown_by_model=history["by_model"],
        )
    
    def get_spending_history(
        self,
        user_id: int,
        month: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent spending transactions.
        
        Args:
            user_id: The user ID
            month: Month to get history for (defaults to current)
            limit: Maximum transactions to return
            
        Returns:
            List of transaction dicts (most recent first)
        """
        if month is None:
            month = self._get_current_month()
        
        history = self._load_monthly_history(user_id, month)
        transactions = history.get("transactions", [])
        
        # Return most recent first
        return list(reversed(transactions[-limit:]))
    
    # ========================================================================
    # MODEL INFORMATION
    # ========================================================================
    
    def get_available_models(self, provider: Optional[str] = None) -> List[Dict]:
        """
        Get list of available models with pricing info.
        
        Args:
            provider: Filter by provider (optional)
            
        Returns:
            List of model info dicts
        """
        models = []
        
        for model_id, pricing in MODEL_PRICING.items():
            if provider and pricing.provider != provider:
                continue
            
            models.append({
                "model_id": model_id,
                "display_name": pricing.display_name,
                "provider": pricing.provider,
                "tier": pricing.tier.value,
                "input_cost_per_1m": pricing.input_cost_per_1m,
                "output_cost_per_1m": pricing.output_cost_per_1m,
                "description": pricing.description,
                "best_for": pricing.best_for,
            })
        
        return models
    
    def get_models_by_tier(self, tier: ModelTier) -> List[Dict]:
        """Get all models of a specific tier."""
        return [
            m for m in self.get_available_models()
            if m["tier"] == tier.value
        ]
    
    def recommend_model_for_task(
        self,
        task_type: str,
        budget_sensitive: bool = False
    ) -> str:
        """
        Recommend a model for a specific task type.
        
        Args:
            task_type: Type of task (indexing_light, indexing_full, chat, etc.)
            budget_sensitive: If True, prefer cheaper options
            
        Returns:
            Recommended model_id
        """
        recommendations = {
            "indexing_light": "claude-3-5-haiku-20241022",
            "indexing_standard": "claude-3-5-sonnet-20241022",
            "indexing_full": "claude-3-5-sonnet-20241022",
            "character_extraction": "claude-3-5-sonnet-20241022",
            "summary": "claude-3-5-haiku-20241022",
            "chat": "claude-3-5-sonnet-20241022",
            "analysis": "claude-3-5-sonnet-20241022",
            "philosophy": "claude-3-opus-20240229",
        }
        
        budget_recommendations = {
            "indexing_light": "gemini-1.5-flash",
            "indexing_standard": "claude-3-5-haiku-20241022",
            "indexing_full": "claude-3-5-haiku-20241022",
            "character_extraction": "claude-3-5-haiku-20241022",
            "summary": "gemini-1.5-flash",
            "chat": "claude-3-5-haiku-20241022",
            "analysis": "claude-3-5-haiku-20241022",
            "philosophy": "claude-3-5-sonnet-20241022",
        }
        
        if budget_sensitive:
            return budget_recommendations.get(task_type, "claude-3-5-haiku-20241022")
        return recommendations.get(task_type, "claude-3-5-sonnet-20241022")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_spending_service: Optional[SpendingService] = None


def get_spending_service(data_dir: Optional[Path] = None) -> SpendingService:
    """Get or create the spending service singleton."""
    global _spending_service
    
    if _spending_service is None:
        if data_dir is None:
            # Import config to get data directory
            from backend.config import config
            data_dir = config.DATA_DIR
        
        _spending_service = SpendingService(data_dir)
    
    return _spending_service
