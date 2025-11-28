"""
Wisdom Agent - Projects Router

API endpoints for project management operations.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services import get_project_service, initialize_project_service


router = APIRouter(prefix="/api/projects", tags=["projects"])


# ========== REQUEST/RESPONSE MODELS ==========

class ProjectCreate(BaseModel):
    """Request model for creating a project."""
    name: str = Field(..., min_length=1, max_length=100)
    project_type: str = Field(default="learning")
    description: str = Field(default="")
    learning_goal: Optional[str] = None


class ResourceAdd(BaseModel):
    """Request model for adding a resource."""
    resource_type: str = Field(..., description="Type: file, url, book, article")
    title: str
    location: str
    notes: Optional[str] = None


class JournalEntryAdd(BaseModel):
    """Request model for adding a journal entry."""
    content: str
    entry_type: str = Field(default="reflection")


class ProgressUpdate(BaseModel):
    """Request model for updating progress."""
    key: str
    value: Any


class SessionAdd(BaseModel):
    """Request model for adding a session to project."""
    session_id: int
    session_type: str = Field(default="learning")
    summary: Optional[str] = None


class LearningPlanUpdate(BaseModel):
    """Request model for updating learning plan."""
    learning_plan: Dict


class ThemeCreate(BaseModel):
    """Request model for creating a theme."""
    theme_name: str
    description: str = ""
    parent_theme: Optional[str] = None
    auto_generated: bool = False


class ProjectSummary(BaseModel):
    """Summary view of a project."""
    name: str
    type: str
    description: str
    sessions_count: int
    resources_count: int
    last_updated: str


class ProjectOutline(BaseModel):
    """Full outline of a project."""
    name: str
    type: str
    description: str
    created: str
    sessions_count: int
    resources_count: int
    journal_entries_count: int
    learning_plan: Optional[Dict]
    progress: Dict
    last_updated: str


# ========== HELPER ==========

def get_service():
    """Get initialized project service or raise error."""
    service = get_project_service()
    if not service:
        service = initialize_project_service()
    if not service:
        raise HTTPException(status_code=503, detail="Project service unavailable")
    return service


# ========== ENDPOINTS ==========

@router.get("/")
async def list_projects() -> List[ProjectSummary]:
    """List all projects."""
    service = get_service()
    projects = service.list_projects()
    return [ProjectSummary(**p) for p in projects]


@router.post("/")
async def create_project(request: ProjectCreate):
    """Create a new project."""
    service = get_service()
    
    try:
        project = service.create_project(
            name=request.name,
            project_type=request.project_type,
            description=request.description,
            learning_goal=request.learning_goal
        )
        return {
            "success": True,
            "message": f"Project '{request.name}' created",
            "project": project.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_name}")
async def get_project(project_name: str):
    """Get project details."""
    service = get_service()
    project = service.load_project(project_name)
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    
    return project.to_dict()


@router.get("/{project_name}/outline")
async def get_project_outline(project_name: str) -> ProjectOutline:
    """Get structured project outline."""
    service = get_service()
    outline = service.get_project_outline(project_name)
    
    if not outline:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    
    return ProjectOutline(**outline)


@router.delete("/{project_name}")
async def delete_project(project_name: str):
    """Delete a project."""
    service = get_service()
    
    if service.delete_project(project_name):
        return {
            "success": True,
            "message": f"Project '{project_name}' deleted"
        }
    
    raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")


# ========== SESSIONS ==========

@router.post("/{project_name}/sessions")
async def add_session(project_name: str, request: SessionAdd):
    """Add a session to a project."""
    service = get_service()
    
    if service.add_session_to_project(
        session_id=request.session_id,
        session_type=request.session_type,
        summary=request.summary,
        project_name=project_name
    ):
        return {
            "success": True,
            "message": f"Session {request.session_id} added to project"
        }
    
    raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")


@router.get("/{project_name}/sessions")
async def get_sessions(project_name: str):
    """Get all sessions for a project."""
    service = get_service()
    project = service.load_project(project_name)
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    
    return {
        "project": project_name,
        "sessions": project.sessions,
        "count": len(project.sessions)
    }


# ========== RESOURCES ==========

@router.post("/{project_name}/resources")
async def add_resource(project_name: str, request: ResourceAdd):
    """Add a resource to a project."""
    service = get_service()
    
    if service.add_resource(
        resource_type=request.resource_type,
        title=request.title,
        location=request.location,
        notes=request.notes,
        project_name=project_name
    ):
        return {
            "success": True,
            "message": f"Resource '{request.title}' added to project"
        }
    
    raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")


@router.get("/{project_name}/resources")
async def get_resources(project_name: str):
    """Get all resources for a project."""
    service = get_service()
    resources = service.get_project_resources(project_name)
    
    return {
        "project": project_name,
        "resources": resources,
        "count": len(resources)
    }


# ========== JOURNAL ==========

@router.post("/{project_name}/journal")
async def add_journal_entry(project_name: str, request: JournalEntryAdd):
    """Add a journal entry to a project."""
    service = get_service()
    
    if service.add_journal_entry(
        content=request.content,
        entry_type=request.entry_type,
        project_name=project_name
    ):
        return {
            "success": True,
            "message": "Journal entry added"
        }
    
    raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")


@router.get("/{project_name}/journal")
async def get_journal_entries(project_name: str):
    """Get all journal entries for a project."""
    service = get_service()
    entries = service.get_journal_entries(project_name)
    
    return {
        "project": project_name,
        "entries": entries,
        "count": len(entries)
    }


# ========== PROGRESS ==========

@router.post("/{project_name}/progress")
async def update_progress(project_name: str, request: ProgressUpdate):
    """Update project progress."""
    service = get_service()
    
    if service.update_progress(
        key=request.key,
        value=request.value,
        project_name=project_name
    ):
        return {
            "success": True,
            "message": f"Progress '{request.key}' updated"
        }
    
    raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")


@router.get("/{project_name}/progress")
async def get_progress(project_name: str):
    """Get project progress."""
    service = get_service()
    project = service.load_project(project_name)
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    
    return {
        "project": project_name,
        "progress": project.progress
    }


# ========== LEARNING PLAN ==========

@router.put("/{project_name}/learning-plan")
async def update_learning_plan(project_name: str, request: LearningPlanUpdate):
    """Update project learning plan."""
    service = get_service()
    
    if service.update_learning_plan(
        learning_plan=request.learning_plan,
        project_name=project_name
    ):
        return {
            "success": True,
            "message": "Learning plan updated"
        }
    
    raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")


@router.get("/{project_name}/learning-plan")
async def get_learning_plan(project_name: str):
    """Get project learning plan."""
    service = get_service()
    project = service.load_project(project_name)
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    
    return {
        "project": project_name,
        "learning_plan": project.learning_plan
    }


# ========== THEMES ==========

@router.get("/themes/all")
async def get_all_themes():
    """Get all knowledge base themes."""
    service = get_service()
    return service.get_themes()


@router.post("/themes")
async def create_theme(request: ThemeCreate):
    """Create a new theme."""
    service = get_service()
    
    if service.add_theme(
        theme_name=request.theme_name,
        description=request.description,
        parent_theme=request.parent_theme,
        auto_generated=request.auto_generated
    ):
        return {
            "success": True,
            "message": f"Theme '{request.theme_name}' created"
        }
    
    raise HTTPException(status_code=400, detail=f"Theme '{request.theme_name}' already exists")
