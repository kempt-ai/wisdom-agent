"""
Chat Router - API endpoints for chat functionality

Provides endpoints for:
- Simple chat completions
- Philosophy-grounded conversations
- Provider management
- Session-aware chat with orientation context

Modified: Added session-aware chat that loads orientation context for continuity
"""

from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from backend.services.llm_router import LLMRouter, initialize_llm_router
from backend.services.philosophy_loader import get_base_philosophy

router = APIRouter()

# Lazy-loaded router instance
_llm_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Get or create the LLM router instance."""
    global _llm_router
    if _llm_router is None:
        _llm_router = initialize_llm_router()
        if _llm_router is None:
            raise HTTPException(status_code=500, detail="LLM Router not available")
    return _llm_router


# === Request/Response Models ===

class Message(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request for chat completion."""
    messages: List[Message]
    system_prompt: Optional[str] = None
    use_philosophy: bool = True
    max_tokens: Optional[int] = None
    temperature: float = 1.0
    provider: Optional[str] = None
    # New fields for session-aware chat
    session_id: Optional[int] = None
    include_orientation: bool = True


class ChatResponse(BaseModel):
    """Response from chat completion."""
    response: str
    provider: str
    model: str
    session_id: Optional[int] = None
    has_orientation_context: bool = False


class SimpleQuestion(BaseModel):
    """Simple question for quick testing."""
    question: str
    use_philosophy: bool = True


class SessionChatRequest(BaseModel):
    """Request for session-aware chat with automatic orientation."""
    session_id: int
    message: str
    use_philosophy: bool = True
    max_tokens: Optional[int] = None
    temperature: float = 1.0
    provider: Optional[str] = None


# === Helper Functions ===

def build_system_prompt(
    base_prompt: Optional[str] = None,
    use_philosophy: bool = True,
    orientation_context: Optional[str] = None
) -> str:
    """
    Build a complete system prompt with philosophy and orientation context.
    
    Args:
        base_prompt: Base system prompt (can be None)
        use_philosophy: Whether to include Something Deeperism philosophy
        orientation_context: Previous session context for continuity
        
    Returns:
        Complete system prompt string
    """
    parts = []
    
    # Add philosophy grounding first
    if use_philosophy:
        philosophy = get_base_philosophy()
        if philosophy:
            parts.append(philosophy)
    
    # Add orientation context from previous sessions
    if orientation_context:
        parts.append(orientation_context)
    
    # Add any custom system prompt
    if base_prompt:
        parts.append(base_prompt)
    
    return "\n\n".join(parts) if parts else ""


def get_session_orientation(session_id: int) -> Optional[str]:
    """
    Get orientation context for a session.
    
    Args:
        session_id: The session ID to get context for
        
    Returns:
        Orientation context string or None
    """
    try:
        from backend.services.conversation_service import get_conversation_service
        conv_service = get_conversation_service()
        
        if conv_service and conv_service.is_initialized():
            session = conv_service.get_session_info(session_id)
            if session:
                return session.get('orientation_context')
    except Exception as e:
        print(f"Warning: Could not get session orientation: {e}")
    
    return None


# === Endpoints ===

