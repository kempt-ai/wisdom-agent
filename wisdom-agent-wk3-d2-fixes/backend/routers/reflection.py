"""
Wisdom Agent - Reflection Router

API endpoints for the self-reflection system:
- 7 Universal Values evaluation
- Session summaries
- Meta-summary (evolving wisdom journey)
- Values trend analysis
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.reflection_service import (
    get_reflection_service, 
    initialize_reflection_service,
    ReflectionService
)
from backend.services.llm_router import get_llm_router
from backend.services.philosophy_loader import get_base_philosophy


router = APIRouter(prefix="/api/reflection", tags=["reflection"])


# ========== REQUEST/RESPONSE MODELS ==========

class SessionSummaryRequest(BaseModel):
    """Request model for generating session summary."""
    session_id: int
    messages: List[Dict] = Field(..., description="Conversation messages")
    reflection_text: str = Field(default="", description="Optional prior reflection")
    include_previous: bool = Field(default=True, description="Include connections to previous sessions")


class ValuesReflectionRequest(BaseModel):
    """Request model for 7 Values reflection."""
    session_id: int
    messages: List[Dict] = Field(..., description="Conversation messages to evaluate")
    custom_rubric: Optional[str] = Field(None, description="Optional custom rubric text")


class ValuesScores(BaseModel):
    """Model for 7 Universal Values scores."""
    Awareness: int = Field(ge=0, le=10)
    Honesty: int = Field(ge=0, le=10)
    Accuracy: int = Field(ge=0, le=10)
    Competence: int = Field(ge=0, le=10)
    Compassion: int = Field(ge=0, le=10)
    Loving_kindness: int = Field(ge=0, le=10)
    Joyful_sharing: int = Field(ge=0, le=10)
    overall: float


class SaveArtifactsRequest(BaseModel):
    """Request model for saving all session artifacts."""
    session_id: int
    messages: List[Dict]
    summary_text: str
    summary_data: Dict
    reflection_text: str
    reflection_scores: Dict


class UpdateMetaSummaryRequest(BaseModel):
    """Request model for updating meta-summary."""
    session_id: int
    session_summary: Dict


# ========== SERVICE STATUS ==========

@router.get("/status")
async def reflection_status():
    """Check reflection service status."""
    service = get_reflection_service()
    
    return {
        "service": "reflection",
        "initialized": service is not None,
        "universal_values": ReflectionService.UNIVERSAL_VALUES if service else [],
        "capabilities": [
            "generate_session_summary",
            "generate_values_reflection",
            "save_session_artifacts",
            "update_meta_summary",
            "get_values_trend"
        ] if service else []
    }


@router.post("/initialize")
async def initialize_service():
    """Initialize the reflection service (requires LLM Router)."""
    llm_router = get_llm_router()
    
    if not llm_router:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not available. Initialize LLM Router first."
        )
    
    # Get philosophy text for grounding
    philosophy_text = get_base_philosophy()
    
    service = initialize_reflection_service(llm_router, philosophy_text)
    
    if not service:
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize Reflection Service"
        )
    
    return {
        "status": "initialized",
        "message": "Reflection Service ready",
        "universal_values": ReflectionService.UNIVERSAL_VALUES
    }


# ========== 7 UNIVERSAL VALUES ==========

@router.get("/values")
async def get_universal_values():
    """
    Get the 7 Universal Values used for self-reflection.
    
    These values from Something Deeperism guide all self-evaluation:
    1. Awareness - Staying present to what's actually happening
    2. Honesty - Truth-telling even when difficult
    3. Accuracy - Precision in understanding and communication
    4. Competence - Doing things well and skillfully
    5. Compassion - Meeting all beings and their suffering with care
    6. Loving-kindness - Active goodwill toward everyone
    7. Joyful-sharing - Generosity and celebration of the good
    """
    return {
        "values": ReflectionService.UNIVERSAL_VALUES,
        "descriptions": {
            "Awareness": "Staying present to what's actually happening",
            "Honesty": "Truth-telling even when difficult",
            "Accuracy": "Precision in understanding and communication",
            "Competence": "Doing things well and skillfully",
            "Compassion": "Meeting all beings and their suffering with care",
            "Loving-kindness": "Active goodwill toward everyone",
            "Joyful-sharing": "Generosity and celebration of the good"
        },
        "scale": "0-10 for each value"
    }


@router.post("/values-reflection")
async def generate_values_reflection(request: ValuesReflectionRequest):
    """
    Generate self-reflection using the 7 Universal Values rubric.
    
    This is the core self-evaluation that grounds the Wisdom Agent
    in Something Deeperism's values framework. Returns both a detailed
    text reflection and numerical scores for each value.
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized. Call /api/reflection/initialize first."
        )
    
    try:
        reflection_text, scores = service.generate_values_reflection(
            session_id=request.session_id,
            messages=request.messages,
            rubric_text=request.custom_rubric
        )
        
        return {
            "success": True,
            "session_id": request.session_id,
            "reflection_text": reflection_text,
            "scores": scores,
            "values_evaluated": ReflectionService.UNIVERSAL_VALUES
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== SESSION SUMMARY ==========

@router.post("/session-summary")
async def generate_session_summary(request: SessionSummaryRequest):
    """
    Generate a comprehensive summary of a session.
    
    Creates structured summary with:
    - Major themes
    - Key insights (user and WA)
    - Philosophical developments
    - Questions raised
    - Connections to previous sessions
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    try:
        # Optionally get previous summaries for connections
        previous_summaries = None
        if request.include_previous:
            previous_summaries = service.get_recent_summaries(n=5)
        
        summary_text, summary_data = service.generate_session_summary(
            session_id=request.session_id,
            messages=request.messages,
            reflection_text=request.reflection_text,
            previous_summaries=previous_summaries
        )
        
        return {
            "success": True,
            "session_id": request.session_id,
            "summary_text": summary_text,
            "summary_data": summary_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== SAVE ARTIFACTS ==========

@router.post("/save-artifacts")
async def save_session_artifacts(request: SaveArtifactsRequest):
    """
    Save all session artifacts (conversation, summary, reflection).
    
    Creates 6 files for each session:
    - conversation.txt / .json
    - summary.txt / .json
    - reflection.txt / .json
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    try:
        saved_files = service.save_session_artifacts(
            session_id=request.session_id,
            messages=request.messages,
            summary_text=request.summary_text,
            summary_data=request.summary_data,
            reflection_text=request.reflection_text,
            reflection_scores=request.reflection_scores
        )
        
        return {
            "success": True,
            "session_id": request.session_id,
            "saved_files": saved_files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== META-SUMMARY ==========

@router.get("/meta-summary")
async def get_meta_summary():
    """
    Get the current meta-summary (evolving wisdom journey).
    
    The meta-summary tracks:
    - Sequential record of all sessions
    - Key patterns across sessions
    - Important developments
    - Philosophical evolution
    - Ongoing questions
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    meta = service.load_meta_summary()
    
    if not meta:
        return {
            "exists": False,
            "message": "No meta-summary yet. Complete some sessions first."
        }
    
    return {
        "exists": True,
        "meta_summary": meta,
        "formatted": service.format_meta_summary_for_prompt(meta)
    }


@router.post("/meta-summary/update")
async def update_meta_summary(request: UpdateMetaSummaryRequest):
    """
    Update the meta-summary with a new session.
    
    This evolves the meta-summary by:
    - Adding to sequential record
    - Identifying new patterns
    - Tracking philosophical evolution
    - Updating ongoing questions
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    try:
        updated_meta = service.update_meta_summary(
            session_id=request.session_id,
            session_summary=request.session_summary
        )
        
        return {
            "success": True,
            "session_id": request.session_id,
            "meta_summary": updated_meta
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== RECENT SUMMARIES ==========

@router.get("/recent-summaries")
async def get_recent_summaries(n: int = Query(default=5, ge=1, le=20)):
    """Get the most recent session summaries."""
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    summaries = service.get_recent_summaries(n=n)
    
    return {
        "count": len(summaries),
        "summaries": summaries
    }


# ========== VALUES TREND ==========

@router.get("/values-trend")
async def get_values_trend(n_sessions: int = Query(default=10, ge=1, le=50)):
    """
    Analyze trends in 7 Values scores across recent sessions.
    
    Shows:
    - Average score for each value
    - Trend (improving, declining, stable)
    - Most recent score
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    trend_data = service.get_values_trend(n_sessions=n_sessions)
    
    return {
        "success": True,
        "trend_analysis": trend_data
    }


# ========== COMPLETE SESSION WORKFLOW ==========

@router.post("/complete-session")
async def complete_session(
    session_id: int,
    messages: List[Dict],
    project_context: Optional[Dict] = None
):
    """
    Complete a full session with all reflection artifacts.
    
    This endpoint handles the entire end-of-session workflow:
    1. Generate 7 Values reflection
    2. Generate session summary
    3. Save all artifacts
    4. Update meta-summary
    
    Use this for a one-call session completion.
    """
    service = get_reflection_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Reflection Service not initialized"
        )
    
    try:
        # Step 1: Generate 7 Values reflection
        reflection_text, reflection_scores = service.generate_values_reflection(
            session_id=session_id,
            messages=messages
        )
        
        # Step 2: Generate session summary
        recent = service.get_recent_summaries(n=5)
        summary_text, summary_data = service.generate_session_summary(
            session_id=session_id,
            messages=messages,
            reflection_text=reflection_text,
            previous_summaries=recent
        )
        
        # Step 3: Save all artifacts
        saved_files = service.save_session_artifacts(
            session_id=session_id,
            messages=messages,
            summary_text=summary_text,
            summary_data=summary_data,
            reflection_text=reflection_text,
            reflection_scores=reflection_scores
        )
        
        # Step 4: Update meta-summary
        meta = service.update_meta_summary(
            session_id=session_id,
            session_summary=summary_data
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "reflection_scores": reflection_scores,
            "summary_themes": summary_data.get('themes', ''),
            "saved_files": saved_files,
            "meta_summary_updated": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
