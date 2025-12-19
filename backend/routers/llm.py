"""LLM Router - API endpoints for LLM provider management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.services.llm_router import get_llm_router

router = APIRouter(prefix="/api/llm", tags=["LLM"])


class SetProviderRequest(BaseModel):
    provider: str


class SetModelRequest(BaseModel):
    provider: str
    model: str


@router.get("/providers")
async def get_providers():
    """Get all LLM providers and their status."""
    llm = get_llm_router()
    if not llm:
        raise HTTPException(status_code=503, detail="LLM Router not initialized")
    return llm.get_all_providers_info()


@router.post("/provider")
async def set_provider(request: SetProviderRequest):
    """Set the active LLM provider."""
    llm = get_llm_router()
    if not llm:
        raise HTTPException(status_code=503, detail="LLM Router not initialized")
    try:
        llm.set_active_provider(request.provider)
        return {"status": "ok", "active": request.provider}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/model")
async def set_model(request: SetModelRequest):
    """Set the model for a provider."""
    llm = get_llm_router()
    if not llm:
        raise HTTPException(status_code=503, detail="LLM Router not initialized")
    try:
        llm.set_provider_model(request.provider, request.model)
        return {"status": "ok", "provider": request.provider, "model": request.model}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    llm = get_llm_router()
    available = llm.get_available_providers() if llm else []
    return {
        "status": "ok" if llm else "degraded",
        "llm_initialized": llm is not None,
        "available_providers": available
    }
