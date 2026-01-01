"""
Wisdom Agent - Model Selection API Router

Endpoints for viewing and selecting LLM models across providers.

Created: December 26, 2025
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from services.llm_router import get_llm_router

router = APIRouter(prefix="/models", tags=["models"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SetModelRequest(BaseModel):
    """Request to set active model for a provider."""
    model_id: str = Field(..., description="Model identifier to use")
    provider: Optional[str] = Field(None, description="Provider (defaults to active)")


class SetProviderRequest(BaseModel):
    """Request to set active provider."""
    provider: str = Field(..., description="Provider name")


class ModelInfo(BaseModel):
    """Model information response."""
    id: str
    name: str
    tier: str
    description: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    context_window: int
    best_for: List[str]
    provider: Optional[str] = None


class ProviderStatus(BaseModel):
    """Provider status response."""
    provider: str
    enabled: bool
    available: bool
    is_active: bool
    current_model: str
    model_info: Optional[Dict[str, Any]]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/providers")
async def get_providers():
    """
    Get list of all providers and their status.
    
    Returns provider availability, current model, and whether it's active.
    """
    llm = get_llm_router()
    statuses = llm.get_all_providers_status()
    
    return {
        "active_provider": llm.active_provider,
        "providers": statuses
    }


@router.get("/providers/{provider}")
async def get_provider_details(provider: str):
    """
    Get detailed information about a specific provider.
    
    Includes all available models with full metadata.
    """
    llm = get_llm_router()
    
    info = llm.get_provider_info(provider)
    if not info:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
    
    return info


@router.post("/providers/active")
async def set_active_provider(request: SetProviderRequest):
    """
    Set the active LLM provider.
    """
    llm = get_llm_router()
    
    try:
        llm.set_active_provider(request.provider)
        return {
            "success": True,
            "active_provider": request.provider,
            "message": f"Active provider set to {request.provider}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_all_models(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    tier: Optional[str] = Query(None, description="Filter by tier (economy, standard, premium)")
):
    """
    List all available models across all or specific providers.
    
    Optionally filter by tier for budget-conscious selection.
    """
    llm = get_llm_router()
    
    if provider:
        models = llm.get_models(provider)
        models = [{"provider": provider, **m} for m in models]
    else:
        # Get models from all providers
        models = []
        for p in llm.get_available_providers():
            p_models = llm.get_models(p)
            models.extend([{"provider": p, **m} for m in p_models])
    
    # Filter by tier if specified
    if tier:
        models = [m for m in models if m.get('tier') == tier]
    
    # Sort by cost (cheapest first)
    models.sort(key=lambda m: m.get('input_cost_per_1m', 0) + m.get('output_cost_per_1m', 0))
    
    return {
        "count": len(models),
        "models": models
    }


@router.get("/current")
async def get_current_model(
    provider: Optional[str] = Query(None, description="Provider (defaults to active)")
):
    """
    Get the currently selected model.
    
    Returns full model info including costs.
    """
    llm = get_llm_router()
    
    try:
        current = llm.get_current_model(provider)
        return current
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/select")
async def select_model(request: SetModelRequest):
    """
    Select a specific model for a provider.
    
    This becomes the default model for that provider.
    """
    llm = get_llm_router()
    
    # Verify model exists
    model_info = llm.get_model_info(request.model_id, request.provider)
    
    try:
        llm.set_model(request.model_id, request.provider)
        
        return {
            "success": True,
            "provider": request.provider or llm.active_provider,
            "model_id": request.model_id,
            "model_info": model_info,
            "message": f"Model set to {request.model_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/info/{model_id}")
async def get_model_info(
    model_id: str,
    provider: Optional[str] = Query(None, description="Provider to search in")
):
    """
    Get detailed information about a specific model.
    """
    llm = get_llm_router()
    
    info = llm.get_model_info(model_id, provider)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    
    return info


@router.get("/compare")
async def compare_models(
    models: str = Query(..., description="Comma-separated model IDs"),
    input_tokens: int = Query(1000, description="Expected input tokens"),
    output_tokens: int = Query(500, description="Expected output tokens")
):
    """
    Compare costs for multiple models.
    
    Helps users choose the most cost-effective option.
    """
    llm = get_llm_router()
    model_ids = [m.strip() for m in models.split(",")]
    
    comparisons = []
    for model_id in model_ids:
        info = llm.get_model_info(model_id)
        if info:
            input_cost = (input_tokens / 1_000_000) * info.get('input_cost_per_1m', 0)
            output_cost = (output_tokens / 1_000_000) * info.get('output_cost_per_1m', 0)
            total_cost = input_cost + output_cost
            
            comparisons.append({
                "model_id": model_id,
                "name": info.get('name'),
                "provider": info.get('provider'),
                "tier": info.get('tier'),
                "estimated_cost": round(total_cost, 6),
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
            })
    
    # Sort by cost
    comparisons.sort(key=lambda x: x['estimated_cost'])
    
    # Calculate savings vs most expensive
    if comparisons:
        max_cost = max(c['estimated_cost'] for c in comparisons)
        for c in comparisons:
            c['savings_vs_max'] = round(max_cost - c['estimated_cost'], 6)
            c['savings_percent'] = round((1 - c['estimated_cost'] / max_cost) * 100, 1) if max_cost > 0 else 0
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "comparisons": comparisons
    }


@router.get("/recommend")
async def recommend_model(
    task: str = Query(..., description="Task type: chat, indexing, summary, analysis, philosophy"),
    budget_sensitive: bool = Query(False, description="Prefer cheaper options")
):
    """
    Get model recommendation for a specific task.
    """
    llm = get_llm_router()
    
    # Task to tier mapping
    task_requirements = {
        'chat': {'min_tier': 'economy', 'preferred': 'standard'},
        'indexing_light': {'min_tier': 'economy', 'preferred': 'economy'},
        'indexing_full': {'min_tier': 'standard', 'preferred': 'standard'},
        'summary': {'min_tier': 'economy', 'preferred': 'economy'},
        'analysis': {'min_tier': 'standard', 'preferred': 'standard'},
        'philosophy': {'min_tier': 'standard', 'preferred': 'premium'},
        'character_extraction': {'min_tier': 'standard', 'preferred': 'standard'},
    }
    
    req = task_requirements.get(task, {'min_tier': 'economy', 'preferred': 'standard'})
    target_tier = req['min_tier'] if budget_sensitive else req['preferred']
    
    # Get models of appropriate tier from active provider
    models = llm.get_models()
    tier_models = [m for m in models if m.get('tier') == target_tier]
    
    # If no models in target tier, try adjacent tiers
    if not tier_models:
        tier_models = models
    
    # Sort by cost and pick cheapest suitable
    tier_models.sort(key=lambda m: m.get('input_cost_per_1m', 0))
    
    recommendation = tier_models[0] if tier_models else None
    
    # Also suggest alternatives
    alternatives = []
    for tier in ['economy', 'standard', 'premium']:
        tier_options = [m for m in models if m.get('tier') == tier]
        if tier_options:
            cheapest = min(tier_options, key=lambda m: m.get('input_cost_per_1m', 0))
            alternatives.append({
                'tier': tier,
                'model': cheapest,
            })
    
    return {
        "task": task,
        "budget_sensitive": budget_sensitive,
        "recommendation": recommendation,
        "alternatives": alternatives,
        "active_provider": llm.active_provider,
    }


@router.get("/tiers")
async def get_model_tiers():
    """
    Get explanation of model tiers.
    """
    return {
        "tiers": [
            {
                "name": "economy",
                "display_name": "Economy",
                "description": "Fast and affordable for simple tasks",
                "typical_cost_range": "$0.05 - $1.00 per 1M tokens",
                "best_for": ["Quick responses", "Simple summaries", "High volume tasks"],
                "examples": ["Claude Haiku", "Gemini Flash", "GPT-4o Mini"],
            },
            {
                "name": "standard",
                "display_name": "Standard",
                "description": "Best balance of capability and cost",
                "typical_cost_range": "$1.00 - $15.00 per 1M tokens",
                "best_for": ["Complex analysis", "Writing", "Code generation"],
                "examples": ["Claude Sonnet", "Gemini Pro", "GPT-4o"],
            },
            {
                "name": "premium",
                "display_name": "Premium",
                "description": "Most capable for complex reasoning",
                "typical_cost_range": "$15.00 - $75.00 per 1M tokens",
                "best_for": ["Deep analysis", "Philosophy", "Nuanced understanding"],
                "examples": ["Claude Opus", "o1"],
            },
            {
                "name": "free",
                "display_name": "Free (Local)",
                "description": "Local models with no API cost",
                "typical_cost_range": "$0.00 (uses your hardware)",
                "best_for": ["Privacy", "Offline use", "Unlimited testing"],
                "examples": ["Ollama models"],
            },
        ]
    }
