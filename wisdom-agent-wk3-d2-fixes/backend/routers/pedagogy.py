"""
Wisdom Agent - Pedagogy Router

API endpoints for pedagogical features:
- Learning plan generation
- Session type detection
- Progress tracking
- Pedagogical reflections
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.pedagogy_service import get_pedagogy_service, initialize_pedagogy_service
from backend.services.llm_router import get_llm_router


router = APIRouter(prefix="/api/pedagogy", tags=["pedagogy"])


# ========== REQUEST/RESPONSE MODELS ==========

class LearningPlanRequest(BaseModel):
    """Request model for generating a learning plan."""
    subject: str = Field(..., min_length=1, description="What to learn")
    current_level: str = Field(..., description="Current knowledge level")
    learning_goal: str = Field(..., description="What they want to achieve")
    time_commitment: str = Field(..., description="How much time they can dedicate")
    preferred_style: Optional[str] = Field(None, description="Learning style preferences")


class LearningPlanResponse(BaseModel):
    """Response model for learning plan."""
    success: bool
    subject: str
    assessment: str
    milestones: List[Dict]
    learning_path: List[str]
    resources: List[Dict]
    timeline: str
    first_session_focus: str
    created: str


class PedagogicalReflectionRequest(BaseModel):
    """Request model for pedagogical reflection."""
    session_id: int
    messages: List[Dict] = Field(..., description="Conversation messages")
    project_context: Optional[Dict] = Field(None, description="Optional project context")


class SessionTypeRequest(BaseModel):
    """Request model for detecting session type."""
    messages: List[Dict] = Field(..., description="Conversation messages to analyze")


class SessionTypeResponse(BaseModel):
    """Response model for session type detection."""
    session_type: str
    description: str


class ProgressUpdateRequest(BaseModel):
    """Request model for progress update."""
    project_context: Dict = Field(..., description="Project context with learning plan")
    recent_sessions: List[Dict] = Field(default=[], description="Recent session summaries")


class NextTopicsRequest(BaseModel):
    """Request model for next topic suggestions."""
    learning_plan: Dict = Field(..., description="The original learning plan")
    completed_topics: List[str] = Field(default=[], description="Topics already covered")
    recent_performance: Optional[Dict] = Field(None, description="Optional performance data")


# ========== SERVICE STATUS ==========

@router.get("/status")
async def pedagogy_status():
    """Check pedagogy service status."""
    service = get_pedagogy_service()
    
    return {
        "service": "pedagogy",
        "initialized": service is not None,
        "capabilities": [
            "generate_learning_plan",
            "generate_pedagogical_reflection",
            "detect_session_type",
            "generate_progress_update",
            "suggest_next_topics"
        ] if service else []
    }


@router.post("/initialize")
async def initialize_service():
    """Initialize the pedagogy service (requires LLM Router)."""
    llm_router = get_llm_router()
    
    if not llm_router:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not available. Initialize LLM Router first."
        )
    
    service = initialize_pedagogy_service(llm_router)
    
    if not service:
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize Pedagogy Service"
        )
    
    return {
        "status": "initialized",
        "message": "Pedagogy Service ready"
    }


# ========== LEARNING PLAN ==========

@router.post("/learning-plan", response_model=LearningPlanResponse)
async def generate_learning_plan(request: LearningPlanRequest):
    """
    Generate a personalized learning plan.
    
    Creates a structured plan with:
    - Assessment of starting point
    - Milestones toward the goal
    - Recommended topic sequence
    - Resources (books, videos, practice)
    - Timeline
    - First session focus
    """
    service = get_pedagogy_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Pedagogy Service not initialized. Call /api/pedagogy/initialize first."
        )
    
    try:
        plan = service.generate_learning_plan(
            subject=request.subject,
            current_level=request.current_level,
            learning_goal=request.learning_goal,
            time_commitment=request.time_commitment,
            preferred_style=request.preferred_style
        )
        
        return LearningPlanResponse(
            success=True,
            subject=plan.get('subject', request.subject),
            assessment=plan.get('assessment', ''),
            milestones=plan.get('milestones', []),
            learning_path=plan.get('learning_path', []),
            resources=plan.get('resources', []),
            timeline=plan.get('timeline', ''),
            first_session_focus=plan.get('first_session_focus', ''),
            created=plan.get('created', '')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== SESSION TYPE DETECTION ==========

@router.post("/detect-session-type", response_model=SessionTypeResponse)
async def detect_session_type(request: SessionTypeRequest):
    """
    Detect the type of session based on conversation content.
    
    Returns one of:
    - wisdom_only: Philosophical/wisdom-focused
    - learning_only: Educational/skill-building
    - mixed: Both wisdom and learning elements
    - fact_checking: Verification-focused
    - shared_contemplation: Collaborative exploration
    """
    service = get_pedagogy_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Pedagogy Service not initialized"
        )
    
    session_type = service.detect_session_type(request.messages)
    
    descriptions = {
        "wisdom_only": "Philosophical exploration and wisdom-seeking conversation",
        "learning_only": "Educational session focused on skill-building or knowledge acquisition",
        "mixed": "Combination of wisdom exploration and practical learning",
        "fact_checking": "Verification and evidence-based inquiry session",
        "shared_contemplation": "Collaborative exploration and mutual reflection"
    }
    
    return SessionTypeResponse(
        session_type=session_type,
        description=descriptions.get(session_type, "Unclassified session type")
    )


# ========== PEDAGOGICAL REFLECTION ==========

@router.post("/pedagogical-reflection")
async def generate_pedagogical_reflection(request: PedagogicalReflectionRequest):
    """
    Generate pedagogical reflection on a learning session.
    
    This provides structured analysis of:
    - What was learned
    - Current understanding levels
    - Pedagogical effectiveness
    - Next session recommendations
    - Long-term progress tracking
    """
    service = get_pedagogy_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Pedagogy Service not initialized"
        )
    
    try:
        reflection = service.generate_pedagogical_reflection(
            session_id=request.session_id,
            messages=request.messages,
            project_context=request.project_context
        )
        
        return {
            "success": True,
            "session_id": request.session_id,
            "reflection": reflection
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== PROGRESS UPDATE ==========

@router.post("/progress-update")
async def generate_progress_update(request: ProgressUpdateRequest):
    """
    Generate progress update for a learning project.
    
    Assesses:
    - Overall status (on track, ahead, behind)
    - Milestones reached
    - Current strengths
    - Areas needing focus
    - Recommended adjustments
    - Encouraging feedback
    """
    service = get_pedagogy_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Pedagogy Service not initialized"
        )
    
    try:
        progress = service.generate_progress_update(
            project_context=request.project_context,
            recent_sessions=request.recent_sessions
        )
        
        return {
            "success": True,
            "progress": progress
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== NEXT TOPICS ==========

@router.post("/suggest-next-topics")
async def suggest_next_topics(request: NextTopicsRequest):
    """
    Suggest next topics to study based on learning progress.
    
    Considers:
    - Logical progression of the subject
    - Prerequisites for upcoming topics
    - Areas that may need reinforcement
    - Student's apparent interests
    """
    service = get_pedagogy_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Pedagogy Service not initialized"
        )
    
    try:
        suggestions = service.suggest_next_topics(
            learning_plan=request.learning_plan,
            completed_topics=request.completed_topics,
            recent_performance=request.recent_performance
        )
        
        return {
            "success": True,
            "suggestions": suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
