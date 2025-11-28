"""
Wisdom Agent - Hybrid Project Service (Week 2 Day 5)

Unified project service that uses PostgreSQL as primary backend
with file-based fallback for compatibility.

Features:
- PostgreSQL for production (scalable, multi-user)
- File-based fallback for development/compatibility
- Automatic backend selection
- Same interface for both backends
"""

from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from backend.config import config

# Try to import PostgreSQL backend
try:
    from backend.services.project_repository import ProjectRepository
    POSTGRES_AVAILABLE = True
except ImportError:
    ProjectRepository = None
    POSTGRES_AVAILABLE = False

# Try to import file-based backend (original)
try:
    from backend.services.project_service import ProjectService as FileProjectService
    FILE_BACKEND_AVAILABLE = True
except ImportError:
    FileProjectService = None
    FILE_BACKEND_AVAILABLE = False

logger = logging.getLogger(__name__)


class HybridProjectService:
    """
    Hybrid project service that uses PostgreSQL or file-based storage.
    
    Backend Priority:
    1. PostgreSQL (if database connection available)
    2. File-based (fallback for development)
    
    This provides a unified interface regardless of backend.
    """
    
    def __init__(self, prefer_postgres: bool = True):
        """
        Initialize hybrid project service.
        
        Args:
            prefer_postgres: If True, prefer PostgreSQL when available
        """
        self.prefer_postgres = prefer_postgres
        self.postgres_backend: Optional[ProjectRepository] = None
        self.file_backend: Optional[FileProjectService] = None
        self.active_backend: str = "none"
        self._initialized = False
        self._default_user_id = 1  # Default user for single-user mode
        
    def initialize(self) -> bool:
        """
        Initialize the appropriate backend.
        
        Returns:
            bool: True if at least one backend initialized successfully
        """
        success = False
        
        # Try PostgreSQL first if preferred
        if self.prefer_postgres and POSTGRES_AVAILABLE:
            try:
                self.postgres_backend = ProjectRepository()
                if self.postgres_backend.initialize():
                    self.active_backend = "postgresql"
                    logger.info("✅ HybridProjectService using PostgreSQL backend")
                    success = True
                else:
                    logger.warning("PostgreSQL backend failed to initialize")
                    self.postgres_backend = None
            except Exception as e:
                logger.warning(f"Could not initialize PostgreSQL backend: {e}")
                self.postgres_backend = None
        
        # Try file-based backend as fallback
        if not success and FILE_BACKEND_AVAILABLE:
            try:
                self.file_backend = FileProjectService()
                self.active_backend = "file"
                logger.info("✅ HybridProjectService using file-based backend")
                success = True
            except Exception as e:
                logger.warning(f"Could not initialize file backend: {e}")
                self.file_backend = None
        
        self._initialized = success
        
        if not success:
            logger.error("❌ No project backend available!")
            
        return success
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the active backend."""
        return {
            "active_backend": self.active_backend,
            "postgres_available": self.postgres_backend is not None,
            "file_available": self.file_backend is not None,
            "initialized": self._initialized
        }
    
    # ===========================================
    # Project CRUD Operations
    # ===========================================
    
    def create_project(
        self,
        name: str,
        project_type: str = "learning",
        description: str = "",
        learning_goal: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new project.
        
        Args:
            name: Project name
            project_type: Type of project (learning, research, wisdom)
            description: Project description
            learning_goal: Learning objective
            user_id: User ID (for multi-user support)
            
        Returns:
            Project data dict or None if failed
        """
        user_id = user_id or self._default_user_id
        
        if self.postgres_backend:
            try:
                # Map project_type to SessionType
                from backend.database.models import SessionType
                session_type_map = {
                    "learning": SessionType.TECHNICAL_LEARNING,
                    "research": SessionType.GENERAL,
                    "wisdom": SessionType.PHILOSOPHY,
                    "language": SessionType.LANGUAGE_LEARNING
                }
                session_type = session_type_map.get(project_type, SessionType.GENERAL)
                
                project = self.postgres_backend.create_project(
                    name=name,
                    user_id=user_id,
                    description=description,
                    session_type=session_type,
                    learning_goal=learning_goal
                )
                if project:
                    return self.postgres_backend.project_to_dict(project)
            except Exception as e:
                logger.error(f"PostgreSQL create_project failed: {e}")
                
        if self.file_backend:
            try:
                project = self.file_backend.create_project(
                    name=name,
                    project_type=project_type,
                    description=description
                )
                if project:
                    # Add learning_goal if provided
                    if learning_goal:
                        self.file_backend.update_project_progress(
                            name, "learning_goal", learning_goal
                        )
                    return self.file_backend.get_project(name)
            except Exception as e:
                logger.error(f"File backend create_project failed: {e}")
                
        return None
    
    def get_project(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        slug: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a project by ID, name, or slug.
        
        Args:
            project_id: Project database ID
            name: Project name
            slug: Project slug
            
        Returns:
            Project data dict or None if not found
        """
        if self.postgres_backend:
            try:
                project = None
                if project_id:
                    project = self.postgres_backend.get_project(project_id)
                elif slug:
                    project = self.postgres_backend.get_project_by_slug(
                        user_id=self._default_user_id, 
                        slug=slug
                    )
                elif name:
                    # Search by name
                    projects = self.postgres_backend.search_projects(query=name, limit=1)
                    if projects:
                        project = projects[0]
                        
                if project:
                    return self.postgres_backend.project_to_dict(project)
            except Exception as e:
                logger.error(f"PostgreSQL get_project failed: {e}")
                
        if self.file_backend and name:
            try:
                return self.file_backend.get_project(name)
            except Exception as e:
                logger.error(f"File backend get_project failed: {e}")
                
        return None
    
    def list_projects(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all projects.
        
        Args:
            user_id: Filter by user (for multi-user support)
            limit: Maximum number of projects to return
            offset: Number of projects to skip
            
        Returns:
            List of project data dicts
        """
        user_id = user_id or self._default_user_id
        
        if self.postgres_backend:
            try:
                projects = self.postgres_backend.get_projects_by_user(
                    user_id=user_id,
                    limit=limit,
                    offset=offset
                )
                return [self.postgres_backend.project_to_dict(p) for p in projects]
            except Exception as e:
                logger.error(f"PostgreSQL list_projects failed: {e}")
                
        if self.file_backend:
            try:
                return self.file_backend.list_projects()
            except Exception as e:
                logger.error(f"File backend list_projects failed: {e}")
                
        return []
    
    def update_project(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        updates: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a project.
        
        Args:
            project_id: Project database ID
            name: Project name (for file backend)
            updates: Dictionary of fields to update
            
        Returns:
            Updated project data dict or None if failed
        """
        if not updates:
            return None
            
        if self.postgres_backend and project_id:
            try:
                project = self.postgres_backend.update_project(project_id, **updates)
                if project:
                    return self.postgres_backend.project_to_dict(project)
            except Exception as e:
                logger.error(f"PostgreSQL update_project failed: {e}")
                
        if self.file_backend and name:
            try:
                # File backend uses progress updates
                for key, value in updates.items():
                    self.file_backend.update_project_progress(name, key, value)
                return self.file_backend.get_project(name)
            except Exception as e:
                logger.error(f"File backend update_project failed: {e}")
                
        return None
    
    def delete_project(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project database ID
            name: Project name
            
        Returns:
            True if deleted successfully
        """
        if self.postgres_backend and project_id:
            try:
                return self.postgres_backend.delete_project(project_id)
            except Exception as e:
                logger.error(f"PostgreSQL delete_project failed: {e}")
                
        if self.file_backend and name:
            try:
                return self.file_backend.delete_project(name)
            except Exception as e:
                logger.error(f"File backend delete_project failed: {e}")
                
        return False
    
    def search_projects(
        self,
        query: str,
        user_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search projects by query.
        
        Args:
            query: Search query string
            user_id: Filter by user
            limit: Maximum results
            
        Returns:
            List of matching projects
        """
        user_id = user_id or self._default_user_id
        
        if self.postgres_backend:
            try:
                projects = self.postgres_backend.search_projects(
                    user_id=user_id,
                    search_query=query,
                    limit=limit
                )
                return [self.postgres_backend.project_to_dict(p) for p in projects]
            except Exception as e:
                logger.error(f"PostgreSQL search_projects failed: {e}")
                
        if self.file_backend:
            try:
                # File backend doesn't have search, filter manually
                all_projects = self.file_backend.list_projects()
                query_lower = query.lower()
                return [
                    p for p in all_projects
                    if query_lower in p.get('name', '').lower() or
                       query_lower in p.get('description', '').lower()
                ][:limit]
            except Exception as e:
                logger.error(f"File backend search failed: {e}")
                
        return []
    
    # ===========================================
    # Journal & Progress Operations
    # ===========================================
    
    def add_journal_entry(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        content: str = "",
        entry_type: str = "reflection"
    ) -> Optional[Dict[str, Any]]:
        """
        Add a journal entry to a project.
        
        Args:
            project_id: Project database ID
            name: Project name
            content: Journal entry content
            entry_type: Type of entry (reflection, question, insight, milestone)
            
        Returns:
            The created journal entry or None
        """
        if self.postgres_backend and project_id:
            try:
                # PostgreSQL backend stores journal in project metadata
                project = self.postgres_backend.get_project(project_id)
                if project:
                    entry = {
                        "content": content,
                        "type": entry_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Update project metadata to include journal entry
                    meta = project.meta_data or {}
                    if "journal_entries" not in meta:
                        meta["journal_entries"] = []
                    meta["journal_entries"].append(entry)
                    self.postgres_backend.update_project(project_id, meta_data=meta)
                    return entry
            except Exception as e:
                logger.error(f"PostgreSQL add_journal_entry failed: {e}")
                
        if self.file_backend and name:
            try:
                return self.file_backend.add_journal_entry(name, content, entry_type)
            except Exception as e:
                logger.error(f"File backend add_journal_entry failed: {e}")
                
        return None
    
    def get_journal_entries(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get journal entries for a project.
        
        Args:
            project_id: Project database ID
            name: Project name
            
        Returns:
            List of journal entries
        """
        if self.postgres_backend and project_id:
            try:
                project = self.postgres_backend.get_project(project_id)
                if project and project.meta_data:
                    return project.meta_data.get("journal_entries", [])
            except Exception as e:
                logger.error(f"PostgreSQL get_journal_entries failed: {e}")
                
        if self.file_backend and name:
            try:
                project = self.file_backend.get_project(name)
                if project:
                    return project.get("journal_entries", [])
            except Exception as e:
                logger.error(f"File backend get_journal_entries failed: {e}")
                
        return []
    
    def update_progress(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        key: str = "",
        value: Any = None
    ) -> bool:
        """
        Update project progress.
        
        Args:
            project_id: Project database ID
            name: Project name
            key: Progress key
            value: Progress value
            
        Returns:
            True if updated successfully
        """
        if self.postgres_backend and project_id:
            try:
                project = self.postgres_backend.get_project(project_id)
                if project:
                    meta = project.meta_data or {}
                    if "progress" not in meta:
                        meta["progress"] = {}
                    meta["progress"][key] = value
                    self.postgres_backend.update_project(project_id, meta_data=meta)
                    return True
            except Exception as e:
                logger.error(f"PostgreSQL update_progress failed: {e}")
                
        if self.file_backend and name:
            try:
                self.file_backend.update_project_progress(name, key, value)
                return True
            except Exception as e:
                logger.error(f"File backend update_progress failed: {e}")
                
        return False
    
    def get_progress(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get project progress.
        
        Args:
            project_id: Project database ID
            name: Project name
            
        Returns:
            Progress dictionary
        """
        if self.postgres_backend and project_id:
            try:
                project = self.postgres_backend.get_project(project_id)
                if project and project.meta_data:
                    return project.meta_data.get("progress", {})
            except Exception as e:
                logger.error(f"PostgreSQL get_progress failed: {e}")
                
        if self.file_backend and name:
            try:
                project = self.file_backend.get_project(name)
                if project:
                    return project.get("progress", {})
            except Exception as e:
                logger.error(f"File backend get_progress failed: {e}")
                
        return {}
    
    # ===========================================
    # Statistics & Analytics
    # ===========================================
    
    def get_project_stats(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a project.
        
        Args:
            project_id: Project database ID
            name: Project name
            
        Returns:
            Statistics dictionary
        """
        if self.postgres_backend and project_id:
            try:
                return self.postgres_backend.get_project_stats(project_id)
            except Exception as e:
                logger.error(f"PostgreSQL get_project_stats failed: {e}")
                
        if self.file_backend and name:
            try:
                project = self.file_backend.get_project(name)
                if project:
                    return {
                        "session_count": len(project.get("sessions", [])),
                        "resource_count": len(project.get("resources", [])),
                        "journal_entries": len(project.get("journal_entries", [])),
                        "created": project.get("created"),
                        "last_updated": project.get("last_updated")
                    }
            except Exception as e:
                logger.error(f"File backend get_project_stats failed: {e}")
                
        return {}
    
    def get_user_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistics across all projects for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            User statistics dictionary
        """
        user_id = user_id or self._default_user_id
        
        if self.postgres_backend:
            try:
                # Use get_project_count and aggregate from projects
                project_count = self.postgres_backend.get_project_count(user_id)
                projects = self.postgres_backend.get_projects_by_user(user_id)
                total_sessions = sum(
                    len(p.sessions) if hasattr(p, 'sessions') and p.sessions else 0 
                    for p in projects
                )
                return {
                    "total_projects": project_count,
                    "total_sessions": total_sessions,
                    "user_id": user_id
                }
            except Exception as e:
                logger.error(f"PostgreSQL get_user_statistics failed: {e}")
                
        if self.file_backend:
            try:
                projects = self.file_backend.list_projects()
                total_sessions = sum(len(p.get("sessions", [])) for p in projects)
                total_resources = sum(len(p.get("resources", [])) for p in projects)
                return {
                    "total_projects": len(projects),
                    "total_sessions": total_sessions,
                    "total_resources": total_resources
                }
            except Exception as e:
                logger.error(f"File backend get_user_statistics failed: {e}")
                
        return {}
    
    # ===========================================
    # Learning Plan Operations
    # ===========================================
    
    def save_learning_plan(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        learning_plan: Dict[str, Any] = None
    ) -> bool:
        """
        Save a learning plan for a project.
        
        Args:
            project_id: Project database ID
            name: Project name
            learning_plan: Learning plan data
            
        Returns:
            True if saved successfully
        """
        if not learning_plan:
            return False
            
        if self.postgres_backend and project_id:
            try:
                project = self.postgres_backend.get_project(project_id)
                if project:
                    meta = project.meta_data or {}
                    meta["learning_plan"] = learning_plan
                    self.postgres_backend.update_project(project_id, meta_data=meta)
                    return True
            except Exception as e:
                logger.error(f"PostgreSQL save_learning_plan failed: {e}")
                
        if self.file_backend and name:
            try:
                self.file_backend.save_learning_plan(name, learning_plan)
                return True
            except Exception as e:
                logger.error(f"File backend save_learning_plan failed: {e}")
                
        return False
    
    def get_learning_plan(
        self,
        project_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the learning plan for a project.
        
        Args:
            project_id: Project database ID
            name: Project name
            
        Returns:
            Learning plan data or None
        """
        if self.postgres_backend and project_id:
            try:
                project = self.postgres_backend.get_project(project_id)
                if project and project.meta_data:
                    return project.meta_data.get("learning_plan")
            except Exception as e:
                logger.error(f"PostgreSQL get_learning_plan failed: {e}")
                
        if self.file_backend and name:
            try:
                project = self.file_backend.get_project(name)
                if project:
                    return project.get("learning_plan")
            except Exception as e:
                logger.error(f"File backend get_learning_plan failed: {e}")
                
        return None
    
    # ===========================================
    # Module-level singleton
    # ===========================================

_hybrid_project_service: Optional[HybridProjectService] = None


def get_hybrid_project_service(prefer_postgres: bool = True) -> Optional[HybridProjectService]:
    """
    Get or create the hybrid project service singleton.
    
    Args:
        prefer_postgres: Whether to prefer PostgreSQL backend
        
    Returns:
        HybridProjectService instance or None if initialization fails
    """
    global _hybrid_project_service
    
    if _hybrid_project_service is not None:
        return _hybrid_project_service
    
    try:
        _hybrid_project_service = HybridProjectService(prefer_postgres=prefer_postgres)
        if _hybrid_project_service.initialize():
            return _hybrid_project_service
        else:
            logger.warning("Could not initialize HybridProjectService")
            _hybrid_project_service = None
            return None
    except Exception as e:
        logger.error(f"Error initializing HybridProjectService: {e}")
        _hybrid_project_service = None
        return None


def initialize_hybrid_project_service(prefer_postgres: bool = True) -> Optional[HybridProjectService]:
    """
    Force (re)initialization of the hybrid project service.
    
    Args:
        prefer_postgres: Whether to prefer PostgreSQL backend
        
    Returns:
        HybridProjectService instance or None if initialization fails
    """
    global _hybrid_project_service
    _hybrid_project_service = None
    return get_hybrid_project_service(prefer_postgres=prefer_postgres)


# Export for convenience
__all__ = [
    'HybridProjectService',
    'get_hybrid_project_service',
    'initialize_hybrid_project_service',
]
