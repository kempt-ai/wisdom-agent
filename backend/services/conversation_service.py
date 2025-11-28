"""
Wisdom Agent - Conversation Service

High-level service for managing conversation sessions.
Orchestrates session repository, memory service, and reflection service.

Author: Wisdom Agent Team
Date: 2025-11-24
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from backend.services.session_repository import get_session_repository
from backend.services.hybrid_memory_service import get_hybrid_memory_service as get_memory_service
from backend.services.reflection_service import ReflectionService
from backend.database.models import SessionType

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation sessions."""
    
    def __init__(self):
        """Initialize conversation service."""
        self.session_repo = get_session_repository()
        self.memory_service = get_memory_service()
        self.reflection_service = None  # Lazy loaded
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize all dependencies.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Initialize session repository
            if not self.session_repo.initialize():
                logger.error("Failed to initialize session repository")
                return False
            
            # Initialize memory service
            if not self.memory_service.initialize():
                logger.warning("Failed to initialize memory service (continuing anyway)")
            
            # Reflection service initialized on demand
            
            self._initialized = True
            logger.info("ConversationService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ConversationService: {e}")
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def _get_reflection_service(self) -> Optional[ReflectionService]:
        """Lazy load reflection service."""
        if self.reflection_service is None:
            try:
                self.reflection_service = ReflectionService()
                self.reflection_service.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize reflection service: {e}")
        return self.reflection_service
    
    # ===========================================
    # Session Management
    # ===========================================
    
    def start_session(
        self,
        project_id: int,
        user_id: int = 1,
        title: Optional[str] = None,
        session_type: str = "general",
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Start a new conversation session.
        
        Args:
            project_id: ID of the project
            user_id: ID of the user (default: 1)
            title: Optional session title
            session_type: Type of session
            llm_provider: LLM provider being used
            llm_model: LLM model being used
            
        Returns:
            Dict with session info if successful, None otherwise
        """
        if not self.is_initialized():
            logger.error("ConversationService not initialized")
            return None
        
        try:
            # Convert session_type string to enum
            try:
                session_type_enum = SessionType[session_type.upper()]
            except KeyError:
                logger.warning(f"Unknown session type '{session_type}', using GENERAL")
                session_type_enum = SessionType.GENERAL
            
            # Create session
            session = self.session_repo.create_session(
                project_id=project_id,
                user_id=user_id,
                title=title,
                session_type=session_type_enum,
                llm_provider=llm_provider,
                llm_model=llm_model
            )
            
            if not session:
                logger.error("Failed to create session")
                return None
            
            return {
                "session_id": session.id,
                "session_number": session.session_number,
                "project_id": session.project_id,
                "user_id": session.user_id,
                "title": session.title,
                "session_type": session.session_type.value,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "message_count": 0
            }
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return None
    
    def get_session_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with session info if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            session = self.session_repo.get_session(session_id)
            if not session:
                return None
            
            message_count = self.session_repo.get_message_count(session_id)
            summary = self.session_repo.get_summary(session_id)
            reflection = self.session_repo.get_reflection(session_id)
            
            return {
                "session_id": session.id,
                "session_number": session.session_number,
                "project_id": session.project_id,
                "user_id": session.user_id,
                "title": session.title,
                "session_type": session.session_type.value,
                "llm_provider": session.llm_provider,
                "llm_model": session.llm_model,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "message_count": message_count,
                "has_summary": summary is not None,
                "has_reflection": reflection is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None
    
    def list_sessions(
        self,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filters.
        
        Args:
            project_id: Optional project filter
            user_id: Optional user filter
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of session info dicts
        """
        if not self.is_initialized():
            return []
        
        try:
            if project_id:
                sessions = self.session_repo.get_sessions_by_project(project_id, limit, offset)
            elif user_id:
                sessions = self.session_repo.get_sessions_by_user(user_id, limit, offset)
            else:
                logger.warning("No filter provided, returning empty list")
                return []
            
            result = []
            for session in sessions:
                message_count = self.session_repo.get_message_count(session.id)
                result.append({
                    "session_id": session.id,
                    "session_number": session.session_number,
                    "project_id": session.project_id,
                    "title": session.title,
                    "session_type": session.session_type.value,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "message_count": message_count
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []
    
    def end_session(
        self,
        session_id: int,
        generate_summary: bool = True,
        generate_reflection: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        End a session and optionally generate summary and reflection.
        
        Args:
            session_id: Session ID
            generate_summary: Whether to generate summary
            generate_reflection: Whether to generate reflection
            
        Returns:
            Dict with session info and generated content if successful
        """
        if not self.is_initialized():
            return None
        
        try:
            # Mark session as ended
            if not self.session_repo.end_session(session_id):
                logger.error(f"Failed to end session {session_id}")
                return None
            
            result = {
                "session_id": session_id,
                "ended_at": datetime.utcnow().isoformat(),
                "summary_generated": False,
                "reflection_generated": False
            }
            
            # Get conversation history for summary/reflection
            messages = self.session_repo.get_conversation_history(session_id)
            
            # Generate summary if requested
            if generate_summary and messages:
                try:
                    reflection_service = self._get_reflection_service()
                    if reflection_service:
                        summary_text = reflection_service.generate_summary(messages)
                        if summary_text:
                            self.session_repo.create_summary(
                                session_id=session_id,
                                summary_text=summary_text,
                                key_topics=[],
                                learning_outcomes=[]
                            )
                            result["summary_generated"] = True
                            result["summary"] = summary_text
                except Exception as e:
                    logger.error(f"Error generating summary: {e}")
            
            # Generate reflection if requested
            if generate_reflection and messages:
                try:
                    reflection_service = self._get_reflection_service()
                    if reflection_service:
                        reflection_result = reflection_service.generate_reflection(messages)
                        if reflection_result and 'reflection_text' in reflection_result:
                            self.session_repo.create_reflection(
                                session_id=session_id,
                                reflection_text=reflection_result['reflection_text'],
                                scores=reflection_result.get('scores', {}),
                                insights=reflection_result.get('insights', []),
                                growth_areas=reflection_result.get('growth_areas', [])
                            )
                            result["reflection_generated"] = True
                            result["reflection"] = reflection_result
                except Exception as e:
                    logger.error(f"Error generating reflection: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return None
    
    # ===========================================
    # Message Management
    # ===========================================
    
    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        store_in_memory: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Add a message to the session.
        
        Args:
            session_id: Session ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            store_in_memory: Whether to also store in vector memory
            
        Returns:
            Dict with message info if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            # Add to database
            message = self.session_repo.add_message(
                session_id=session_id,
                role=role,
                content=content
            )
            
            if not message:
                logger.error("Failed to add message to database")
                return None
            
            # Store in vector memory if requested
            if store_in_memory and role in ['user', 'assistant']:
                try:
                    self.memory_service.store_memory(
                        content=content,
                        user_id=1,  # TODO: Get from session
                        session_id=session_id,
                        content_type=f'{role}_message',
                        meta_data={'role': role}
                    )
                except Exception as e:
                    logger.warning(f"Failed to store message in vector memory: {e}")
            
            return {
                "message_id": message.id,
                "session_id": message.session_id,
                "role": message.role,
                "content": message.content,
                "message_index": message.message_index,
                "created_at": message.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return None
    
    def get_conversation_history(
        self,
        session_id: int,
        limit: Optional[int] = None,
        format: str = "dict"
    ) -> Any:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            limit: Optional limit on number of messages
            format: 'dict' for LLM format, 'messages' for Message objects
            
        Returns:
            List of messages in requested format
        """
        if not self.is_initialized():
            return []
        
        try:
            if format == "dict":
                return self.session_repo.get_conversation_history(session_id, limit)
            elif format == "messages":
                return self.session_repo.get_messages(session_id, limit)
            else:
                logger.error(f"Unknown format: {format}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    # ===========================================
    # Summary & Reflection
    # ===========================================
    
    def get_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get session summary.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with summary info if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            summary = self.session_repo.get_summary(session_id)
            if not summary:
                return None
            
            return {
                "session_id": summary.session_id,
                "summary_text": summary.summary_text,
                "key_topics": summary.key_topics or [],
                "learning_outcomes": summary.learning_outcomes or [],
                "created_at": summary.created_at.isoformat(),
                "updated_at": summary.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return None
    
    def get_reflection(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get session reflection with 7 Universal Values scores.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with reflection info if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            reflection = self.session_repo.get_reflection(session_id)
            if not reflection:
                return None
            
            return {
                "session_id": reflection.session_id,
                "reflection_text": reflection.reflection_text,
                "scores": {
                    "awareness": reflection.awareness_score,
                    "honesty": reflection.honesty_score,
                    "accuracy": reflection.accuracy_score,
                    "competence": reflection.competence_score,
                    "compassion": reflection.compassion_score,
                    "loving_kindness": reflection.loving_kindness_score,
                    "joyful_sharing": reflection.joyful_sharing_score
                },
                "insights": reflection.insights or [],
                "growth_areas": reflection.growth_areas or [],
                "created_at": reflection.created_at.isoformat(),
                "updated_at": reflection.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting reflection: {e}")
            return None
    
    def generate_summary(
        self,
        session_id: int,
        force_regenerate: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Generate or retrieve session summary.
        
        Args:
            session_id: Session ID
            force_regenerate: Force regeneration even if summary exists
            
        Returns:
            Dict with summary info if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            # Check if summary already exists
            if not force_regenerate:
                existing = self.get_summary(session_id)
                if existing:
                    return existing
            
            # Get conversation history
            messages = self.session_repo.get_conversation_history(session_id)
            if not messages:
                logger.error(f"No messages found for session {session_id}")
                return None
            
            # Generate summary
            reflection_service = self._get_reflection_service()
            if not reflection_service:
                logger.error("Reflection service not available")
                return None
            
            summary_text = reflection_service.generate_summary(messages)
            if not summary_text:
                logger.error("Failed to generate summary")
                return None
            
            # Store summary
            summary_obj = self.session_repo.create_summary(
                session_id=session_id,
                summary_text=summary_text,
                key_topics=[],
                learning_outcomes=[]
            )
            
            if not summary_obj:
                logger.error("Failed to store summary")
                return None
            
            return self.get_summary(session_id)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None
    
    def generate_reflection(
        self,
        session_id: int,
        force_regenerate: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Generate or retrieve session reflection with 7 Universal Values scores.
        
        Args:
            session_id: Session ID
            force_regenerate: Force regeneration even if reflection exists
            
        Returns:
            Dict with reflection info if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            # Check if reflection already exists
            if not force_regenerate:
                existing = self.get_reflection(session_id)
                if existing:
                    return existing
            
            # Get conversation history
            messages = self.session_repo.get_conversation_history(session_id)
            if not messages:
                logger.error(f"No messages found for session {session_id}")
                return None
            
            # Generate reflection
            reflection_service = self._get_reflection_service()
            if not reflection_service:
                logger.error("Reflection service not available")
                return None
            
            reflection_result = reflection_service.generate_reflection(messages)
            if not reflection_result or 'reflection_text' not in reflection_result:
                logger.error("Failed to generate reflection")
                return None
            
            # Store reflection
            reflection_obj = self.session_repo.create_reflection(
                session_id=session_id,
                reflection_text=reflection_result['reflection_text'],
                scores=reflection_result.get('scores', {}),
                insights=reflection_result.get('insights', []),
                growth_areas=reflection_result.get('growth_areas', [])
            )
            
            if not reflection_obj:
                logger.error("Failed to store reflection")
                return None
            
            return self.get_reflection(session_id)
            
        except Exception as e:
            logger.error(f"Error generating reflection: {e}")
            return None
    
    # ===========================================
    # Statistics
    # ===========================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get service status and statistics.
        
        Returns:
            Dict with status information
        """
        if not self.is_initialized():
            return {
                "initialized": False,
                "error": "Not initialized"
            }
        
        try:
            session_stats = self.session_repo.get_status()
            memory_stats = self.memory_service.get_status()
            
            return {
                "initialized": True,
                "session_repository": session_stats,
                "memory_service": memory_stats,
                "reflection_service_loaded": self.reflection_service is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "initialized": True,
                "error": str(e)
            }


# Singleton instance
_conversation_service = None


def get_conversation_service() -> ConversationService:
    """Get or create singleton conversation service."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
