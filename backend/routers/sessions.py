"""
Wisdom Agent - Sessions API Router

API endpoints for session and conversation management.

Author: Wisdom Agent Team
Date: 2025-11-24
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from backend.services.conversation_service import get_conversation_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ===========================================
# Request/Response Models
# ===========================================

class StartSessionRequest(BaseModel):
    """Request model for starting a new session."""
    project_id: int = Field(..., description="ID of the project")
    user_id: int = Field(default=1, description="ID of the user")
    title: Optional[str] = Field(None, description="Optional session title")
    session_type: str = Field(default="general", description="Type of session")
    llm_provider: Optional[str] = Field(None, description="LLM provider")
    llm_model: Optional[str] = Field(None, description="LLM model")


class AddMessageRequest(BaseModel):
    """Request model for adding a message."""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    store_in_memory: bool = Field(default=True, description="Store in vector memory")


class EndSessionRequest(BaseModel):
    """Request model for ending a session."""
    generate_summary: bool = Field(default=True, description="Generate summary")
    generate_reflection: bool = Field(default=True, description="Generate reflection")


class SessionResponse(BaseModel):
    """Response model for session information."""
    session_id: int
    session_number: int
    project_id: int
    user_id: int
    title: Optional[str]
    session_type: str
    llm_provider: Optional[str]
    llm_model: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    message_count: int
    has_summary: Optional[bool] = None
    has_reflection: Optional[bool] = None


class MessageResponse(BaseModel):
    """Response model for message information."""
    message_id: int
    session_id: int
    role: str
    content: str
    message_index: int
    created_at: str


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    session_id: int
    messages: List[Dict[str, str]]


class SummaryResponse(BaseModel):
    """Response model for session summary."""
    session_id: int
    summary_text: str
    key_topics: List[str]
    learning_outcomes: List[str]
    created_at: str
    updated_at: str


class ReflectionResponse(BaseModel):
    """Response model for session reflection."""
    session_id: int
    reflection_text: str
    scores: Dict[str, float]
    insights: List[str]
    growth_areas: List[str]
    created_at: str
    updated_at: str


# ===========================================
# Service Management
# ===========================================

@router.post("/initialize")
async def initialize_service():
    """Initialize the conversation service."""
    service = get_conversation_service()
    success = service.initialize()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize conversation service")
    
    return {"status": "initialized", "message": "Conversation service initialized successfully"}


@router.get("/status")
async def get_status():
    """Get service status and statistics."""
    service = get_conversation_service()
    return service.get_status()


# ===========================================
# Session Management
# ===========================================

@router.post("/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest):
    """
    Start a new conversation session.
    
    Creates a new session in the database and returns session information.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.start_session(
        project_id=request.project_id,
        user_id=request.user_id,
        title=request.title,
        session_type=request.session_type,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to start session")
    
    return SessionResponse(**result)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int):
    """
    Get detailed information about a session.
    
    Includes message count, summary/reflection status, and session metadata.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.get_session_info(session_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return SessionResponse(**result)


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip")
):
    """
    List sessions with optional filters.
    
    Can filter by project_id or user_id. Returns sessions in reverse chronological order.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not project_id and not user_id:
        raise HTTPException(status_code=400, detail="Must provide either project_id or user_id")
    
    results = service.list_sessions(
        project_id=project_id,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return [SessionResponse(**r) for r in results]


@router.post("/{session_id}/end")
async def end_session(session_id: int, request: EndSessionRequest):
    """
    End a session and optionally generate summary and reflection.
    
    Marks the session as ended and can automatically generate
    summary and philosophical reflection with 7 Universal Values scores.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.end_session(
        session_id=session_id,
        generate_summary=request.generate_summary,
        generate_reflection=request.generate_reflection
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to end session")
    
    return result


@router.delete("/{session_id}")
async def delete_session(session_id: int):
    """
    Delete a session.
    
    Cascades to all messages, summary, and reflection.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    success = service.session_repo.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    
    return {"status": "deleted", "session_id": session_id}


# ===========================================
# Message Management
# ===========================================

@router.post("/{session_id}/messages", response_model=MessageResponse)
async def add_message(session_id: int, request: AddMessageRequest):
    """
    Add a message to a session.
    
    Stores the message in the database and optionally in vector memory
    for semantic search.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.add_message(
        session_id=session_id,
        role=request.role,
        content=request.content,
        store_in_memory=request.store_in_memory
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to add message")
    
    return MessageResponse(**result)


@router.get("/{session_id}/messages", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: int,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of messages")
):
    """
    Get conversation history for a session.
    
    Returns messages in chronological order, formatted for LLM use.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    messages = service.get_conversation_history(session_id, limit=limit, format="dict")
    
    return ConversationHistoryResponse(
        session_id=session_id,
        messages=messages
    )


# ===========================================
# Summary & Reflection
# ===========================================

@router.get("/{session_id}/summary", response_model=SummaryResponse)
async def get_summary(session_id: int):
    """
    Get session summary.
    
    Returns the AI-generated summary if it exists.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.get_summary(session_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Summary not found for session {session_id}")
    
    return SummaryResponse(**result)


@router.post("/{session_id}/summary", response_model=SummaryResponse)
async def generate_summary(
    session_id: int,
    force_regenerate: bool = Query(False, description="Force regeneration if summary exists")
):
    """
    Generate or retrieve session summary.
    
    Generates a new summary using the LLM if one doesn't exist,
    or returns existing summary. Use force_regenerate=true to regenerate.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.generate_summary(session_id, force_regenerate=force_regenerate)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate summary")
    
    return SummaryResponse(**result)


@router.get("/{session_id}/reflection", response_model=ReflectionResponse)
async def get_reflection(session_id: int):
    """
    Get session reflection with 7 Universal Values scores.
    
    Returns the philosophical reflection if it exists.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.get_reflection(session_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Reflection not found for session {session_id}")
    
    return ReflectionResponse(**result)


@router.post("/{session_id}/reflection", response_model=ReflectionResponse)
async def generate_reflection(
    session_id: int,
    force_regenerate: bool = Query(False, description="Force regeneration if reflection exists")
):
    """
    Generate or retrieve session reflection.
    
    Generates a philosophical reflection with 7 Universal Values scores
    if one doesn't exist, or returns existing reflection.
    Use force_regenerate=true to regenerate.
    """
    service = get_conversation_service()
    
    if not service.is_initialized():
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = service.generate_reflection(session_id, force_regenerate=force_regenerate)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate reflection")
    
    return ReflectionResponse(**result)
