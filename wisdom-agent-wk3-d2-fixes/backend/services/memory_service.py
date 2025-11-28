"""
Wisdom Agent - Memory Service

Vector database operations with ChromaDB for semantic search.
Handles conversation and reflection embeddings with project awareness.

MIGRATION NOTES:
- Ported from knowledge_base/memory_manager.py
- Uses Config.CHROMA_PERSIST_DIR for paths
- Same interface preserved for compatibility
- ChromaDB kept for now (PostgreSQL + pgvector in Week 2)
"""

import os
from typing import List, Dict, Optional, Tuple

# Optional heavy dependencies - graceful degradation if not installed
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None
    CHROMADB_AVAILABLE = False

from backend.config import config


# Constants
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "wisdom_sessions"


class MemoryService:
    """
    Manages vector embeddings and semantic search for conversations and reflections.
    
    Features:
    - Store conversation and reflection embeddings
    - Semantic similarity search
    - Project-aware filtering
    - Session type tracking
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Memory Service with ChromaDB and embedding model.
        
        Args:
            db_path: Path to ChromaDB storage (uses config default if not provided)
        """
        self.db_path = db_path or str(config.CHROMA_PERSIST_DIR)
        self.client = None
        self.collection = None
        self.model = None
        self._initialized = False
        
        # Check for required dependencies
        self._dependencies_available = SENTENCE_TRANSFORMERS_AVAILABLE and CHROMADB_AVAILABLE
    
    def initialize(self) -> bool:
        """
        Initialize ChromaDB client, collection, and embedding model.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
        
        if not self._dependencies_available:
            print("Warning: Memory service dependencies not available.")
            print("  - sentence-transformers:", "✓" if SENTENCE_TRANSFORMERS_AVAILABLE else "✗ not installed")
            print("  - chromadb:", "✓" if CHROMADB_AVAILABLE else "✗ not installed")
            print("Install with: pip install sentence-transformers chromadb")
            return False
            
        try:
            # Ensure directory exists
            os.makedirs(self.db_path, exist_ok=True)
            
            # Initialize ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Load embedding model
            print(f"Loading embedding model: {EMBEDDING_MODEL}...")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            print("✓ Embedding model loaded")
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error initializing MemoryService: {e}")
            return False
    
    def _ensure_initialized(self):
        """Ensure service is initialized before operations."""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("MemoryService not initialized")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        self._ensure_initialized()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    # ========== STORE METHODS ==========
    
    def store(self, content: str, metadata: Dict) -> str:
        """
        Generic store method for any content type.
        
        Args:
            content: Text content to embed
            metadata: Must include 'type' (conversation/reflection/summary)
                     and 'session_id'
                     
        Returns:
            Embedding ID
        """
        self._ensure_initialized()
        
        content_type = metadata.get('type', 'unknown')
        session_id = metadata.get('session_id', 0)
        
        if content_type == 'conversation':
            return self.store_conversation(session_id, content, metadata)
        elif content_type == 'reflection':
            return self.store_reflection(session_id, content, metadata)
        else:
            # Generic storage
            embedding_id = f"{content_type}_{session_id:03d}"
            embedding = self.generate_embedding(content)
            preview_text = self._extract_preview(content)
            
            self.collection.upsert(
                embeddings=[embedding],
                documents=[preview_text],
                metadatas=[metadata],
                ids=[embedding_id]
            )
            return embedding_id
    
    def store_conversation(self, session_id: int, conversation_text: str, 
                          metadata: Dict) -> str:
        """
        Store conversation embedding in vector database.
        
        Args:
            session_id: Unique session identifier
            conversation_text: Full conversation text to embed
            metadata: Additional metadata (date, message_count, session_type, project, etc.)
            
        Returns:
            Embedding ID (conv_XXX)
        """
        self._ensure_initialized()
        
        embedding_id = f"conv_{session_id:03d}"
        embedding = self.generate_embedding(conversation_text)
        
        # Ensure required fields are set
        metadata_with_type = {
            **metadata, 
            "type": "conversation", 
            "session_id": session_id
        }
        
        # Ensure project and session_type have defaults
        if "project" not in metadata_with_type:
            metadata_with_type["project"] = None
        if "session_type" not in metadata_with_type:
            metadata_with_type["session_type"] = "wisdom_only"
        
        # Extract meaningful preview (skip headers, get actual dialogue)
        preview_text = self._extract_preview(conversation_text, skip_lines=3)
        
        self.collection.upsert(
            embeddings=[embedding],
            documents=[preview_text],
            metadatas=[metadata_with_type],
            ids=[embedding_id]
        )
        
        return embedding_id
    
    def store_reflection(self, session_id: int, reflection_text: str, 
                        metadata: Dict) -> str:
        """
        Store reflection embedding in vector database.
        
        Args:
            session_id: Unique session identifier
            reflection_text: Full reflection text to embed
            metadata: Additional metadata (date, scores, reflection_type, etc.)
            
        Returns:
            Embedding ID (refl_XXX or refl_ped_XXX)
        """
        self._ensure_initialized()
        
        # Different ID for pedagogical reflections
        reflection_type = metadata.get('reflection_type', 'wisdom')
        if reflection_type == 'pedagogical':
            embedding_id = f"refl_ped_{session_id:03d}"
        else:
            embedding_id = f"refl_{session_id:03d}"
        
        embedding = self.generate_embedding(reflection_text)
        
        metadata_with_type = {
            **metadata, 
            "type": "reflection", 
            "session_id": session_id
        }
        
        # Extract meaningful preview (skip header lines)
        preview_text = self._extract_preview(reflection_text, skip_lines=5)
        
        self.collection.upsert(
            embeddings=[embedding],
            documents=[preview_text],
            metadatas=[metadata_with_type],
            ids=[embedding_id]
        )
        
        return embedding_id
    
    # ========== SEARCH METHODS ==========
    
    def search(self, query: str, n_results: int = 3, 
               filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Generic search method with optional metadata filtering.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            filter_metadata: Optional dict with filters (type, session_type, project)
            
        Returns:
            List of search results with similarity scores
        """
        self._ensure_initialized()
        
        query_embedding = self.generate_embedding(query)
        
        # Build where clause from filter
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        return self._format_search_results(results)
    
    def search_similar_sessions(self, query: str, n_results: int = 3, 
                               search_type: Optional[str] = None,
                               session_type: Optional[str] = None,
                               project: Optional[str] = None) -> List[Dict]:
        """
        Search for semantically similar sessions with flexible filtering.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            search_type: Filter by type ("conversation", "reflection"), None for all
            session_type: Filter by session_type ("wisdom_only", "learning_only", etc.)
            project: Filter by project name
            
        Returns:
            List of dictionaries containing session info and similarity scores
        """
        self._ensure_initialized()
        
        query_embedding = self.generate_embedding(query)
        
        # Build where clause with multiple filters
        where_clause = {}
        if search_type:
            where_clause["type"] = search_type
        if session_type:
            where_clause["session_type"] = session_type
        if project:
            where_clause["project"] = project
        
        where = where_clause if where_clause else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        return self._format_search_results(results)
    
    def get_session_memory(self, session_id: int, n_results: int = 5) -> List[Dict]:
        """
        Get memory entries related to a specific session.
        
        Args:
            session_id: Session identifier
            n_results: Maximum results to return
            
        Returns:
            List of memory entries for this session
        """
        self._ensure_initialized()
        
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                limit=n_results
            )
            
            formatted = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted.append({
                        'embedding_id': results['ids'][i],
                        'session_id': results['metadatas'][i].get('session_id'),
                        'type': results['metadatas'][i].get('type'),
                        'metadata': results['metadatas'][i],
                        'text_preview': results['documents'][i][:200] if results['documents'][i] else ""
                    })
            return formatted
            
        except Exception as e:
            print(f"Error getting session memory: {e}")
            return []
    
    # ========== PROJECT METHODS ==========
    
    def search_by_project(self, project_name: str, n_results: int = 10) -> List[Dict]:
        """
        Get all sessions for a specific project.
        
        Args:
            project_name: Name of the project
            n_results: Maximum number of results
            
        Returns:
            List of sessions associated with the project
        """
        self._ensure_initialized()
        
        try:
            results = self.collection.get(
                where={"project": project_name},
                limit=n_results
            )
            
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'embedding_id': results['ids'][i],
                        'session_id': results['metadatas'][i]['session_id'],
                        'type': results['metadatas'][i]['type'],
                        'session_type': results['metadatas'][i].get('session_type', 'unknown'),
                        'project': results['metadatas'][i].get('project'),
                        'metadata': results['metadatas'][i],
                        'text_preview': results['documents'][i][:200] if results['documents'][i] else ""
                    })
            
            # Sort by session_id
            formatted_results.sort(key=lambda x: x['session_id'])
            return formatted_results
            
        except Exception as e:
            print(f"Error searching by project: {e}")
            return []
    
    def get_project_context(self, project_name: str, n_recent: int = 5) -> str:
        """
        Get recent context from a project for inclusion in prompts.
        
        Args:
            project_name: Name of the project
            n_recent: Number of recent sessions to include
            
        Returns:
            Formatted context string
        """
        sessions = self.search_by_project(project_name, n_results=n_recent)
        
        if not sessions:
            return ""
        
        context_parts = [f"\n\nRECENT SESSIONS IN PROJECT '{project_name}':"]
        
        for session in sessions[-n_recent:]:  # Most recent
            session_id = session['session_id']
            preview = session['text_preview']
            session_type = session.get('session_type', 'unknown')
            
            context_parts.append(
                f"\nSession {session_id:03d} [{session_type}]:\n  {preview}..."
            )
        
        return "\n".join(context_parts)
    
    def get_all_projects(self) -> List[str]:
        """
        Get list of all unique projects in memory.
        
        Returns:
            List of project names
        """
        self._ensure_initialized()
        
        try:
            all_docs = self.collection.get()
            
            projects = set()
            for metadata in all_docs['metadatas']:
                project = metadata.get('project')
                if project:
                    projects.add(project)
            
            return sorted(list(projects))
            
        except Exception as e:
            print(f"Error getting projects: {e}")
            return []
    
    # ========== STATS & UTILITY METHODS ==========
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the memory database.
        
        Returns:
            Dictionary with various statistics
        """
        self._ensure_initialized()
        
        try:
            all_docs = self.collection.get()
            
            total_docs = len(all_docs['ids'])
            
            # Count by type
            type_counts = {}
            session_type_counts = {}
            projects = set()
            
            for metadata in all_docs['metadatas']:
                doc_type = metadata.get('type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
                
                if doc_type == 'conversation':
                    session_type = metadata.get('session_type', 'unknown')
                    session_type_counts[session_type] = session_type_counts.get(session_type, 0) + 1
                    
                    project = metadata.get('project')
                    if project:
                        projects.add(project)
            
            return {
                'total_documents': total_docs,
                'by_type': type_counts,
                'by_session_type': session_type_counts,
                'total_projects': len(projects),
                'projects': sorted(list(projects))
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def get_session_types_count(self) -> Dict[str, int]:
        """
        Get count of sessions by type.
        
        Returns:
            Dictionary with counts per session type
        """
        self._ensure_initialized()
        
        try:
            all_docs = self.collection.get()
            
            type_counts = {}
            for metadata in all_docs['metadatas']:
                if metadata.get('type') == 'conversation':
                    session_type = metadata.get('session_type', 'unknown')
                    type_counts[session_type] = type_counts.get(session_type, 0) + 1
            
            return type_counts
            
        except Exception as e:
            print(f"Error getting type counts: {e}")
            return {}
    
    def get_session_embeddings(self, session_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get embedding IDs for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (conversation_id, wisdom_reflection_id, pedagogical_reflection_id)
        """
        self._ensure_initialized()
        
        conv_id = f"conv_{session_id:03d}"
        refl_id = f"refl_{session_id:03d}"
        refl_ped_id = f"refl_ped_{session_id:03d}"
        
        try:
            conv_exists = self.collection.get(ids=[conv_id])['ids']
            conv_id = conv_id if conv_exists else None
        except:
            conv_id = None
        
        try:
            refl_exists = self.collection.get(ids=[refl_id])['ids']
            refl_id = refl_id if refl_exists else None
        except:
            refl_id = None
        
        try:
            refl_ped_exists = self.collection.get(ids=[refl_ped_id])['ids']
            refl_ped_id = refl_ped_id if refl_ped_exists else None
        except:
            refl_ped_id = None
        
        return conv_id, refl_id, refl_ped_id
    
    def format_context_for_prompt(self, search_results: List[Dict], 
                                  include_project_info: bool = True) -> str:
        """
        Format search results into natural language for system prompt.
        
        Args:
            search_results: List of search result dictionaries
            include_project_info: Whether to include project/type info
            
        Returns:
            Formatted string for inclusion in system prompt
        """
        if not search_results:
            return ""
        
        context_parts = ["Here are some relevant past conversations:"]
        
        for i, result in enumerate(search_results, 1):
            session_id = result.get('session_id', 0)
            similarity = result.get('similarity_score', 0)
            preview = result.get('text_preview', '')
            
            extra_info = ""
            if include_project_info:
                session_type = result.get('session_type', 'unknown')
                project = result.get('project')
                
                if project:
                    extra_info = f" [Project: {project}, Type: {session_type}]"
                else:
                    extra_info = f" [Type: {session_type}]"
            
            context_parts.append(
                f"\n{i}. Session {session_id:03d}{extra_info} (similarity: {similarity:.2%}):\n   {preview}..."
            )
        
        return "\n".join(context_parts)
    
    # ========== PRIVATE HELPER METHODS ==========
    
    def _extract_preview(self, text: str, skip_lines: int = 0) -> str:
        """
        Extract meaningful preview text, skipping header lines.
        
        Args:
            text: Full text content
            skip_lines: Number of initial lines to skip
            
        Returns:
            Preview text (up to 500 chars of actual content)
        """
        lines = text.split('\n')
        
        # Skip header lines
        content_lines = lines[skip_lines:] if len(lines) > skip_lines else lines
        
        # Find first substantial line
        preview_start = 0
        for i, line in enumerate(content_lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('=') and not stripped.startswith('#'):
                preview_start = i
                break
        
        # Get meaningful content
        preview_lines = content_lines[preview_start:]
        preview = '\n'.join(preview_lines)
        
        return preview[:500] if len(preview) > 500 else preview
    
    def _format_search_results(self, results: Dict) -> List[Dict]:
        """
        Format ChromaDB query results into a consistent structure.
        
        Args:
            results: Raw ChromaDB query results
            
        Returns:
            List of formatted result dictionaries
        """
        formatted_results = []
        
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'embedding_id': results['ids'][0][i],
                    'session_id': results['metadatas'][0][i].get('session_id', 0),
                    'type': results['metadatas'][0][i].get('type', 'unknown'),
                    'session_type': results['metadatas'][0][i].get('session_type', 'unknown'),
                    'project': results['metadatas'][0][i].get('project'),
                    'similarity_score': 1 - results['distances'][0][i] if results['distances'] else 0,
                    'metadata': results['metadatas'][0][i],
                    'text_preview': results['documents'][0][i][:200] if results['documents'][0][i] else ""
                })
        
        return formatted_results


