"""
Wisdom Agent - Project Service

Manages learning and research projects with resources, sessions, and progress tracking.

MIGRATION NOTES:
- Ported from project_manager.py
- Uses Config paths for all directories
- Same interface preserved for compatibility
- Added Pydantic models for API integration
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field

from backend.config import config


# ========== PYDANTIC MODELS ==========

class ProjectCreate(BaseModel):
    """Model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=100)
    project_type: str = Field(default="learning", pattern="^(learning|research|wisdom)$")
    description: str = Field(default="")
    learning_goal: Optional[str] = None


class ResourceCreate(BaseModel):
    """Model for adding a resource."""
    resource_type: str = Field(..., description="Type: file, url, book, article")
    title: str
    location: str
    notes: Optional[str] = None


class JournalEntryCreate(BaseModel):
    """Model for adding a journal entry."""
    content: str
    entry_type: str = Field(default="reflection", pattern="^(reflection|question|insight|milestone)$")


class ProgressUpdate(BaseModel):
    """Model for updating progress."""
    key: str
    value: Any


# ========== PROJECT CLASS ==========

class Project:
    """Represents a learning or research project."""
    
    def __init__(self, name: str, project_type: str = "learning", description: str = ""):
        self.name = name
        self.project_type = project_type
        self.description = description
        self.created = datetime.now().isoformat()
        self.last_updated = self.created
        self.sessions: List[Dict] = []
        self.resources: List[Dict] = []
        self.journal_entries: List[Dict] = []
        self.learning_plan: Optional[Dict] = None
        self.progress: Dict = {}
        
    def to_dict(self) -> Dict:
        """Convert project to dictionary."""
        return {
            'name': self.name,
            'type': self.project_type,
            'description': self.description,
            'created': self.created,
            'last_updated': self.last_updated,
            'sessions': self.sessions,
            'resources': self.resources,
            'journal_entries': self.journal_entries,
            'learning_plan': self.learning_plan,
            'progress': self.progress
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        """Create project from dictionary."""
        project = cls(
            name=data['name'],
            project_type=data.get('type', 'learning'),
            description=data.get('description', '')
        )
        project.created = data.get('created', project.created)
        project.last_updated = data.get('last_updated', project.last_updated)
        project.sessions = data.get('sessions', [])
        project.resources = data.get('resources', [])
        project.journal_entries = data.get('journal_entries', [])
        project.learning_plan = data.get('learning_plan')
        project.progress = data.get('progress', {})
        return project


# ========== PROJECT SERVICE ==========

class ProjectService:
    """Manages projects, knowledge base, and thematic organization."""
    
    def __init__(self, 
                 projects_dir: Optional[Path] = None,
                 kb_dir: Optional[Path] = None):
        """
        Initialize Project Service.
        
        Args:
            projects_dir: Directory for project storage (uses config default)
            kb_dir: Directory for knowledge base (uses config default)
        """
        self.projects_dir = projects_dir or config.PROJECTS_DIR
        self.kb_dir = kb_dir or config.KNOWLEDGE_BASE_DIR
        
        # Ensure directories exist
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_project: Optional[Project] = None
        self.themes = self._load_themes()
    
    # ========== PROJECT CRUD ==========
    
    def create_project(self, 
                      name: str,
                      project_type: str = "learning",
                      description: str = "",
                      learning_goal: Optional[str] = None) -> Project:
        """
        Create a new project.
        
        Args:
            name: Project name
            project_type: Type (learning, research, wisdom)
            description: Project description
            learning_goal: Specific learning goal (for learning projects)
            
        Returns:
            Created Project object
            
        Raises:
            ValueError: If project already exists
        """
        safe_name = self._sanitize_name(name)
        project_path = self.projects_dir / safe_name
        
        if project_path.exists():
            raise ValueError(f"Project '{name}' already exists")
        
        # Create project
        project = Project(name, project_type, description)
        
        # Create directory structure
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "sessions").mkdir(exist_ok=True)
        (project_path / "resources").mkdir(exist_ok=True)
        (project_path / "exports").mkdir(exist_ok=True)
        
        # For learning projects, set up initial learning plan
        if project_type == "learning" and learning_goal:
            project.learning_plan = {
                'goal': learning_goal,
                'status': 'planning',
                'milestones': [],
                'created': datetime.now().isoformat()
            }
        
        # Save project
        self._save_project(project, safe_name)
        
        return project
    
    def load_project(self, name: str) -> Optional[Project]:
        """
        Load an existing project.
        
        Args:
            name: Project name
            
        Returns:
            Project object or None if not found
        """
        safe_name = self._sanitize_name(name)
        project_file = self.projects_dir / safe_name / "project.json"
        
        if not project_file.exists():
            return None
        
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        return Project.from_dict(data)
    
    def delete_project(self, name: str) -> bool:
        """
        Delete a project.
        
        Args:
            name: Project name
            
        Returns:
            True if deleted, False if not found
        """
        import shutil
        
        safe_name = self._sanitize_name(name)
        project_path = self.projects_dir / safe_name
        
        if not project_path.exists():
            return False
        
        shutil.rmtree(project_path)
        
        # Clear current project if it was the deleted one
        if self.current_project and self._sanitize_name(self.current_project.name) == safe_name:
            self.current_project = None
        
        return True
    
    def set_current_project(self, name: str) -> bool:
        """
        Set the active project.
        
        Args:
            name: Project name
            
        Returns:
            True if successful
        """
        project = self.load_project(name)
        if project:
            self.current_project = project
            return True
        return False
    
    def list_projects(self) -> List[Dict]:
        """
        List all projects.
        
        Returns:
            List of project summaries
        """
        projects = []
        
        if not self.projects_dir.exists():
            return projects
        
        for item in self.projects_dir.iterdir():
            if item.is_dir():
                project = self.load_project(item.name)
                if project:
                    projects.append({
                        'name': project.name,
                        'type': project.project_type,
                        'description': project.description,
                        'sessions_count': len(project.sessions),
                        'resources_count': len(project.resources),
                        'last_updated': project.last_updated
                    })
        
        return sorted(projects, key=lambda x: x['last_updated'], reverse=True)
    
    # ========== SESSION MANAGEMENT ==========
    
    def add_session_to_project(self, 
                               session_id: int,
                               session_type: str = "learning",
                               summary: Optional[str] = None,
                               project_name: Optional[str] = None) -> bool:
        """
        Add a session to a project.
        
        Args:
            session_id: Session identifier
            session_type: Type of session
            summary: Brief session summary
            project_name: Project to add to (default: current)
            
        Returns:
            True if successful
        """
        project = self._get_project(project_name)
        if not project:
            return False
        
        session_entry = {
            'session_id': session_id,
            'type': session_type,
            'date': datetime.now().isoformat(),
            'summary': summary
        }
        
        project.sessions.append(session_entry)
        project.last_updated = datetime.now().isoformat()
        
        self._save_project(project, self._sanitize_name(project.name))
        return True
    
    # ========== RESOURCE MANAGEMENT ==========
    
    def add_resource(self,
                    resource_type: str,
                    title: str,
                    location: str,
                    notes: Optional[str] = None,
                    project_name: Optional[str] = None) -> bool:
        """
        Add a resource to a project.
        
        Args:
            resource_type: Type (file, url, book, article)
            title: Resource title
            location: File path or URL
            notes: Optional notes about resource
            project_name: Project to add to (default: current)
            
        Returns:
            True if successful
        """
        project = self._get_project(project_name)
        if not project:
            return False
        
        resource = {
            'type': resource_type,
            'title': title,
            'location': location,
            'notes': notes,
            'added': datetime.now().isoformat()
        }
        
        project.resources.append(resource)
        project.last_updated = datetime.now().isoformat()
        
        self._save_project(project, self._sanitize_name(project.name))
        return True
    
    def get_project_resources(self, project_name: str) -> List[Dict]:
        """Get all resources for a project."""
        project = self.load_project(project_name)
        if not project:
            return []
        return project.resources
    
    # ========== JOURNAL ENTRIES ==========
    
    def add_journal_entry(self,
                         content: str,
                         entry_type: str = "reflection",
                         project_name: Optional[str] = None) -> bool:
        """
        Add a journal entry to a project.
        
        Args:
            content: Entry content
            entry_type: Type (reflection, question, insight, milestone)
            project_name: Project to add to (default: current)
            
        Returns:
            True if successful
        """
        project = self._get_project(project_name)
        if not project:
            return False
        
        entry = {
            'type': entry_type,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        project.journal_entries.append(entry)
        project.last_updated = datetime.now().isoformat()
        
        self._save_project(project, self._sanitize_name(project.name))
        return True
    
    def get_journal_entries(self, project_name: str) -> List[Dict]:
        """Get all journal entries for a project."""
        project = self.load_project(project_name)
        if not project:
            return []
        return project.journal_entries
    
    # ========== PROGRESS TRACKING ==========
    
    def update_progress(self,
                       key: str,
                       value: Any,
                       project_name: Optional[str] = None) -> bool:
        """
        Update project progress tracking.
        
        Args:
            key: Progress key (e.g., 'concepts_mastered', 'current_level')
            value: Progress value
            project_name: Project to update (default: current)
            
        Returns:
            True if successful
        """
        project = self._get_project(project_name)
        if not project:
            return False
        
        project.progress[key] = {
            'value': value,
            'updated': datetime.now().isoformat()
        }
        project.last_updated = datetime.now().isoformat()
        
        self._save_project(project, self._sanitize_name(project.name))
        return True
    
    def get_project_outline(self, project_name: Optional[str] = None) -> Dict:
        """
        Get structured outline of project.
        
        Args:
            project_name: Project name (default: current)
            
        Returns:
            Dictionary with project outline
        """
        project = self._get_project(project_name)
        if not project:
            return {}
        
        return {
            'name': project.name,
            'type': project.project_type,
            'description': project.description,
            'created': project.created,
            'sessions_count': len(project.sessions),
            'resources_count': len(project.resources),
            'journal_entries_count': len(project.journal_entries),
            'learning_plan': project.learning_plan,
            'progress': project.progress,
            'last_updated': project.last_updated
        }
    
    # ========== LEARNING PLAN ==========
    
    def update_learning_plan(self,
                            learning_plan: Dict,
                            project_name: Optional[str] = None) -> bool:
        """
        Update the learning plan for a project.
        
        Args:
            learning_plan: New learning plan dict
            project_name: Project to update
            
        Returns:
            True if successful
        """
        project = self._get_project(project_name)
        if not project:
            return False
        
        project.learning_plan = learning_plan
        project.last_updated = datetime.now().isoformat()
        
        self._save_project(project, self._sanitize_name(project.name))
        return True
    
    # ========== THEMES ==========
    
    def add_theme(self, 
                  theme_name: str,
                  description: str = "",
                  parent_theme: Optional[str] = None,
                  auto_generated: bool = False) -> bool:
        """
        Add a theme to knowledge base.
        
        Args:
            theme_name: Theme name
            description: Theme description
            parent_theme: Parent theme (for hierarchy)
            auto_generated: Whether theme was auto-generated by LLM
            
        Returns:
            True if created, False if already exists
        """
        category = 'auto_generated' if auto_generated else 'user_defined'
        
        if theme_name in self.themes[category]:
            return False
        
        self.themes[category][theme_name] = {
            'description': description,
            'parent': parent_theme,
            'sessions': [],
            'projects': [],
            'resources': [],
            'created': datetime.now().isoformat()
        }
        self._save_themes()
        return True
    
    def get_themes(self) -> Dict:
        """Get all themes."""
        return self.themes
    
    def categorize_under_theme(self,
                               theme_name: str,
                               item_type: str,
                               item_id: Any) -> bool:
        """
        Categorize an item under a theme.
        
        Args:
            theme_name: Theme name
            item_type: Type (session, project, resource)
            item_id: Item identifier
            
        Returns:
            True if successful
        """
        # Check both auto_generated and user_defined
        theme_data = None
        if theme_name in self.themes['auto_generated']:
            theme_data = self.themes['auto_generated'][theme_name]
        elif theme_name in self.themes['user_defined']:
            theme_data = self.themes['user_defined'][theme_name]
        
        if not theme_data:
            return False
        
        list_key = f"{item_type}s" if not item_type.endswith('s') else item_type
        if list_key in theme_data and item_id not in theme_data[list_key]:
            theme_data[list_key].append(item_id)
            self._save_themes()
            return True
        
        return False
    
    # ========== PRIVATE HELPERS ==========
    
    def _get_project(self, project_name: Optional[str] = None) -> Optional[Project]:
        """Get project by name or current project."""
        if project_name:
            return self.load_project(project_name)
        return self.current_project
    
    def _save_project(self, project: Project, safe_name: str):
        """Save project to disk."""
        project_path = self.projects_dir / safe_name
        project_file = project_path / "project.json"
        
        with open(project_file, 'w') as f:
            json.dump(project.to_dict(), f, indent=2)
    
    def _load_themes(self) -> Dict:
        """Load knowledge base themes."""
        themes_file = self.kb_dir / "themes.json"
        
        if themes_file.exists():
            with open(themes_file, 'r') as f:
                return json.load(f)
        
        # Default themes structure
        return {
            'auto_generated': {},
            'user_defined': {}
        }
    
    def _save_themes(self):
        """Save themes to file."""
        themes_file = self.kb_dir / "themes.json"
        with open(themes_file, 'w') as f:
            json.dump(self.themes, f, indent=2)
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for filesystem."""
        safe = name.lower().replace(' ', '_')
        safe = ''.join(c for c in safe if c.isalnum() or c == '_')
        return safe


# ========== SINGLETON & FACTORY ==========

_project_service: Optional[ProjectService] = None


def get_project_service() -> Optional[ProjectService]:
    """Get the singleton ProjectService instance."""
    global _project_service
    return _project_service


def initialize_project_service() -> Optional[ProjectService]:
    """
    Initialize and return the singleton ProjectService.
    
    Returns:
        ProjectService instance or None if initialization fails
    """
    global _project_service
    
    if _project_service is not None:
        return _project_service
    
    try:
        _project_service = ProjectService()
        return _project_service
    except Exception as e:
        print(f"Warning: Could not initialize ProjectService: {e}")
        return None
