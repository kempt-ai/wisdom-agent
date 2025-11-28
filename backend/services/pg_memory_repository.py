"""
Wisdom Agent - PostgreSQL Memory Repository

PostgreSQL + pgvector implementation for semantic memory search.
This replaces ChromaDB with a more scalable database solution.
"""

from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.database.connection import SessionLocal
from backend.database.models import Memory

# Optional dependency - graceful degradation if not installed
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False


# Constants
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class PostgresMemoryRepository:
    """
    PostgreSQL + pgvector repository for vector memories.
    
    Features:
    - Store embeddings with metadata
    - Semantic similarity search using cosine distance
    - Project and session filtering
    - Efficient vector indexing with pgvector
    """
    
    def __init__(self):
        """Initialize the PostgreSQL memory repository."""
        self.model = None
        self._initialized = False
        self._dependencies_available = SENTENCE_TRANSFORMERS_AVAILABLE
    
    def initialize(self) -> bool:
        """
        Initialize the embedding model.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
        
        if not self._dependencies_available:
            print("Warning: sentence-transformers not available")
            print("Install with: pip install sentence-transformers")
            return False
        
        try:
            print(f"Loading embedding model: {EMBEDDING_MODEL}...")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            print("✓ Embedding model loaded")
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing PostgresMemoryRepository: {e}")
            return False
    
    def _ensure_initialized(self):
        """Ensure service is initialized before operations."""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("PostgresMemoryRepository not initialized")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector (384-dimensional)
        """
        self._ensure_initialized()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    # ========== STORE METHODS ==========
    
    def store_memory(
        self,
        content: str,
        user_id: int,
        session_id: Optional[int] = None,
        project_id: Optional[int] = None,
        meta_data: Optional[Dict] = None
    ) -> int:
        """
        Store a memory with its embedding.
        
        Args:
            content: Text content to embed
            user_id: User ID who owns this memory
            session_id: Optional session ID
            project_id: Optional project ID
            meta_data: Optional metadata dictionary
            
        Returns:
            Memory ID
        """
        self._ensure_initialized()
        
        # Generate embedding
        embedding = self.generate_embedding(content)
        
        # Create memory record
        db = SessionLocal()
        try:
            memory = Memory(
                content=content,
                embedding=embedding,
                user_id=user_id,
                session_id=session_id,
                project_id=project_id,
                meta_data=meta_data or {}
            )
            db.add(memory)
            db.commit()
            db.refresh(memory)
            return memory.id
        finally:
            db.close()
    
    # ========== SEARCH METHODS ==========
    
    def search_similar(
        self,
        query: str,
        user_id: int,
        n_results: int = 5,
        session_id: Optional[int] = None,
        project_id: Optional[int] = None,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for semantically similar memories using cosine similarity.
        
        Args:
            query: Search query text
            user_id: User ID to filter by
            n_results: Number of results to return
            session_id: Optional filter by session
            project_id: Optional filter by project
            metadata_filter: Optional filter by metadata fields
            
        Returns:
            List of similar memories with scores
        """
        self._ensure_initialized()
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        db = SessionLocal()
        try:
            # Build query with filters
            query_obj = db.query(
                Memory.id,
                Memory.content,
                Memory.session_id,
                Memory.project_id,
                Memory.meta_data,
                Memory.created_at,
                Memory.embedding.cosine_distance(query_embedding).label('distance')
            ).filter(
                Memory.user_id == user_id
            )
            
            # Apply optional filters
            if session_id is not None:
                query_obj = query_obj.filter(Memory.session_id == session_id)
            if project_id is not None:
                query_obj = query_obj.filter(Memory.project_id == project_id)
            
            # Apply metadata filters if provided
            if metadata_filter:
                for key, value in metadata_filter.items():
                    query_obj = query_obj.filter(
                        Memory.meta_data[key].astext == str(value)
                    )
            
            # Order by similarity (lower distance = more similar)
            results = query_obj.order_by('distance').limit(n_results).all()
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'content': result.content,
                    'session_id': result.session_id,
                    'project_id': result.project_id,
                    'metadata': result.meta_data,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'similarity': 1 - result.distance,  # Convert distance to similarity
                    'distance': result.distance
                })
            
            return formatted_results
            
        finally:
            db.close()
    
    def get_session_memories(
        self,
        session_id: int,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get all memories for a specific session.
        
        Args:
            session_id: Session identifier
            user_id: User ID
            limit: Maximum results to return
            
        Returns:
            List of memories from this session
        """
        db = SessionLocal()
        try:
            memories = db.query(Memory).filter(
                and_(
                    Memory.session_id == session_id,
                    Memory.user_id == user_id
                )
            ).order_by(
                Memory.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': m.id,
                    'content': m.content,
                    'session_id': m.session_id,
                    'project_id': m.project_id,
                    'metadata': m.meta_data,
                    'created_at': m.created_at.isoformat() if m.created_at else None
                }
                for m in memories
            ]
            
        finally:
            db.close()
    
    def get_project_memories(
        self,
        project_id: int,
        user_id: int,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get all memories for a specific project.
        
        Args:
            project_id: Project identifier
            user_id: User ID
            limit: Maximum results to return
            
        Returns:
            List of memories from this project
        """
        db = SessionLocal()
        try:
            memories = db.query(Memory).filter(
                and_(
                    Memory.project_id == project_id,
                    Memory.user_id == user_id
                )
            ).order_by(
                Memory.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': m.id,
                    'content': m.content,
                    'session_id': m.session_id,
                    'project_id': m.project_id,
                    'metadata': m.meta_data,
                    'created_at': m.created_at.isoformat() if m.created_at else None
                }
                for m in memories
            ]
            
        finally:
            db.close()
    
    def count_memories(self, user_id: int) -> int:
        """
        Count total memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Total number of memories
        """
        db = SessionLocal()
        try:
            return db.query(func.count(Memory.id)).filter(
                Memory.user_id == user_id
            ).scalar()
        finally:
            db.close()
    
    def delete_memory(self, memory_id: int, user_id: int) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: Memory ID to delete
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted, False if not found
        """
        db = SessionLocal()
        try:
            memory = db.query(Memory).filter(
                and_(
                    Memory.id == memory_id,
                    Memory.user_id == user_id
                )
            ).first()
            
            if memory:
                db.delete(memory)
                db.commit()
                return True
            return False
            
        finally:
            db.close()
    
    def delete_session_memories(self, session_id: int, user_id: int) -> int:
        """
        Delete all memories for a session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            
        Returns:
            Number of memories deleted
        """
        db = SessionLocal()
        try:
            deleted = db.query(Memory).filter(
                and_(
                    Memory.session_id == session_id,
                    Memory.user_id == user_id
                )
            ).delete()
            db.commit()
            return deleted
            
        finally:
            db.close()
    
    def get_status(self) -> Dict:
        """
        Get repository status information.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'initialized': self._initialized,
            'dependencies_available': self._dependencies_available,
            'embedding_model': EMBEDDING_MODEL if self._initialized else None,
            'embedding_dimension': EMBEDDING_DIMENSION,
        }
        
        if self._initialized:
            db = SessionLocal()
            try:
                # Get total memory count
                total_memories = db.query(func.count(Memory.id)).scalar()
                status['total_memories'] = total_memories
                
                # Get unique user count
                unique_users = db.query(func.count(Memory.user_id.distinct())).scalar()
                status['unique_users'] = unique_users
                
            finally:
                db.close()
        
        return status