# ========== SINGLETON & FACTORY ==========

# Singleton instance (lazy initialization)
_memory_service: Optional[MemoryService] = None


def memory_dependencies_available() -> bool:
    """Check if memory service dependencies are installed."""
    return SENTENCE_TRANSFORMERS_AVAILABLE and CHROMADB_AVAILABLE


def get_memory_service() -> Optional[MemoryService]:
    """
    Get the singleton MemoryService instance.
    
    Returns:
        MemoryService instance or None if not initialized
    """
    global _memory_service
    return _memory_service


def initialize_memory_service() -> Optional[MemoryService]:
    """
    Initialize and return the singleton MemoryService.
    
    Returns:
        MemoryService instance or None if initialization fails
    """
    global _memory_service
    
    if _memory_service is not None:
        return _memory_service
    
    if not memory_dependencies_available():
        print("Warning: Memory service dependencies not installed.")
        print("  Install with: pip install sentence-transformers chromadb")
        print("  Continuing without semantic memory features...")
        return None
    
    try:
        _memory_service = MemoryService()
        if _memory_service.initialize():
            return _memory_service
        else:
            _memory_service = None
            return None
    except Exception as e:
        print(f"Warning: Could not initialize MemoryService: {e}")
        print("Continuing without semantic memory features...")
        _memory_service = None
        return None
