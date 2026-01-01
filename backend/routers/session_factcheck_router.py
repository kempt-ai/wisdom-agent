"""
Wisdom Agent - Session FactCheck Router

API endpoints for fact-checking within sessions.

Author: Wisdom Agent Team
Date: 2025-12-21 (Phase 3)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from backend.models.session_factcheck_models import (
    TriggerFactCheckRequest,
    TriggerFactCheckResponse,
    SessionFactChecksResponse,
    SessionFactCheckSummary,
    AnalyzeMessageRequest,
    AnalyzeMessageResponse,
    DetectionResult,
    SuggestionResult
)
from backend.services.session_factcheck_service import get_session_factcheck_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Session FactCheck"])


# =========================================
# Fact-Check Endpoints
# =========================================

@router.post("/{session_id}/factcheck", response_model=TriggerFactCheckResponse)
async def trigger_factcheck(session_id: int, request: TriggerFactCheckRequest):
    """
    Trigger a fact-check within a session.
    
    Creates a new fact-check review linked to the session.
    The analysis runs asynchronously - poll the returned poll_url for status.
    
    **Example:**
    ```
    POST /api/sessions/1/factcheck
    {
        "content": "The Great Wall of China is visible from space",
        "source_type": "text"
    }
    ```
    """
    try:
        service = get_session_factcheck_service()
        
        # Determine source_url based on source_type
        source_url = None
        content = request.content
        
        if request.source_type.value == "url":
            source_url = request.source_url or request.content
            content = request.source_url or request.content
        
        result = await service.trigger_factcheck_in_session(
            session_id=session_id,
            content=content,
            source_type=request.source_type.value,
            source_url=source_url,
            title=request.title,
            auto_triggered=False
        )
        
        return TriggerFactCheckResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to trigger fact-check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/factchecks", response_model=SessionFactChecksResponse)
async def get_session_factchecks(
    session_id: int,
    include_details: bool = Query(
        default=False,
        description="Include full review details for each fact-check"
    )
):
    """
    Get all fact-checks associated with a session.
    
    Returns a list of fact-check summaries. Use include_details=true
    for full review information.
    
    **Example:**
    ```
    GET /api/sessions/1/factchecks?include_details=false
    ```
    """
    try:
        service = get_session_factcheck_service()
        
        result = await service.get_session_factchecks(
            session_id=session_id,
            include_details=include_details
        )
        
        # Convert to proper response model
        factchecks = [
            SessionFactCheckSummary(**fc) for fc in result.get("factchecks", [])
        ]
        
        return SessionFactChecksResponse(
            session_id=result["session_id"],
            factchecks=factchecks,
            total=result["total"],
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Failed to get session fact-checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/analyze-message", response_model=AnalyzeMessageResponse)
async def analyze_message_for_factcheck(
    session_id: int,
    request: AnalyzeMessageRequest
):
    """
    Analyze a message to detect fact-check opportunities.
    
    This endpoint helps the frontend/AI determine whether to:
    - Automatically trigger a fact-check (explicit request)
    - Suggest fact-checking to the user (URL or uncertain claim)
    - Do nothing (no checkworthy content)
    
    **Example:**
    ```
    POST /api/sessions/1/analyze-message
    {
        "content": "I read that vaccines cause autism"
    }
    ```
    """
    try:
        service = get_session_factcheck_service()
        
        detection = service.detect_factcheck_intent(request.content)
        suggestion = service.should_suggest_factcheck(request.content)
        
        return AnalyzeMessageResponse(
            detection=DetectionResult(**detection),
            suggestion=SuggestionResult(**suggestion)
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# Quick Actions
# =========================================

@router.post("/{session_id}/factcheck-url", response_model=TriggerFactCheckResponse)
async def factcheck_url(
    session_id: int,
    url: str = Query(..., description="URL to fact-check")
):
    """
    Quick endpoint to fact-check a URL.
    
    Convenience endpoint for URL fact-checking without JSON body.
    
    **Example:**
    ```
    POST /api/sessions/1/factcheck-url?url=https://example.com/article
    ```
    """
    try:
        service = get_session_factcheck_service()
        
        result = await service.trigger_factcheck_in_session(
            session_id=session_id,
            content=url,
            source_type="url",
            source_url=url,
            auto_triggered=False
        )
        
        return TriggerFactCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to fact-check URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/factcheck-claim", response_model=TriggerFactCheckResponse)
async def factcheck_claim(
    session_id: int,
    claim: str = Query(..., description="Claim text to fact-check", min_length=10)
):
    """
    Quick endpoint to fact-check a text claim.
    
    Convenience endpoint for claim fact-checking without JSON body.
    
    **Example:**
    ```
    POST /api/sessions/1/factcheck-claim?claim=The earth is flat
    ```
    """
    try:
        service = get_session_factcheck_service()
        
        result = await service.trigger_factcheck_in_session(
            session_id=session_id,
            content=claim,
            source_type="text",
            auto_triggered=False
        )
        
        return TriggerFactCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to fact-check claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))
