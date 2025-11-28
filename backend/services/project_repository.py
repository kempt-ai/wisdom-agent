"""
Wisdom Agent - PostgreSQL Project Repository

Handles CRUD operations for projects with PostgreSQL backend.
Supports the hybrid project service for seamless database integration.

Author: Wisdom Agent Team
Date: 2025-11-24
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import Session as DBSession, joinedload

from backend.database.connection import get_db_session
from backend.database.models import Project, Session, SessionType

logger = logging.getLogger(__name__)


class ProjectRepository:
    """Repository for project-related database operations."""
    
    def __init__(self):
        """Initialize the project repository."""
        self.db_session: Optional[DBSession] = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize database connection.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db_session = get_db_session()
            self._initialized = True
            logger.info("ProjectRepository initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ProjectRepository: {e}")
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if repository is initialized."""
        return self._initialized and self.db_session is not None
    
    # ===========================================
    # Project CRUD Operations
    # ===========================================
    
    def create_project(
        self,
        name: str,
        user_id: int,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        session_type: SessionType = SessionType.GENERAL,
        subject: Optional[str] = None,
        current_level: Optional[str] = None,
        learning_goal: Optional[str] = None,
        time_commitment: Optional[str] = None,
        philosophy_overlay: Optional[str] = None,
        organization_id: Optional[int] = None
    ) -> Optional[Project]:
        """
        Create a new project.
        
        Args:
            name: Project name
            user_id: ID of the user creating the project
            slug: URL-friendly project identifier (auto-generated if None)
            description: Project description
            session_type: Default session type for this project
            subject: Learning subject
            current_level: Current skill level
            learning_goal: Learning goal description
            time_commitment: Time commitment description
            philosophy_overlay: Optional project-specific philosophy
            organization_id: Optional organization ID
            
        Returns:
            Project object if successful, None otherwise
        """
        if not self.is_initialized():
            logger.error("ProjectRepository not initialized")
            return None
        
        try:
            # Auto-generate slug if not provided
            if slug is None:
                slug = name.lower().replace(' ', '_').replace('-', '_')
                # Ensure slug is unique for this user
                base_slug = slug
                counter = 1
                while self._slug_exists(user_id, slug):
                    slug = f"{base_slug}_{counter}"
                    counter += 1
            
            # Create project
            project = Project(
                name=name,
                slug=slug,
                description=description,
                session_type=session_type,
                subject=subject,
                current_level=current_level,
                learning_goal=learning_goal,
                time_commitment=time_commitment,
                philosophy_overlay=philosophy_overlay,
                user_id=user_id,
                organization_id=organization_id
            )
            
            self.db_session.add(project)
            self.db_session.commit()
            self.db_session.refresh(project)
            
            logger.info(f"Created project {project.id} ('{project.name}') for user {user_id}")
            return project
            
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            self.db_session.rollback()
            return None
    
    def _slug_exists(self, user_id: int, slug: str) -> bool:
        """Check if slug already exists for user."""
        try:
            result = self.db_session.query(Project).filter(
                and_(Project.user_id == user_id, Project.slug == slug)
            ).first()
            return result is not None
        except Exception:
            return False
    
    def get_project(self, project_id: int, load_sessions: bool = False) -> Optional[Project]:
        """
        Get a project by ID.
        
        Args:
            project_id: Project ID
            load_sessions: Whether to eagerly load sessions
            
        Returns:
            Project object if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            query = select(Project).where(Project.id == project_id)
            
            if load_sessions:
                query = query.options(joinedload(Project.sessions))
            
            result = self.db_session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {e}")
            return None
    
    def get_project_by_slug(self, user_id: int, slug: str, load_sessions: bool = False) -> Optional[Project]:
        """
        Get a project by user ID and slug.
        
        Args:
            user_id: User ID
            slug: Project slug
            load_sessions: Whether to eagerly load sessions
            
        Returns:
            Project object if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            query = select(Project).where(
                and_(Project.user_id == user_id, Project.slug == slug)
            )
            
            if load_sessions:
                query = query.options(joinedload(Project.sessions))
            
            result = self.db_session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting project by slug '{slug}': {e}")
            return None
    
    def get_projects_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Get all projects for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of projects to return
            offset: Number of projects to skip
            
        Returns:
            List of Project objects
        """
        if not self.is_initialized():
            return []
        
        try:
            query = select(Project).where(
                Project.user_id == user_id
            ).order_by(
                desc(Project.updated_at)
            ).limit(limit).offset(offset)
            
            result = self.db_session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting projects for user {user_id}: {e}")
            return []
    
    def update_project(
        self,
        project_id: int,
        **kwargs
    ) -> Optional[Project]:
        """
        Update a project.
        
        Args:
            project_id: Project ID
            **kwargs: Fields to update
            
        Returns:
            Updated Project object if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            project = self.get_project(project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(project, key) and key not in ['id', 'user_id', 'created_at']:
                    setattr(project, key, value)
            
            project.updated_at = datetime.utcnow()
            self.db_session.commit()
            self.db_session.refresh(project)
            
            logger.info(f"Updated project {project_id}")
            return project
            
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            self.db_session.rollback()
            return None
    
    def update_learning_plan(
        self,
        project_id: int,
        learning_plan: Dict[str, Any]
    ) -> bool:
        """
        Update project's learning plan.
        
        Args:
            project_id: Project ID
            learning_plan: Learning plan dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.update_project(project_id, learning_plan=learning_plan)
        return result is not None
    
    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project (cascades to sessions).
        
        Args:
            project_id: Project ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized():
            return False
        
        try:
            project = self.get_project(project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return False
            
            self.db_session.delete(project)
            self.db_session.commit()
            
            logger.info(f"Deleted project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            self.db_session.rollback()
            return False
    
    # ===========================================
    # Project Statistics
    # ===========================================
    
    def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """
        Get statistics for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict with project statistics
        """
        if not self.is_initialized():
            return {}
        
        try:
            project = self.get_project(project_id)
            if not project:
                return {}
            
            # Count sessions
            session_count = self.db_session.query(func.count(Session.id)).filter(
                Session.project_id == project_id
            ).scalar() or 0
            
            # Get latest session
            latest_session = self.db_session.query(Session).filter(
                Session.project_id == project_id
            ).order_by(desc(Session.created_at)).first()
            
            return {
                "project_id": project_id,
                "name": project.name,
                "slug": project.slug,
                "session_count": session_count,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "last_session": latest_session.created_at.isoformat() if latest_session else None,
                "has_learning_plan": project.learning_plan is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting project stats: {e}")
            return {}
    
    def get_project_count(self, user_id: Optional[int] = None) -> int:
        """
        Get count of projects.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            int: Number of projects
        """
        if not self.is_initialized():
            return 0
        
        try:
            query = select(func.count(Project.id))
            
            if user_id:
                query = query.where(Project.user_id == user_id)
            
            result = self.db_session.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting project count: {e}")
            return 0
    
    # ===========================================
    # Search & Query
    # ===========================================
    
    def search_projects(
        self,
        user_id: int,
        search_query: str,
        limit: int = 20
    ) -> List[Project]:
        """
        Search projects by name or description.
        
        Args:
            user_id: User ID
            search_query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching Project objects
        """
        if not self.is_initialized():
            return []
        
        try:
            # Use case-insensitive LIKE search
            pattern = f"%{search_query}%"
            query = select(Project).where(
                and_(
                    Project.user_id == user_id,
                    or_(
                        Project.name.ilike(pattern),
                        Project.description.ilike(pattern),
                        Project.subject.ilike(pattern)
                    )
                )
            ).order_by(desc(Project.updated_at)).limit(limit)
            
            result = self.db_session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error searching projects: {e}")
            return []
    
    # ===========================================
    # Conversion Utilities
    # ===========================================
    
    def project_to_dict(self, project: Project, include_sessions: bool = False) -> Dict[str, Any]:
        """
        Convert Project model to dictionary.
        
        Args:
            project: Project model instance
            include_sessions: Include session information
            
        Returns:
            Dict representation of project
        """
        try:
            result = {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "description": project.description,
                "type": project.session_type.value,
                "subject": project.subject,
                "current_level": project.current_level,
                "learning_goal": project.learning_goal,
                "time_commitment": project.time_commitment,
                "learning_plan": project.learning_plan,
                "philosophy_overlay": project.philosophy_overlay,
                "user_id": project.user_id,
                "organization_id": project.organization_id,
                "created": project.created_at.isoformat() if project.created_at else None,
                "last_updated": project.updated_at.isoformat() if project.updated_at else None,
            }
            
            if include_sessions:
                # Count sessions
                session_count = self.db_session.query(func.count(Session.id)).filter(
                    Session.project_id == project.id
                ).scalar() or 0
                
                result["session_count"] = session_count
                
                # Get recent sessions
                recent_sessions = self.db_session.query(Session).filter(
                    Session.project_id == project.id
                ).order_by(desc(Session.created_at)).limit(5).all()
                
                result["recent_sessions"] = [
                    {
                        "id": s.id,
                        "number": s.session_number,
                        "title": s.title,
                        "created_at": s.created_at.isoformat() if s.created_at else None
                    }
                    for s in recent_sessions
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error converting project to dict: {e}")
            return {}
    
    # ===========================================
    # Status & Health
    # ===========================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get repository status.
        
        Returns:
            Dict with status information
        """
        if not self.is_initialized():
            return {
                "initialized": False,
                "backend": "postgresql",
                "error": "Not initialized"
            }
        
        try:
            project_count = self.get_project_count()
            
            return {
                "initialized": True,
                "backend": "postgresql",
                "projects": project_count
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "initialized": True,
                "backend": "postgresql",
                "error": str(e)
            }


# Singleton instance
_project_repository = None


def get_project_repository() -> ProjectRepository:
    """Get or create singleton project repository."""
    global _project_repository
    if _project_repository is None:
        _project_repository = ProjectRepository()
    return _project_repository
