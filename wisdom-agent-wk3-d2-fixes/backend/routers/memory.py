"""
Wisdom Agent - Memory Router

API endpoints for memory/vector search operations.
Supports both PostgreSQL (primary) and ChromaDB (fallback) backends.
"""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Import hybrid service (Week 2)
from backend.services.hybrid_memory_service import (
    get_hybrid_memory_service,
    initialize_hybrid_memory_service
)


router = APIRouter(prefix="/api/memory", tags=["memory"])


# ========== REQUEST/RESPONSE MODELS ==========

class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., description="Search query text")
    n_results: int = Field(default=3, ge=1, le=20, description="Number of results")
    search_type: Optional[str] = Field(default=None, description="Filter by type: conversation, reflection")
    session_type: Optional[str] = Field(default=None, description="Filter by session type")
    project: Optional[str] = Field(default=None, description="Filter by project name")


class StoreRequest(BaseModel):
    """Request model for storing content."""
    content: str = Field(..., description="Text content to store")
    session_id: int = Field(..., description="Session identifier")
    content_type: str = Field(default="conversation", description="Type: conversation, reflection")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class SearchResult(BaseModel):
    """Single search result."""
    embedding_id: Optional[str] = None
    id: Optional[int] = None  # PostgreSQL memory ID
    session_id: Optional[int] = None
    type: Optional[str] = None
    session_type: Optional[str] = None
    project: Optional[str] = None
    similarity_score: Optional[float] = None
    similarity: Optional[float] = None  # Alternative field name
    distance: Optional[float] = None  # For PostgreSQL cosine distance
    text_preview: Optional[str] = None
    content: Optional[str] = None  # Full content for PostgreSQL
    metadata: Optional[Dict] = None


class SearchResponse(BaseModel):
    """Response model for search operations."""
    results: List[SearchResult]
    query: str
    count: int


class StoreResponse(BaseModel):
    """Response model for store operations."""
    embedding_id: str
    success: bool
    message: str


class StatsResponse(BaseModel):
    """Response model for stats endpoint."""
    total_documents: int
    by_type: Dict[str, int]
    by_session_type: Dict[str, int]
    total_projects: int
    projects: List[str]


# ========== ENDPOINTS ==========

@router.get("/status")
async def memory_status():
    """Check if memory service is available and which backend is being used."""
    memory = get_hybrid_memory_service()
    if memory and memory._initialized:
        status = memory.get_status()
        return {
            "status": "available",
            "initialized": True,
            "backend": status.get('backend'),
            **status
        }
    return {
        "status": "not_initialized",
        "initialized": False,
        "message": "Memory service not yet initialized. Call POST /api/memory/initialize first."
    }


@router.post("/initialize")
async def initialize_memory():
    """Initialize the hybrid memory service (loads embedding model)."""
    memory = initialize_hybrid_memory_service()
    if memory:
        status = memory.get_status()
        return {
            "success": True,
            "message": f"Memory service initialized with {status.get('backend')} backend",
            "backend": status.get('backend'),
            **status
        }
    raise HTTPException(
        status_code=500,
        detail="Failed to initialize memory service. Check logs for details."
    )


@router.post("/search", response_model=SearchResponse)
async def search_memory(request: SearchRequest):
    """
    Search for semantically similar sessions.
    
    Returns sessions ordered by semantic similarity to the query.
    """
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized. Call POST /api/memory/initialize first."
        )
    
    try:
        results = memory.search_similar(
            query=request.query,
            n_results=request.n_results,
            session_type=request.session_type,
            project=request.project
        )
        
        return SearchResponse(
            results=[SearchResult(**r) for r in results],
            query=request.query,
            count=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store", response_model=StoreResponse)
async def store_content(request: StoreRequest):
    """
    Store content in the vector database.
    
    Generates embedding and stores for future semantic search.
    """
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized. Call POST /api/memory/initialize first."
        )
    
    try:
        metadata = {
            **request.metadata,
            "type": request.content_type,
            "session_id": request.session_id
        }
        
        embedding_id = memory.store_memory(request.content, metadata)
        
        return StoreResponse(
            embedding_id=embedding_id,
            success=True,
            message=f"Content stored with ID: {embedding_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_memory_stats():
    """Get statistics about the memory database."""
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized. Call POST /api/memory/initialize first."
        )
    
    try:
        # Try to get stats from backend
        if hasattr(memory.backend, 'get_stats'):
            stats = memory.backend.get_stats()
            return StatsResponse(
                total_documents=stats.get('total_documents', 0),
                by_type=stats.get('by_type', {}),
                by_session_type=stats.get('by_session_type', {}),
                total_projects=stats.get('total_projects', 0),
                projects=stats.get('projects', [])
            )
        else:
            # PostgreSQL backend doesn't have this method yet
            return StatsResponse(
                total_documents=0,
                by_type={},
                by_session_type={},
                total_projects=0,
                projects=[]
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def list_projects():
    """Get list of all projects in memory."""
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized"
        )
    
    try:
        if hasattr(memory.backend, 'get_all_projects'):
            projects = memory.backend.get_all_projects()
        else:
            projects = []  # PostgreSQL backend needs this implemented
        
        return {
            "projects": projects,
            "count": len(projects)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_name}")
async def get_project_sessions(project_name: str, n_results: int = 10):
    """Get sessions for a specific project."""
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized"
        )
    
    try:
        sessions = memory.get_project_memories(project_name, n_results=n_results)
        return {
            "project": project_name,
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_name}/context")
async def get_project_context(project_name: str, n_recent: int = 5):
    """Get formatted context string for a project (for prompts)."""
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized"
        )
    
    try:
        if hasattr(memory.backend, 'get_project_context'):
            context = memory.backend.get_project_context(project_name, n_recent=n_recent)
        else:
            # Build context from project memories
            memories = memory.get_project_memories(project_name, n_results=n_recent)
            context = "\n\n".join([m.get('content', '')[:200] for m in memories])
        
        return {
            "project": project_name,
            "context": context,
            "n_recent": n_recent
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_memory_endpoint(session_id: int):
    """Get memory entries for a specific session."""
    memory = get_hybrid_memory_service()
    if not memory or not memory._initialized:
        raise HTTPException(
            status_code=503,
            detail="Memory service not initialized"
        )
    
    try:
        entries = memory.get_session_memory(session_id)
        
        # Try to get embeddings if backend supports it
        embedding_ids = {}
        if hasattr(memory.backend, 'get_session_embeddings'):
            embeddings = memory.backend.get_session_embeddings(session_id)
            embedding_ids = {
                "conversation": embeddings[0],
                "wisdom_reflection": embeddings[1],
                "pedagogical_reflection": embeddings[2]
            }
        
        return {
            "session_id": session_id,
            "entries": entries,
            "embedding_ids": embedding_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
