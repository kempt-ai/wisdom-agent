"""
Wisdom Agent - PostgreSQL Session Repository

Handles CRUD operations for sessions, messages, summaries, and reflections.
Used by conversation_service for high-level session management.

Author: Wisdom Agent Team
Date: 2025-11-24
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import Session as DBSession, joinedload

from backend.database.connection import get_db_session
from backend.database.models import (
    Session, Message, SessionSummary, SessionReflection,
    Project, User, SessionType
)

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for session-related database operations."""
    
    def __init__(self):
        """Initialize the session repository."""
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
            logger.info("SessionRepository initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SessionRepository: {e}")
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if repository is initialized."""
        return self._initialized and self.db_session is not None
    
    # ===========================================
    # Session CRUD Operations
    # ===========================================
    
    def create_session(
        self,
        project_id: int,
        user_id: int,
        session_number: Optional[int] = None,
        title: Optional[str] = None,
        session_type: SessionType = SessionType.GENERAL,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None
    ) -> Optional[Session]:
        """
        Create a new session.
        
        Args:
            project_id: ID of the project
            user_id: ID of the user
            session_number: Session number (auto-generated if None)
            title: Optional session title
            session_type: Type of session
            llm_provider: LLM provider used
            llm_model: LLM model used
            
        Returns:
            Session object if successful, None otherwise
        """
        if not self.is_initialized():
            logger.error("SessionRepository not initialized")
            return None
        
        try:
            # Auto-generate session number if not provided
            if session_number is None:
                max_session = self.db_session.query(
                    func.max(Session.session_number)
                ).filter(
                    Session.project_id == project_id
                ).scalar()
                session_number = (max_session or 0) + 1
            
            # Create session
            session = Session(
                session_number=session_number,
                title=title,
                session_type=session_type,
                llm_provider=llm_provider,
                llm_model=llm_model,
                project_id=project_id,
                user_id=user_id,
                started_at=datetime.utcnow()
            )
            
            self.db_session.add(session)
            self.db_session.commit()
            self.db_session.refresh(session)
            
            logger.info(f"Created session {session.id} (#{session_number}) for project {project_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            self.db_session.rollback()
            return None
    
    def get_session(self, session_id: int, load_messages: bool = False) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            load_messages: Whether to eagerly load messages
            
        Returns:
            Session object if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            query = select(Session).where(Session.id == session_id)
            
            if load_messages:
                query = query.options(joinedload(Session.messages))
            
            result = self.db_session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    def get_sessions_by_project(
        self,
        project_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """
        Get all sessions for a project.
        
        Args:
            project_id: Project ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of Session objects
        """
        if not self.is_initialized():
            return []
        
        try:
            query = select(Session).where(
                Session.project_id == project_id
            ).order_by(
                desc(Session.session_number)
            ).limit(limit).offset(offset)
            
            result = self.db_session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting sessions for project {project_id}: {e}")
            return []
    
    def get_sessions_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of Session objects
        """
        if not self.is_initialized():
            return []
        
        try:
            query = select(Session).where(
                Session.user_id == user_id
            ).order_by(
                desc(Session.created_at)
            ).limit(limit).offset(offset)
            
            result = self.db_session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    def update_session(
        self,
        session_id: int,
        **kwargs
    ) -> Optional[Session]:
        """
        Update a session.
        
        Args:
            session_id: Session ID
            **kwargs: Fields to update (title, session_type, ended_at, etc.)
            
        Returns:
            Updated Session object if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            session = self.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            session.updated_at = datetime.utcnow()
            self.db_session.commit()
            self.db_session.refresh(session)
            
            logger.info(f"Updated session {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            self.db_session.rollback()
            return None
    
    def end_session(self, session_id: int) -> bool:
        """
        Mark a session as ended.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.update_session(session_id, ended_at=datetime.utcnow())
        return result is not None
    
    def delete_session(self, session_id: int) -> bool:
        """
        Delete a session (cascades to messages, summary, reflection).
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized():
            return False
        
        try:
            session = self.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            self.db_session.delete(session)
            self.db_session.commit()
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            self.db_session.rollback()
            return False
    
    # ===========================================
    # Message Operations
    # ===========================================
    
    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        token_count: Optional[int] = None
    ) -> Optional[Message]:
        """
        Add a message to a session.
        
        Args:
            session_id: Session ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            token_count: Optional token count
            
        Returns:
            Message object if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            # Get current max message index for this session
            max_index = self.db_session.query(
                func.max(Message.message_index)
            ).filter(
                Message.session_id == session_id
            ).scalar()
            
            message_index = (max_index or -1) + 1
            
            # Create message
            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                message_index=message_index,
                token_count=token_count
            )
            
            self.db_session.add(message)
            self.db_session.commit()
            self.db_session.refresh(message)
            
            logger.debug(f"Added message {message.id} to session {session_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            self.db_session.rollback()
            return None
    
    def get_messages(
        self,
        session_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get all messages for a session.
        
        Args:
            session_id: Session ID
            limit: Optional limit on number of messages
            
        Returns:
            List of Message objects ordered by message_index
        """
        if not self.is_initialized():
            return []
        
        try:
            query = select(Message).where(
                Message.session_id == session_id
            ).order_by(Message.message_index)
            
            if limit:
                query = query.limit(limit)
            
            result = self.db_session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
    
    def get_conversation_history(
        self,
        session_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history in LLM-friendly format.
        
        Args:
            session_id: Session ID
            limit: Optional limit on number of messages
            
        Returns:
            List of dicts with 'role' and 'content' keys
        """
        messages = self.get_messages(session_id, limit)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    # ===========================================
    # Summary Operations
    # ===========================================
    
    def create_summary(
        self,
        session_id: int,
        summary_text: str,
        key_topics: Optional[List[str]] = None,
        learning_outcomes: Optional[List[str]] = None
    ) -> Optional[SessionSummary]:
        """
        Create or update a session summary.
        
        Args:
            session_id: Session ID
            summary_text: Summary text
            key_topics: List of key topics
            learning_outcomes: List of learning outcomes
            
        Returns:
            SessionSummary object if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            # Check if summary already exists
            existing = self.db_session.query(SessionSummary).filter(
                SessionSummary.session_id == session_id
            ).first()
            
            if existing:
                # Update existing
                existing.summary_text = summary_text
                existing.key_topics = key_topics
                existing.learning_outcomes = learning_outcomes
                existing.updated_at = datetime.utcnow()
                summary = existing
            else:
                # Create new
                summary = SessionSummary(
                    session_id=session_id,
                    summary_text=summary_text,
                    key_topics=key_topics,
                    learning_outcomes=learning_outcomes
                )
                self.db_session.add(summary)
            
            self.db_session.commit()
            self.db_session.refresh(summary)
            
            logger.info(f"Created/updated summary for session {session_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error creating summary for session {session_id}: {e}")
            self.db_session.rollback()
            return None
    
    def get_summary(self, session_id: int) -> Optional[SessionSummary]:
        """
        Get summary for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionSummary object if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            result = self.db_session.query(SessionSummary).filter(
                SessionSummary.session_id == session_id
            ).first()
            return result
            
        except Exception as e:
            logger.error(f"Error getting summary for session {session_id}: {e}")
            return None
    
    # ===========================================
    # Reflection Operations
    # ===========================================
    
    def create_reflection(
        self,
        session_id: int,
        reflection_text: str,
        scores: Dict[str, float],
        insights: Optional[List[str]] = None,
        growth_areas: Optional[List[str]] = None
    ) -> Optional[SessionReflection]:
        """
        Create or update a session reflection with 7 Universal Values scores.
        
        Args:
            session_id: Session ID
            reflection_text: Reflection text
            scores: Dict with keys: awareness, honesty, accuracy, competence,
                   compassion, loving_kindness, joyful_sharing
            insights: List of insights
            growth_areas: List of growth areas
            
        Returns:
            SessionReflection object if successful, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            # Check if reflection already exists
            existing = self.db_session.query(SessionReflection).filter(
                SessionReflection.session_id == session_id
            ).first()
            
            if existing:
                # Update existing
                existing.reflection_text = reflection_text
                existing.awareness_score = scores.get('awareness', 0.0)
                existing.honesty_score = scores.get('honesty', 0.0)
                existing.accuracy_score = scores.get('accuracy', 0.0)
                existing.competence_score = scores.get('competence', 0.0)
                existing.compassion_score = scores.get('compassion', 0.0)
                existing.loving_kindness_score = scores.get('loving_kindness', 0.0)
                existing.joyful_sharing_score = scores.get('joyful_sharing', 0.0)
                existing.insights = insights
                existing.growth_areas = growth_areas
                existing.updated_at = datetime.utcnow()
                reflection = existing
            else:
                # Create new
                reflection = SessionReflection(
                    session_id=session_id,
                    reflection_text=reflection_text,
                    awareness_score=scores.get('awareness', 0.0),
                    honesty_score=scores.get('honesty', 0.0),
                    accuracy_score=scores.get('accuracy', 0.0),
                    competence_score=scores.get('competence', 0.0),
                    compassion_score=scores.get('compassion', 0.0),
                    loving_kindness_score=scores.get('loving_kindness', 0.0),
                    joyful_sharing_score=scores.get('joyful_sharing', 0.0),
                    insights=insights,
                    growth_areas=growth_areas
                )
                self.db_session.add(reflection)
            
            self.db_session.commit()
            self.db_session.refresh(reflection)
            
            logger.info(f"Created/updated reflection for session {session_id}")
            return reflection
            
        except Exception as e:
            logger.error(f"Error creating reflection for session {session_id}: {e}")
            self.db_session.rollback()
            return None
    
    def get_reflection(self, session_id: int) -> Optional[SessionReflection]:
        """
        Get reflection for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionReflection object if found, None otherwise
        """
        if not self.is_initialized():
            return None
        
        try:
            result = self.db_session.query(SessionReflection).filter(
                SessionReflection.session_id == session_id
            ).first()
            return result
            
        except Exception as e:
            logger.error(f"Error getting reflection for session {session_id}: {e}")
            return None
    
    # ===========================================
    # Statistics & Reporting
    # ===========================================
    
    def get_session_count(self, project_id: Optional[int] = None, user_id: Optional[int] = None) -> int:
        """
        Get count of sessions.
        
        Args:
            project_id: Optional project filter
            user_id: Optional user filter
            
        Returns:
            int: Number of sessions
        """
        if not self.is_initialized():
            return 0
        
        try:
            query = select(func.count(Session.id))
            
            if project_id:
                query = query.where(Session.project_id == project_id)
            if user_id:
                query = query.where(Session.user_id == user_id)
            
            result = self.db_session.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting session count: {e}")
            return 0
    
    def get_message_count(self, session_id: int) -> int:
        """
        Get count of messages in a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            int: Number of messages
        """
        if not self.is_initialized():
            return 0
        
        try:
            count = self.db_session.query(func.count(Message.id)).filter(
                Message.session_id == session_id
            ).scalar()
            return count or 0
            
        except Exception as e:
            logger.error(f"Error getting message count for session {session_id}: {e}")
            return 0
    
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
            session_count = self.get_session_count()
            message_count = self.db_session.query(func.count(Message.id)).scalar() or 0
            summary_count = self.db_session.query(func.count(SessionSummary.id)).scalar() or 0
            reflection_count = self.db_session.query(func.count(SessionReflection.id)).scalar() or 0
            
            return {
                "initialized": True,
                "backend": "postgresql",
                "sessions": session_count,
                "messages": message_count,
                "summaries": summary_count,
                "reflections": reflection_count
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "initialized": True,
                "backend": "postgresql",
                "error": str(e)
            }


# Singleton instance
_session_repository = None


def get_session_repository() -> SessionRepository:
    """Get or create singleton session repository."""
    global _session_repository
    if _session_repository is None:
        _session_repository = SessionRepository()
    return _session_repository
