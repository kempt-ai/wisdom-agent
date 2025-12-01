"""
Wisdom Agent - Conversation Service

Manages sessions, messages, and conversation persistence.
This service connects the sessions API to the database and other services.

Created: Week 3 Day 3
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from backend.config import config


# Singleton instance
_conversation_service: Optional['ConversationService'] = None


class ConversationService:
    """
    Manages conversation sessions, messages, and related data.
    
    Provides a unified interface for:
    - Creating and managing sessions
    - Storing and retrieving messages
    - Generating summaries and reflections
    - Connecting to memory service for semantic search
    """
    
    def __init__(self, llm_router=None):
        """
        Initialize the Conversation Service.
        
        Args:
            llm_router: LLMRouter instance for generating summaries/reflections
        """
        self.llm_router = llm_router
        self._initialized = False
        self._sessions: Dict[int, Dict] = {}  # In-memory session storage
        self._messages: Dict[int, List[Dict]] = {}  # session_id -> messages
        self._next_session_id = 1
        self._next_message_id = 1
        
        # Load session counter from file if exists
        self._counter_file = config.DATA_DIR / "session_counter.json"
        self._load_counters()
    
    def _load_counters(self):
        """Load session/message counters from persistent storage."""
        if self._counter_file.exists():
            try:
                with open(self._counter_file, 'r') as f:
                    data = json.load(f)
                    self._next_session_id = data.get('next_session_id', 1)
                    self._next_message_id = data.get('next_message_id', 1)
            except Exception as e:
                print(f"Warning: Could not load counters: {e}")
    
    def _save_counters(self):
        """Save session/message counters to persistent storage."""
        try:
            with open(self._counter_file, 'w') as f:
                json.dump({
                    'next_session_id': self._next_session_id,
                    'next_message_id': self._next_message_id
                }, f)
        except Exception as e:
            print(f"Warning: Could not save counters: {e}")
    
    def initialize(self) -> bool:
        """
        Initialize the conversation service.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        try:
            # Ensure data directories exist
            config.CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Load existing sessions from disk
            self._load_sessions_from_disk()
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Error initializing ConversationService: {e}")
            return False
    
    def _load_sessions_from_disk(self):
        """Load existing sessions from the conversations directory."""
        sessions_index = config.CONVERSATIONS_DIR / "sessions_index.json"
        if sessions_index.exists():
            try:
                with open(sessions_index, 'r') as f:
                    data = json.load(f)
                    self._sessions = {int(k): v for k, v in data.get('sessions', {}).items()}
                    self._next_session_id = data.get('next_session_id', 1)
            except Exception as e:
                print(f"Warning: Could not load sessions index: {e}")
    
    def _save_sessions_index(self):
        """Save sessions index to disk."""
        sessions_index = config.CONVERSATIONS_DIR / "sessions_index.json"
        try:
            with open(sessions_index, 'w') as f:
                json.dump({
                    'sessions': self._sessions,
                    'next_session_id': self._next_session_id
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save sessions index: {e}")
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def get_status(self) -> Dict:
        """Get service status and statistics."""
        return {
            "initialized": self._initialized,
            "total_sessions": len(self._sessions),
            "active_sessions": sum(1 for s in self._sessions.values() if not s.get('ended_at')),
            "total_messages": sum(len(msgs) for msgs in self._messages.values()),
            "has_llm_router": self.llm_router is not None
        }
    
    # ============================================
    # SESSION MANAGEMENT
    # ============================================
    
    def start_session(
        self,
        project_id: int = 1,
        user_id: int = 1,
        title: Optional[str] = None,
        session_type: str = "general",
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Start a new conversation session.
        
        Args:
            project_id: ID of the project
            user_id: ID of the user
            title: Optional session title
            session_type: Type of session (general, learning, reflection, etc.)
            llm_provider: LLM provider to use
            llm_model: LLM model to use
            
        Returns:
            Session info dictionary or None if failed
        """
        if not self._initialized:
            return None
        
        session_id = self._next_session_id
        self._next_session_id += 1
        
        session = {
            "session_id": session_id,
            "session_number": session_id,
            "project_id": project_id,
            "user_id": user_id,
            "title": title or f"Session {session_id}",
            "session_type": session_type,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "message_count": 0,
            "has_summary": False,
            "has_reflection": False
        }
        
        self._sessions[session_id] = session
        self._messages[session_id] = []
        
        # Save to disk
        self._save_sessions_index()
        self._save_counters()
        
        return session
    
    def get_session_info(self, session_id: int) -> Optional[Dict]:
        """Get information about a session."""
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id].copy()
        session["message_count"] = len(self._messages.get(session_id, []))
        return session
    
    def list_sessions(
        self,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        List sessions with optional filters.
        
        Args:
            project_id: Filter by project
            user_id: Filter by user
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of session dictionaries
        """
        sessions = list(self._sessions.values())
        
        # Apply filters
        if project_id is not None:
            sessions = [s for s in sessions if s.get('project_id') == project_id]
        if user_id is not None:
            sessions = [s for s in sessions if s.get('user_id') == user_id]
        
        # Sort by started_at descending
        sessions.sort(key=lambda x: x.get('started_at', ''), reverse=True)
        
        # Apply pagination
        sessions = sessions[offset:offset + limit]
        
        # Add message counts
        for session in sessions:
            session_id = session['session_id']
            session['message_count'] = len(self._messages.get(session_id, []))
        
        return sessions
    
    def end_session(
        self,
        session_id: int,
        generate_summary: bool = True,
        generate_reflection: bool = True
    ) -> Optional[Dict]:
        """
        End a session and optionally generate summary and reflection.
        
        Args:
            session_id: ID of the session to end
            generate_summary: Whether to generate a summary
            generate_reflection: Whether to generate a 7 Values reflection
            
        Returns:
            Result dictionary with session info and generated content
        """
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        session['ended_at'] = datetime.now().isoformat()
        
        result = {
            "session_id": session_id,
            "ended_at": session['ended_at'],
            "message_count": len(self._messages.get(session_id, [])),
            "summary": None,
            "reflection": None
        }
        
        messages = self._messages.get(session_id, [])
        
        # Generate summary if requested
        if generate_summary and self.llm_router and messages:
            try:
                summary = self._generate_summary(session_id, messages)
                result["summary"] = summary
                session['has_summary'] = True
            except Exception as e:
                print(f"Error generating summary: {e}")
        
        # Generate reflection if requested
        if generate_reflection and self.llm_router and messages:
            try:
                reflection = self._generate_reflection(session_id, messages)
                result["reflection"] = reflection
                session['has_reflection'] = True
            except Exception as e:
                print(f"Error generating reflection: {e}")
        
        # Save session to disk
        self._save_session_to_disk(session_id)
        self._save_sessions_index()
        
        return result
    
    def _save_session_to_disk(self, session_id: int):
        """Save a complete session (messages, summary, reflection) to disk."""
        if session_id not in self._sessions:
            return
        
        session = self._sessions[session_id]
        messages = self._messages.get(session_id, [])
        
        # Create session directory
        session_dir = config.CONVERSATIONS_DIR / f"session_{session_id:03d}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save session metadata
        with open(session_dir / "session.json", 'w') as f:
            json.dump(session, f, indent=2, default=str)
        
        # Save messages
        with open(session_dir / "messages.json", 'w') as f:
            json.dump(messages, f, indent=2, default=str)
        
        # Save conversation as text
        with open(session_dir / "conversation.txt", 'w') as f:
            f.write(f"Session {session_id}: {session.get('title', 'Untitled')}\n")
            f.write(f"Started: {session.get('started_at')}\n")
            f.write(f"Ended: {session.get('ended_at')}\n")
            f.write("=" * 60 + "\n\n")
            for msg in messages:
                role = msg.get('role', 'unknown').upper()
                content = msg.get('content', '')
                f.write(f"{role}:\n{content}\n\n")
    
    # ============================================
    # MESSAGE MANAGEMENT
    # ============================================
    
    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        store_in_memory: bool = True
    ) -> Optional[Dict]:
        """
        Add a message to a session.
        
        Args:
            session_id: ID of the session
            role: Message role (user/assistant/system)
            content: Message content
            store_in_memory: Whether to store in vector memory
            
        Returns:
            Message info dictionary or None if failed
        """
        if session_id not in self._sessions:
            return None
        
        message_id = self._next_message_id
        self._next_message_id += 1
        
        message = {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "message_index": len(self._messages.get(session_id, [])),
            "created_at": datetime.now().isoformat()
        }
        
        if session_id not in self._messages:
            self._messages[session_id] = []
        
        self._messages[session_id].append(message)
        
        # Update session message count
        self._sessions[session_id]['message_count'] = len(self._messages[session_id])
        
        # Store in memory service if requested
        if store_in_memory:
            self._store_in_memory(session_id, message)
        
        self._save_counters()
        
        return message
    
    def get_conversation_history(
        self,
        session_id: int,
        limit: Optional[int] = None,
        format: str = "dict"
    ) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: ID of the session
            limit: Maximum number of messages
            format: 'dict' for full message dicts, 'simple' for role/content only
            
        Returns:
            List of messages
        """
        messages = self._messages.get(session_id, [])
        
        if limit:
            messages = messages[-limit:]
        
        if format == "simple" or format == "dict":
            return [{"role": m["role"], "content": m["content"]} for m in messages]
        
        return messages
    
    def _store_in_memory(self, session_id: int, message: Dict):
        """Store a message in the vector memory service."""
        try:
            from backend.services.memory_service import get_memory_service
            memory = get_memory_service()
            if memory and memory._initialized:
                # Only store substantial messages
                if len(message.get('content', '')) > 50:
                    memory.store(
                        content=message['content'],
                        metadata={
                            'type': 'message',
                            'session_id': session_id,
                            'role': message['role'],
                            'message_id': message['message_id']
                        }
                    )
        except Exception as e:
            # Non-critical - just log and continue
            print(f"Warning: Could not store message in memory: {e}")
    
    # ============================================
    # SUMMARY & REFLECTION
    # ============================================
    
    def _generate_summary(self, session_id: int, messages: List[Dict]) -> Dict:
        """Generate a summary for the session."""
        if not self.llm_router:
            return {"error": "No LLM router available"}
        
        # Format conversation
        conversation = "\n\n".join([
            f"{m.get('role', 'unknown').upper()}: {m.get('content', '')}"
            for m in messages
        ])
        
        prompt = f"""Please summarize this conversation session.

CONVERSATION:
{conversation}

Provide a summary with:
1. Main topics discussed
2. Key insights or conclusions
3. Any action items or next steps
4. Overall tone and quality of the exchange

Keep it concise but comprehensive."""

        try:
            response = self.llm_router.complete(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are summarizing a wisdom-focused conversation.",
                max_tokens=1000,
                temperature=0.7
            )
            
            summary = {
                "session_id": session_id,
                "summary_text": response,
                "key_topics": [],  # Could parse these from response
                "learning_outcomes": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Save summary to disk
            self._save_summary(session_id, summary)
            
            return summary
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_reflection(self, session_id: int, messages: List[Dict]) -> Dict:
        """Generate a 7 Values reflection for the session."""
        try:
            from backend.services.reflection_service import get_reflection_service
            reflection_service = get_reflection_service()
            
            if reflection_service:
                # Use the dedicated reflection service
                reflection_text, scores = reflection_service.generate_values_reflection(
                    session_id=session_id,
                    messages=[{"role": m["role"], "content": m["content"]} for m in messages]
                )
                
                reflection = {
                    "session_id": session_id,
                    "reflection_text": reflection_text,
                    "scores": scores,
                    "insights": [],
                    "growth_areas": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # Save reflection to disk
                self._save_reflection(session_id, reflection)
                
                return reflection
        except Exception as e:
            print(f"Reflection service error: {e}")
        
        # Fallback if reflection service not available
        if not self.llm_router:
            return {"error": "No LLM router or reflection service available"}
        
        return {"error": "Could not generate reflection"}
    
    def _save_summary(self, session_id: int, summary: Dict):
        """Save summary to disk."""
        session_dir = config.CONVERSATIONS_DIR / f"session_{session_id:03d}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        with open(session_dir / "summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        with open(session_dir / "summary.txt", 'w') as f:
            f.write(summary.get('summary_text', ''))
    
    def _save_reflection(self, session_id: int, reflection: Dict):
        """Save reflection to disk."""
        session_dir = config.CONVERSATIONS_DIR / f"session_{session_id:03d}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        with open(session_dir / "reflection.json", 'w') as f:
            json.dump(reflection, f, indent=2, default=str)
        
        with open(session_dir / "reflection.txt", 'w') as f:
            f.write(reflection.get('reflection_text', ''))
    
    def get_summary(self, session_id: int) -> Optional[Dict]:
        """Get the summary for a session."""
        session_dir = config.CONVERSATIONS_DIR / f"session_{session_id:03d}"
        summary_file = session_dir / "summary.json"
        
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_reflection(self, session_id: int) -> Optional[Dict]:
        """Get the reflection for a session."""
        session_dir = config.CONVERSATIONS_DIR / f"session_{session_id:03d}"
        reflection_file = session_dir / "reflection.json"
        
        if reflection_file.exists():
            with open(reflection_file, 'r') as f:
                return json.load(f)
        return None
    
    def generate_summary(self, session_id: int, force_regenerate: bool = False) -> Optional[Dict]:
        """Generate or retrieve session summary."""
        if not force_regenerate:
            existing = self.get_summary(session_id)
            if existing:
                return existing
        
        messages = self._messages.get(session_id, [])
        if not messages:
            return None
        
        return self._generate_summary(session_id, messages)
    
    def generate_reflection(self, session_id: int, force_regenerate: bool = False) -> Optional[Dict]:
        """Generate or retrieve session reflection."""
        if not force_regenerate:
            existing = self.get_reflection(session_id)
            if existing:
                return existing
        
        messages = self._messages.get(session_id, [])
        if not messages:
            return None
        
        return self._generate_reflection(session_id, messages)
    
    # Session repository compatibility (for sessions router)
    @property
    def session_repo(self):
        """Compatibility property for sessions router."""
        return self


# ============================================
# SINGLETON & FACTORY
# ============================================

def get_conversation_service() -> 'ConversationService':
    """Get the singleton ConversationService instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service


def initialize_conversation_service(llm_router=None) -> Optional['ConversationService']:
    """
    Initialize and return the ConversationService.
    
    Args:
        llm_router: LLMRouter instance for generating summaries/reflections
        
    Returns:
        ConversationService instance or None if initialization fails
    """
    global _conversation_service
    
    try:
        _conversation_service = ConversationService(llm_router=llm_router)
        if _conversation_service.initialize():
            return _conversation_service
        else:
            return None
    except Exception as e:
        print(f"Error initializing ConversationService: {e}")
        return None
