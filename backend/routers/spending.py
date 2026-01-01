"""
Wisdom Agent - Spending API Router

Endpoints for spending tracking, limits, and cost estimation.

Created: December 26, 2025
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.services.spending_service import (
    get_spending_service,
    SpendingCheck,
    CostEstimate,
    SpendingSummary,
    ModelTier,
)

router = APIRouter(prefix="/spending", tags=["spending"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UpdateLimitRequest(BaseModel):
    """Request to update spending limit."""
    monthly_limit: float = Field(..., ge=0, description="New monthly limit in dollars")


class UpdateThresholdRequest(BaseModel):
    """Request to update warning threshold."""
    threshold: float = Field(..., ge=0.0, le=1.0, description="Warning threshold (0.0-1.0)")


class EstimateCostRequest(BaseModel):
    """Request to estimate operation cost."""
    input_tokens: int = Field(..., ge=0, description="Expected input tokens")
    output_tokens: int = Field(..., ge=0, description="Expected output tokens")
    model_id: Optional[str] = Field(None, description="Specific model ID")
    provider: Optional[str] = Field(None, description="Provider name if model not specified")
    operation: str = Field("general", description="Type of operation")


class RecordSpendingRequest(BaseModel):
    """Request to record a spending transaction."""
    amount: float = Field(..., ge=0, description="Cost in dollars")
    operation: str = Field(..., description="Type of operation")
    model_id: str = Field(..., description="Model used")
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class SpendingSummaryResponse(BaseModel):
    """Response with spending summary."""
    user_id: int
    month: str
    month_display: str  # "December 2025"
    total_spent: float
    limit: float
    remaining: float
    percentage_used: float
    at_warning: bool
    transaction_count: int
    breakdown_by_operation: Dict[str, float]
    breakdown_by_model: Dict[str, float]


class SpendingCheckResponse(BaseModel):
    """Response for spending check."""
    allowed: bool
    current_spending: float
    estimated_cost: float
    projected_total: float
    limit: float
    remaining: float
    at_warning: bool
    over_limit: bool
    message: str


class CostEstimateResponse(BaseModel):
    """Response for cost estimate."""
    operation: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    model_used: str
    model_tier: str
    alternatives: List[Dict[str, Any]]


class ModelInfoResponse(BaseModel):
    """Response with model information."""
    model_id: str
    display_name: str
    provider: str
    tier: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    description: str
    best_for: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/summary", response_model=SpendingSummaryResponse)
async def get_spending_summary(
    user_id: int = Query(1, description="User ID"),
    month: Optional[str] = Query(None, description="Month (YYYY-MM), defaults to current")
):
    """
    Get spending summary for a user.
    
    Returns total spent, limit, remaining budget, and breakdowns.
    """
    service = get_spending_service()
    summary = service.get_spending_summary(user_id, month)
    
    # Format month for display
    year, month_num = summary.month.split("-")
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_display = f"{month_names[int(month_num)]} {year}"
    
    return SpendingSummaryResponse(
        user_id=summary.user_id,
        month=summary.month,
        month_display=month_display,
        total_spent=round(summary.total_spent, 2),
        limit=summary.limit,
        remaining=round(summary.remaining, 2),
        percentage_used=summary.percentage_used,
        at_warning=summary.at_warning,
        transaction_count=summary.transaction_count,
        breakdown_by_operation=summary.breakdown_by_operation,
        breakdown_by_model=summary.breakdown_by_model,
    )


@router.get("/check", response_model=SpendingCheckResponse)
async def check_spending(
    user_id: int = Query(1, description="User ID"),
    estimated_cost: float = Query(..., description="Estimated cost of operation")
):
    """
    Check if user can afford an operation.
    
    Returns whether the operation is allowed and budget status.
    """
    service = get_spending_service()
    check = service.check_can_spend(user_id, estimated_cost)
    
    return SpendingCheckResponse(
        allowed=check.allowed,
        current_spending=round(check.current_spending, 2),
        estimated_cost=round(check.estimated_cost, 4),
        projected_total=round(check.projected_total, 2),
        limit=check.limit,
        remaining=round(check.remaining, 2),
        at_warning=check.at_warning,
        over_limit=check.over_limit,
        message=check.message,
    )


@router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_cost(request: EstimateCostRequest):
    """
    Estimate cost for an operation with alternatives.
    
    Provides cost for specified model and cheaper alternatives.
    """
    service = get_spending_service()
    estimate = service.estimate_cost(
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        model_id=request.model_id,
        provider=request.provider,
        operation=request.operation,
    )
    
    return CostEstimateResponse(
        operation=estimate.operation,
        input_tokens=estimate.input_tokens,
        output_tokens=estimate.output_tokens,
        total_tokens=estimate.total_tokens,
        estimated_cost=round(estimate.estimated_cost, 4),
        model_used=estimate.model_used,
        model_tier=estimate.model_tier.value,
        alternatives=estimate.alternatives[:5],  # Top 5 alternatives
    )


@router.post("/record")
async def record_spending(
    user_id: int,
    request: RecordSpendingRequest
):
    """
    Record a spending transaction.
    
    Called after LLM operations complete to track actual spending.
    """
    service = get_spending_service()
    
    history = service.record_spending(
        user_id=user_id,
        amount=request.amount,
        operation=request.operation,
        model_id=request.model_id,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        details=request.details,
    )
    
    return {
        "success": True,
        "total_spent_this_month": round(history["total_spent"], 2),
        "transaction_count": history["transaction_count"],
    }


@router.get("/history")
async def get_spending_history(
    user_id: int = Query(1, description="User ID"),
    month: Optional[str] = Query(None, description="Month (YYYY-MM)"),
    limit: int = Query(50, ge=1, le=500, description="Max transactions to return")
):
    """
    Get recent spending transactions.
    
    Returns list of transactions, most recent first.
    """
    service = get_spending_service()
    transactions = service.get_spending_history(user_id, month, limit)
    
    return {
        "transactions": transactions,
        "count": len(transactions),
    }


@router.put("/settings/limit")
async def update_spending_limit(
    user_id: int,
    request: UpdateLimitRequest
):
    """
    Update user's monthly spending limit.
    """
    service = get_spending_service()
    settings = service.update_spending_limit(user_id, request.monthly_limit)
    
    return {
        "success": True,
        "monthly_limit": settings["monthly_limit"],
        "message": f"Spending limit updated to ${settings['monthly_limit']:.2f}/month",
    }


@router.put("/settings/threshold")
async def update_warning_threshold(
    user_id: int,
    request: UpdateThresholdRequest
):
    """
    Update user's warning threshold.
    """
    service = get_spending_service()
    settings = service.update_warning_threshold(user_id, request.threshold)
    
    return {
        "success": True,
        "warning_threshold": settings["warning_threshold"],
        "message": f"Warning threshold updated to {settings['warning_threshold']*100:.0f}%",
    }


@router.get("/settings")
async def get_spending_settings(
    user_id: int = Query(1, description="User ID")
):
    """
    Get user's spending settings.
    """
    service = get_spending_service()
    settings = service.get_user_settings(user_id)
    
    return {
        "monthly_limit": settings["monthly_limit"],
        "warning_threshold": settings["warning_threshold"],
        "preferred_tier": settings.get("preferred_tier", "standard"),
    }


# ============================================================================
# MODEL INFORMATION ENDPOINTS
# ============================================================================

@router.get("/models", response_model=List[ModelInfoResponse])
async def get_available_models(
    provider: Optional[str] = Query(None, description="Filter by provider")
):
    """
    Get list of available models with pricing.
    """
    service = get_spending_service()
    models = service.get_available_models(provider)
    
    return [ModelInfoResponse(**m) for m in models]


@router.get("/models/by-tier")
async def get_models_by_tier(
    tier: str = Query(..., description="Model tier: economy, standard, or premium")
):
    """
    Get models filtered by capability tier.
    """
    try:
        tier_enum = ModelTier(tier)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: economy, standard, premium"
        )
    
    service = get_spending_service()
    models = service.get_models_by_tier(tier_enum)
    
    return {"tier": tier, "models": models}


@router.get("/models/recommend")
async def recommend_model(
    task_type: str = Query(..., description="Task type (e.g., indexing_light, chat, analysis)"),
    budget_sensitive: bool = Query(False, description="Prefer cheaper options")
):
    """
    Get model recommendation for a specific task.
    """
    service = get_spending_service()
    model_id = service.recommend_model_for_task(task_type, budget_sensitive)
    
    # Get full model info
    models = service.get_available_models()
    model_info = next((m for m in models if m["model_id"] == model_id), None)
    
    return {
        "task_type": task_type,
        "budget_sensitive": budget_sensitive,
        "recommended_model": model_id,
        "model_info": model_info,
    }


# ============================================================================
# QUICK DASHBOARD ENDPOINT
# ============================================================================

@router.get("/dashboard")
async def get_dashboard_data(
    user_id: int = Query(1, description="User ID")
):
    """
    Get all data needed for the spending dashboard widget.
    
    Single endpoint to minimize frontend API calls.
    """
    service = get_spending_service()
    summary = service.get_spending_summary(user_id)
    settings = service.get_user_settings(user_id)
    
    # Format month for display
    year, month_num = summary.month.split("-")
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_display = f"{month_names[int(month_num)]} {year}"
    
    return {
        "month": summary.month,
        "month_display": month_display,
        "total_spent": round(summary.total_spent, 2),
        "limit": summary.limit,
        "remaining": round(summary.remaining, 2),
        "percentage_used": summary.percentage_used,
        "at_warning": summary.at_warning,
        "warning_threshold_percent": int(settings["warning_threshold"] * 100),
        "transaction_count": summary.transaction_count,
        # For the sidebar widget
        "display_text": f"${summary.total_spent:.2f}",
        "display_percentage": f"{summary.percentage_used:.0f}%",
        "display_limit": f"${summary.limit:.0f}",
    }
