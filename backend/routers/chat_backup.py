"""
Chat Router - API endpoints for chat functionality

Provides endpoints for:
- Simple chat completions
- Philosophy-grounded conversations
- Provider management
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


class ChatResponse(BaseModel):
    """Response from chat completion."""
    response: str
    provider: str
    model: str


class SimpleQuestion(BaseModel):
    """Simple question for quick testing."""
    question: str
    use_philosophy: bool = True


# === Endpoints ===

@router.post("/complete", response_model=ChatResponse)
async def chat_complete(request: ChatRequest):
    """
    Generate a chat completion.
    
    Optionally grounds the conversation in Something Deeperism philosophy.
    """
    llm = get_router()
    
    # Build system prompt
    system_prompt = request.system_prompt or ""
    if request.use_philosophy:
        philosophy = get_base_philosophy()
        system_prompt = f"{philosophy}\n\n{system_prompt}" if system_prompt else philosophy
    
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
            model=info.get('model', 'unknown')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", response_model=ChatResponse)
async def ask_simple(request: SimpleQuestion):
    """
    Simple endpoint for quick questions.
    
    Just send a question, get an answer (with philosophy grounding by default).
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
