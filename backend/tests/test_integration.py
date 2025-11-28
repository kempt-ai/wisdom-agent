"""
Wisdom Agent - Integration Tests (Week 2 Day 5)

Comprehensive tests for all services and repositories.
Run with: python -m pytest backend/tests/test_integration.py -v
"""

import pytest
import os
from datetime import datetime

# Set SQLite mode for testing
os.environ["USE_SQLITE"] = "true"


class TestDatabaseConnection:
    """Test database connection and initialization."""
    
    def test_connection_initialized(self):
        """Test that database connection can be established."""
        from backend.database.connection import check_database_connection
        assert check_database_connection() == True
    
    def test_database_initialized(self):
        """Test that database tables are created."""
        from backend.database.connection import init_database
        result = init_database()
        assert result == True


class TestHybridMemoryService:
    """Test hybrid memory service."""
    
    def test_service_initialization(self):
        """Test that memory service initializes."""
        from backend.services.hybrid_memory_service import get_hybrid_memory_service
        service = get_hybrid_memory_service()
        # May be None if no backend available, but shouldn't crash
        if service:
            assert service.is_initialized() == True
    
    def test_backend_info(self):
        """Test getting backend information."""
        from backend.services.hybrid_memory_service import get_hybrid_memory_service
        service = get_hybrid_memory_service()
        if service:
            info = service.get_backend_info()
            assert "active_backend" in info
            assert "initialized" in info


class TestHybridProjectService:
    """Test hybrid project service."""
    
    def test_service_initialization(self):
        """Test that project service initializes."""
        from backend.services.hybrid_project_service import get_hybrid_project_service
        service = get_hybrid_project_service()
        assert service is not None
        assert service.is_initialized() == True
    
    def test_backend_info(self):
        """Test getting backend information."""
        from backend.services.hybrid_project_service import get_hybrid_project_service
        service = get_hybrid_project_service()
        info = service.get_backend_info()
        assert "active_backend" in info
        assert info["initialized"] == True
    
    def test_create_project(self):
        """Test creating a project."""
        from backend.services.hybrid_project_service import get_hybrid_project_service
        service = get_hybrid_project_service()
        
        project = service.create_project(
            name="Test Integration Project",
            project_type="learning",
            description="A test project for integration testing"
        )
        
        assert project is not None
        assert project["name"] == "Test Integration Project"
    
    def test_list_projects(self):
        """Test listing projects."""
        from backend.services.hybrid_project_service import get_hybrid_project_service
        service = get_hybrid_project_service()
        
        projects = service.list_projects()
        assert isinstance(projects, list)
    
    def test_search_projects(self):
        """Test searching projects."""
        from backend.services.hybrid_project_service import get_hybrid_project_service
        service = get_hybrid_project_service()
        
        # First create a project to search for
        service.create_project(
            name="Searchable Project",
            description="This is searchable"
        )
        
        results = service.search_projects("Searchable")
        assert isinstance(results, list)


class TestSessionRepository:
    """Test session repository."""
    
    def test_repository_initialization(self):
        """Test that session repository initializes."""
        from backend.services.session_repository import get_session_repository
        repo = get_session_repository()
        assert repo.initialize() == True
    
    def test_create_session(self):
        """Test creating a session."""
        from backend.services.session_repository import get_session_repository
        repo = get_session_repository()
        repo.initialize()
        
        session = repo.create_session(
            user_id=1,
            title="Test Session",
            session_type="general"
        )
        
        assert session is not None
        assert session.title == "Test Session"


class TestConversationService:
    """Test conversation service."""
    
    def test_service_initialization(self):
        """Test that conversation service initializes."""
        from backend.services.conversation_service import get_conversation_service
        service = get_conversation_service()
        assert service.initialize() == True
    
    def test_start_session(self):
        """Test starting a conversation session."""
        from backend.services.conversation_service import get_conversation_service
        service = get_conversation_service()
        service.initialize()
        
        result = service.start_session(
            user_id=1,
            title="Integration Test Session"
        )
        
        assert result is not None
        assert "session_id" in result


class TestAPIEndpoints:
    """Test API endpoints are registered."""
    
    def test_app_loads(self):
        """Test that the FastAPI app loads."""
        from backend.main import app
        assert app is not None
    
    def test_routes_registered(self):
        """Test that routes are registered."""
        from backend.main import app
        routes = [r.path for r in app.routes]
        
        # Check essential routes exist
        assert "/" in routes
        assert "/health" in routes
        assert "/philosophy" in routes
    
    def test_route_count(self):
        """Test that expected number of routes exist."""
        from backend.main import app
        route_count = len(app.routes)
        # We expect at least 80 routes based on migration progress
        assert route_count >= 80, f"Expected at least 80 routes, got {route_count}"


class TestPhilosophyLoader:
    """Test philosophy loader."""
    
    def test_loader_exists(self):
        """Test that philosophy loader can be imported."""
        from backend.services.philosophy_loader import philosophy_loader
        assert philosophy_loader is not None
    
    def test_base_philosophy_loads(self):
        """Test that base philosophy files load."""
        from backend.services.philosophy_loader import philosophy_loader
        base = philosophy_loader.load_base_philosophy()
        assert base is not None
        assert len(base) > 0


class TestReflectionService:
    """Test reflection service."""
    
    def test_service_initialization(self):
        """Test that reflection service initializes."""
        from backend.services.reflection_service import ReflectionService
        service = ReflectionService()
        assert service.initialize() == True
    
    def test_seven_values_available(self):
        """Test that 7 Universal Values are defined."""
        from backend.services.reflection_service import ReflectionService
        service = ReflectionService()
        values = service.get_seven_values()
        
        assert len(values) == 7
        expected = ["awareness", "honesty", "accuracy", "competence", 
                   "compassion", "loving_kindness", "joyful_sharing"]
        for value in expected:
            assert value in values


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