@router.post("/complete", response_model=ChatResponse)
async def chat_complete(request: ChatRequest):
    """
    Generate a chat completion.
    
    Optionally grounds the conversation in Something Deeperism philosophy
    and includes orientation context from previous sessions if session_id is provided.
    """
    llm = get_router()
    
    # Get orientation context if session_id provided
    orientation_context = None
    if request.session_id and request.include_orientation:
        orientation_context = get_session_orientation(request.session_id)
    
    # Build complete system prompt
    system_prompt = build_system_prompt(
        base_prompt=request.system_prompt,
        use_philosophy=request.use_philosophy,
        orientation_context=orientation_context
    )
    
    # Convert messages to dict format
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    try:
        response = llm.complete(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            provider=request.provider
        )
        
        info = llm.get_provider_info(request.provider)
        
        return ChatResponse(
            response=response,
            provider=info.get('name', 'unknown'),
            model=info.get('model', 'unknown'),
            session_id=request.session_id,
            has_orientation_context=orientation_context is not None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session-chat", response_model=ChatResponse)
async def session_chat(request: SessionChatRequest):
    """
    Session-aware chat endpoint.
    
    Automatically loads session history, orientation context, and manages
    message storage. This is the recommended endpoint for the main chat interface.
    """
    llm = get_router()
    
    try:
        from backend.services.conversation_service import get_conversation_service
        conv_service = get_conversation_service()
        
        if not conv_service or not conv_service.is_initialized():
            raise HTTPException(status_code=500, detail="Conversation service not available")
        
        # Get session info and orientation context
        session = conv_service.get_session_info(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
        
        orientation_context = session.get('orientation_context')
        
        # Get conversation history
        history = conv_service.get_conversation_history(request.session_id, format="simple")
        
        # Add the new user message
        conv_service.add_message(
            session_id=request.session_id,
            role="user",
            content=request.message
        )
        
        # Build messages list with history
        messages = history + [{"role": "user", "content": request.message}]
        
        # Build system prompt with philosophy and orientation
        system_prompt = build_system_prompt(
            use_philosophy=request.use_philosophy,
            orientation_context=orientation_context
        )
        
        # Generate response
        response = llm.complete(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            provider=request.provider
        )
        
        # Store assistant response
        conv_service.add_message(
            session_id=request.session_id,
            role="assistant",
            content=response
        )
        
        info = llm.get_provider_info(request.provider)
        
        return ChatResponse(
            response=response,
            provider=info.get('name', 'unknown'),
            model=info.get('model', 'unknown'),
            session_id=request.session_id,
            has_orientation_context=orientation_context is not None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", response_model=ChatResponse)
async def ask_simple(request: SimpleQuestion):
    """
    Simple endpoint for quick questions.
    
    Just send a question, get an answer (with philosophy grounding by default).
    No session tracking or orientation context.
    """
    llm = get_router()
    
    system_prompt = ""
    if request.use_philosophy:
        system_prompt = get_base_philosophy()
    
    try:
        response = llm.complete(
            messages=[{"role": "user", "content": request.question}],
            system_prompt=system_prompt
        )
        
        info = llm.get_provider_info()
        
        return ChatResponse(
            response=response,
            provider=info.get('name', 'unknown'),
            model=info.get('model', 'unknown')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers():
    """List available LLM providers."""
    llm = get_router()
    
    available = llm.get_available_providers()
    all_providers = list(llm.provider_config['providers'].keys())
    
    return {
        "active": llm.active_provider,
        "available": available,
        "configured": all_providers,
        "details": {
            provider: llm.get_provider_info(provider)
            for provider in all_providers
        }
    }


@router.post("/providers/{provider}/activate")
async def activate_provider(provider: str):
    """Set the active LLM provider."""
    llm = get_router()
    
    try:
        llm.set_active_provider(provider)
        return {
            "success": True,
            "active_provider": provider,
            "info": llm.get_provider_info(provider)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/session/{session_id}/orientation")
async def get_session_orientation_context(session_id: int):
    """
    Get the orientation context for a session.
    
    Useful for debugging or displaying the context to users.
    """
    try:
        from backend.services.conversation_service import get_conversation_service
        conv_service = get_conversation_service()
        
        if not conv_service or not conv_service.is_initialized():
            raise HTTPException(status_code=500, detail="Conversation service not available")
        
        session = conv_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        orientation = session.get('orientation_context')
        
        return {
            "session_id": session_id,
            "has_orientation": orientation is not None,
            "orientation_context": orientation,
            "context_length": len(orientation) if orientation else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/refresh-orientation")
async def refresh_session_orientation(session_id: int):
    """
    Refresh/regenerate the orientation context for a session.
    
    Useful if previous sessions have been completed since this session started.
    """
    try:
        from backend.services.conversation_service import get_conversation_service
        conv_service = get_conversation_service()
        
        if not conv_service or not conv_service.is_initialized():
            raise HTTPException(status_code=500, detail="Conversation service not available")
        
        session = conv_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Generate fresh orientation context
        new_orientation = conv_service.get_session_orientation_context()
        
        # Update the session
        if session_id in conv_service._sessions:
            conv_service._sessions[session_id]['orientation_context'] = new_orientation
            conv_service._save_sessions_index()
        
        return {
            "session_id": session_id,
            "success": True,
            "has_orientation": new_orientation is not None,
            "context_length": len(new_orientation) if new_orientation else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
