"""
Wisdom Agent - Hybrid Memory Service (Week 2)

Unified memory service that uses PostgreSQL + pgvector as primary backend
with ChromaDB as fallback for compatibility.

Features:
- PostgreSQL + pgvector for production (scalable, multi-user)
- ChromaDB fallback for development/compatibility
- Automatic backend selection
- Same interface for both backends
"""

from typing import List, Dict, Optional
import logging

from backend.config import config

# Try to import PostgreSQL backend
try:
    from backend.services.pg_memory_repository import PostgresMemoryRepository
    POSTGRES_AVAILABLE = True
except ImportError:
    PostgresMemoryRepository = None
    POSTGRES_AVAILABLE = False

# Try to import ChromaDB backend (original)
try:
    from backend.services.memory_service import MemoryService as ChromaMemoryService
    CHROMA_AVAILABLE = True
except ImportError:
    ChromaMemoryService = None
    CHROMA_AVAILABLE = False

logger = logging.getLogger(__name__)


class HybridMemoryService:
    """
    Hybrid memory service that uses PostgreSQL or ChromaDB.
    
    Backend Priority:
    1. PostgreSQL + pgvector (if DATABASE_URL configured)
    2. ChromaDB (fallback for development)
    
    This provides a unified interface regardless of backend.
    """
    
    def __init__(self, prefer_postgres: bool = True):
        """
        Initialize hybrid memory service.
        
        Args:
            prefer_postgres: If True, use PostgreSQL when available
        """
        self.backend_name = None
        self.backend = None
        self._initialized = False
        self.prefer_postgres = prefer_postgres
        
        # Default user_id for single-user mode (Week 2)
        # In future, this will come from authentication
        self.default_user_id = 1
    
    def initialize(self) -> bool:
        """
        Initialize the memory service with best available backend.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
        
        # Try PostgreSQL first if preferred and configured
        if self.prefer_postgres and config.DATABASE_URL and POSTGRES_AVAILABLE:
            try:
                logger.info("Attempting to use PostgreSQL + pgvector backend...")
                self.backend = PostgresMemoryRepository()
                if self.backend.initialize():
                    self.backend_name = "postgresql"
                    self._initialized = True
                    logger.info("✅ PostgreSQL memory backend initialized")
                    return True
                else:
                    logger.warning("PostgreSQL backend failed to initialize, trying ChromaDB...")
            except Exception as e:
                logger.warning(f"PostgreSQL backend error: {e}, trying ChromaDB...")
        
        # Fallback to ChromaDB
        if CHROMA_AVAILABLE:
            try:
                logger.info("Using ChromaDB backend...")
                self.backend = ChromaMemoryService()
                if self.backend.initialize():
                    self.backend_name = "chromadb"
                    self._initialized = True
                    logger.info("✅ ChromaDB memory backend initialized")
                    return True
            except Exception as e:
                logger.error(f"ChromaDB backend error: {e}")
        
        logger.error("❌ No memory backend available")
        return False
    
    def _ensure_initialized(self):
        """Ensure service is initialized before operations."""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("HybridMemoryService not initialized")
    
    # ========== UNIFIED INTERFACE ==========
    
    def store_conversation(
        self,
        session_id: int,
        conversation_text: str,
        metadata: Dict,
        user_id: Optional[int] = None
    ) -> str:
        """
        Store conversation embedding.
        
        Args:
            session_id: Session identifier
            conversation_text: Full conversation text
            metadata: Additional metadata
            user_id: Optional user ID (defaults to 1 for single-user)
            
        Returns:
            Embedding ID or memory ID
        """
        self._ensure_initialized()
        user_id = user_id or self.default_user_id
        
        if self.backend_name == "postgresql":
            # PostgreSQL backend
            meta_data = {
                **metadata,
                'type': 'conversation',
                'session_id': session_id
            }
            memory_id = self.backend.store_memory(
                content=conversation_text,
                user_id=user_id,
                session_id=session_id,
                meta_data=meta_data
            )
            return f"pg_mem_{memory_id}"
        else:
            # ChromaDB backend
            return self.backend.store_conversation(
                session_id=session_id,
                conversation_text=conversation_text,
                metadata=metadata
            )
    
    def store_reflection(
        self,
        session_id: int,
        reflection_text: str,
        metadata: Dict,
        user_id: Optional[int] = None
    ) -> str:
        """
        Store reflection embedding.
        
        Args:
            session_id: Session identifier
            reflection_text: Full reflection text
            metadata: Additional metadata
            user_id: Optional user ID
            
        Returns:
            Embedding ID or memory ID
        """
        self._ensure_initialized()
        user_id = user_id or self.default_user_id
        
        if self.backend_name == "postgresql":
            # PostgreSQL backend
            meta_data = {
                **metadata,
                'type': 'reflection',
                'session_id': session_id
            }
            memory_id = self.backend.store_memory(
                content=reflection_text,
                user_id=user_id,
                session_id=session_id,
                meta_data=meta_data
            )
            return f"pg_mem_{memory_id}"
        else:
            # ChromaDB backend
            return self.backend.store_reflection(
                session_id=session_id,
                reflection_text=reflection_text,
                metadata=metadata
            )
    
    def store_memory(
        self,
        content: str,
        metadata: Dict,
        user_id: Optional[int] = None
    ) -> str:
        """
        Store generic memory.
        
        Args:
            content: Text content
            metadata: Metadata including type, session_id, etc.
            user_id: Optional user ID
            
        Returns:
            Memory ID
        """
        self._ensure_initialized()
        user_id = user_id or self.default_user_id
        
        if self.backend_name == "postgresql":
            session_id = metadata.get('session_id')
            project_id = metadata.get('project_id')
            memory_id = self.backend.store_memory(
                content=content,
                user_id=user_id,
                session_id=session_id,
                project_id=project_id,
                meta_data=metadata
            )
            return f"pg_mem_{memory_id}"
        else:
            # ChromaDB backend
            return self.backend.store(content=content, metadata=metadata)
    
    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        session_type: Optional[str] = None,
        project: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for semantically similar memories.
        
        Args:
            query: Search query
            n_results: Number of results
            session_type: Optional session type filter
            project: Optional project filter
            user_id: Optional user ID
            
        Returns:
            List of similar memories
        """
        self._ensure_initialized()
        user_id = user_id or self.default_user_id
        
        if self.backend_name == "postgresql":
            # Build metadata filter
            metadata_filter = {}
            if session_type:
                metadata_filter['session_type'] = session_type
            if project:
                metadata_filter['project'] = project
            
            return self.backend.search_similar(
                query=query,
                user_id=user_id,
                n_results=n_results,
                metadata_filter=metadata_filter if metadata_filter else None
            )
        else:
            # ChromaDB backend
            return self.backend.search_similar_sessions(
                query=query,
                n_results=n_results,
                session_type=session_type,
                project=project
            )
    
    def get_session_memory(
        self,
        session_id: int,
        n_results: int = 10,
        user_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get memories for a specific session.
        
        Args:
            session_id: Session identifier
            n_results: Maximum results
            user_id: Optional user ID
            
        Returns:
            List of session memories
        """
        self._ensure_initialized()
        user_id = user_id or self.default_user_id
        
        if self.backend_name == "postgresql":
            return self.backend.get_session_memories(
                session_id=session_id,
                user_id=user_id,
                limit=n_results
            )
        else:
            # ChromaDB backend
            return self.backend.get_session_memory(
                session_id=session_id,
                n_results=n_results
            )
    
    def get_project_memories(
        self,
        project_name: str,
        n_results: int = 20,
        user_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get memories for a specific project.
        
        Args:
            project_name: Project name
            n_results: Maximum results
            user_id: Optional user ID
            
        Returns:
            List of project memories
        """
        self._ensure_initialized()
        user_id = user_id or self.default_user_id
        
        if self.backend_name == "postgresql":
            # For PostgreSQL, we need project_id, not name
            # This is a limitation - in real usage, we'd look up project_id from name
            logger.warning("PostgreSQL backend requires project_id, not name. Using ChromaDB fallback method.")
            if hasattr(self.backend, 'search_similar'):
                # Use metadata filter instead
                return self.backend.search_similar(
                    query="",  # Empty query to get all
                    user_id=user_id,
                    n_results=n_results,
                    metadata_filter={'project': project_name}
                )
            return []
        else:
            # ChromaDB backend
            return self.backend.search_by_project(
                project_name=project_name,
                n_results=n_results
            )
    
    def get_status(self) -> Dict:
        """
        Get memory service status.
        
        Returns:
            Status dictionary
        """
        status = {
            'initialized': self._initialized,
            'backend': self.backend_name,
            'postgres_available': POSTGRES_AVAILABLE,
            'chroma_available': CHROMA_AVAILABLE,
        }
        
        if self._initialized and hasattr(self.backend, 'get_status'):
            backend_status = self.backend.get_status()
            status.update(backend_status)
        
        return status


# ========== SINGLETON & FACTORY ==========

_hybrid_memory_service: Optional[HybridMemoryService] = None


def get_hybrid_memory_service() -> Optional[HybridMemoryService]:
    """
    Get the singleton HybridMemoryService instance.
    
    Returns:
        HybridMemoryService instance or None if not initialized
    """
    global _hybrid_memory_service
    return _hybrid_memory_service


def initialize_hybrid_memory_service(prefer_postgres: bool = True) -> Optional[HybridMemoryService]:
    """
    Initialize and return the singleton HybridMemoryService.
    
    Args:
        prefer_postgres: If True, prefer PostgreSQL over ChromaDB
        
    Returns:
        HybridMemoryService instance or None if initialization fails
    """
    global _hybrid_memory_service
    
    if _hybrid_memory_service is not None:
        return _hybrid_memory_service
    
    try:
        _hybrid_memory_service = HybridMemoryService(prefer_postgres=prefer_postgres)
        if _hybrid_memory_service.initialize():
            return _hybrid_memory_service
        else:
            logger.warning("Could not initialize HybridMemoryService")
            _hybrid_memory_service = None
            return None
    except Exception as e:
        logger.error(f"Error initializing HybridMemoryService: {e}")
        _hybrid_memory_service = None
        return None


# Export for backward compatibility
__all__ = [
    'HybridMemoryService',
    'get_hybrid_memory_service',
    'initialize_hybrid_memory_service',
]
