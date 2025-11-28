"""
Wisdom Agent - Database Models

SQLAlchemy models for PostgreSQL + pgvector.
SQLite fallback support for testing without vector operations.

Schema Design:
- Core: users, organizations, projects, sessions, conversations
- Memory: memories with vector embeddings
- Future: claims, verifications, evidence (for fact-checking)
- Future: evolution tracking (for safe AI self-improvement)
"""

from datetime import datetime
from typing import Optional
import os
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    ForeignKey, JSON, Enum as SQLEnum, Index, CheckConstraint, LargeBinary
)
from sqlalchemy.orm import relationship
import enum

# Conditional import for pgvector
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    # Use LargeBinary as placeholder for vectors in SQLite
    def Vector(dim):
        return LargeBinary
else:
    from pgvector.sqlalchemy import Vector

from backend.database.connection import Base


# ===========================================
# Enums
# ===========================================

class VisibilityLevel(str, enum.Enum):
    """Visibility levels for multi-user support."""
    PRIVATE = "private"          # Only owner can see
    ORGANIZATION = "organization"  # Organization members can see
    PUBLIC = "public"            # Everyone can see


class SessionType(str, enum.Enum):
    """Types of learning/conversation sessions."""
    GENERAL = "general"
    LANGUAGE_LEARNING = "language_learning"
    TECHNICAL_LEARNING = "technical_learning"
    CREATIVE_WRITING = "creative_writing"
    REFLECTION = "reflection"
    PHILOSOPHY = "philosophy"


class ClaimStatus(str, enum.Enum):
    """Status of fact-checking claims."""
    PENDING = "pending"
    VERIFIED = "verified"
    REFUTED = "refuted"
    DISPUTED = "disputed"
    UNVERIFIABLE = "unverifiable"


# ===========================================
# Core Models - Users & Organizations
# ===========================================

class User(Base):
    """User accounts (multi-user ready)."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # User settings
    preferred_llm_provider = Column(String(50), default="anthropic")
    preferred_model = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    organizations = relationship("Organization", back_populates="owner")
    projects = relationship("Project", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    memories = relationship("Memory", back_populates="user")


class Organization(Base):
    """Organizations for multi-user collaboration (future)."""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Organization settings
    philosophy_overlay = Column(Text)  # Custom philosophy for this org
    default_visibility = Column(SQLEnum(VisibilityLevel), default=VisibilityLevel.ORGANIZATION)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="organizations")
    projects = relationship("Project", back_populates="organization")


# ===========================================
# Core Models - Projects & Sessions
# ===========================================

class Project(Base):
    """Learning projects (e.g., 'improve_my_spanish')."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # Project type and settings
    session_type = Column(SQLEnum(SessionType), default=SessionType.GENERAL)
    philosophy_overlay = Column(Text)  # Optional project-specific philosophy
    
    # Learning settings (for pedagogy)
    subject = Column(String(255))
    current_level = Column(String(100))
    learning_goal = Column(Text)
    time_commitment = Column(String(100))
    learning_plan = Column(JSON)  # Structured learning plan
    meta_data = Column(JSON)  # Flexible metadata (journal_entries, progress, etc.)
    
    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    visibility = Column(SQLEnum(VisibilityLevel), default=VisibilityLevel.PRIVATE)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_user_project_slug', 'user_id', 'slug', unique=True),
    )


class Session(Base):
    """Conversation sessions within a project."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_number = Column(Integer, nullable=False)  # e.g., session_007
    
    # Session metadata
    title = Column(String(255))
    session_type = Column(SQLEnum(SessionType), default=SessionType.GENERAL)
    
    # LLM settings used
    llm_provider = Column(String(50))
    llm_model = Column(String(100))
    
    # Ownership
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="sessions")
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    summary = relationship("SessionSummary", back_populates="session", uselist=False, cascade="all, delete-orphan")
    reflection = relationship("SessionReflection", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_project_session_number', 'project_id', 'session_number', unique=True),
    )


class Message(Base):
    """Individual messages in a conversation."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    
    # Message content
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    
    # Metadata
    message_index = Column(Integer, nullable=False)  # Order within session
    token_count = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    
    __table_args__ = (
        Index('idx_session_message_index', 'session_id', 'message_index', unique=True),
    )


class SessionSummary(Base):
    """AI-generated summaries of sessions."""
    __tablename__ = "session_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    
    # Summary content
    summary_text = Column(Text, nullable=False)
    key_topics = Column(JSON)  # List of main topics discussed
    learning_outcomes = Column(JSON)  # What the user learned/accomplished
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="summary")


class SessionReflection(Base):
    """Philosophical reflections and 7 Universal Values scoring."""
    __tablename__ = "session_reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    
    # Reflection content
    reflection_text = Column(Text, nullable=False)
    
    # 7 Universal Values scores (0-10)
    awareness_score = Column(Float, CheckConstraint('awareness_score >= 0 AND awareness_score <= 10'))
    honesty_score = Column(Float, CheckConstraint('honesty_score >= 0 AND honesty_score <= 10'))
    accuracy_score = Column(Float, CheckConstraint('accuracy_score >= 0 AND accuracy_score <= 10'))
    competence_score = Column(Float, CheckConstraint('competence_score >= 0 AND competence_score <= 10'))
    compassion_score = Column(Float, CheckConstraint('compassion_score >= 0 AND compassion_score <= 10'))
    loving_kindness_score = Column(Float, CheckConstraint('loving_kindness_score >= 0 AND loving_kindness_score <= 10'))
    joyful_sharing_score = Column(Float, CheckConstraint('joyful_sharing_score >= 0 AND joyful_sharing_score <= 10'))
    
    # Overall wisdom score
    overall_score = Column(Float, CheckConstraint('overall_score >= 0 AND overall_score <= 10'))
    
    # Additional reflection content
    insights = Column(JSON)  # List of key insights
    growth_areas = Column(JSON)  # List of identified growth areas
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="reflection")


# ===========================================
# Memory System - Vector Embeddings
# ===========================================

class Memory(Base):
    """Vector memories for semantic search (replaces ChromaDB)."""
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Memory content
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384) if not USE_SQLITE else LargeBinary, nullable=True)  # all-MiniLM-L6-v2 dimension
    
    # Metadata
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Additional metadata (flexible JSON)
    meta_data = Column(JSON)  # tags, categories, custom fields
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    # Vector similarity search index (PostgreSQL only)
    if not USE_SQLITE:
        __table_args__ = (
            Index('idx_memory_embedding', 'embedding', postgresql_using='ivfflat', 
                  postgresql_ops={'embedding': 'vector_cosine_ops'}),
        )


# ===========================================
# Future Models - Democracy & Fact-Checking
# ===========================================

class Claim(Base):
    """Claims for fact-checking (future Week 3+)."""
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Claim content
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String(100))  # factual, opinion, prediction, etc.
    
    # Source information
    source_url = Column(String(500))
    source_title = Column(String(500))
    source_date = Column(DateTime)
    author = Column(String(255))
    
    # Verification status
    status = Column(SQLEnum(ClaimStatus), default=ClaimStatus.PENDING)
    confidence_score = Column(Float, CheckConstraint('confidence_score >= 0 AND confidence_score <= 1'))
    
    # Ownership & visibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visibility = Column(SQLEnum(VisibilityLevel), default=VisibilityLevel.PRIVATE)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verifications = relationship("Verification", back_populates="claim", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="claim", cascade="all, delete-orphan")


class Verification(Base):
    """Verification results from fact-checking APIs (future)."""
    __tablename__ = "verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    
    # Verification details
    verdict = Column(String(100))  # true, false, mixed, unverifiable
    explanation = Column(Text)
    confidence = Column(Float, CheckConstraint('confidence >= 0 AND confidence <= 1'))
    
    # Source
    verification_source = Column(String(255))  # e.g., "Google Fact Check API"
    source_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    claim = relationship("Claim", back_populates="verifications")


class Evidence(Base):
    """Supporting or refuting evidence for claims (future)."""
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    
    # Evidence content
    evidence_text = Column(Text, nullable=False)
    evidence_type = Column(String(100))  # supporting, refuting, contextual
    
    # Source
    source_url = Column(String(500))
    source_title = Column(String(500))
    source_date = Column(DateTime)
    credibility_score = Column(Float, CheckConstraint('credibility_score >= 0 AND credibility_score <= 1'))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    claim = relationship("Claim", back_populates="evidence_items")


class LogicalAnalysis(Base):
    """Logical analysis of arguments (media literacy, future)."""
    __tablename__ = "logical_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Analysis content
    argument_text = Column(Text, nullable=False)
    logical_structure = Column(JSON)  # premises, conclusions, fallacies
    fallacies_identified = Column(JSON)  # list of logical fallacies
    reasoning_quality_score = Column(Float, CheckConstraint('reasoning_quality_score >= 0 AND reasoning_quality_score <= 10'))
    
    # Metadata
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# ===========================================
# Future Models - AI Evolution Tracking
# ===========================================

class ReasoningTrace(Base):
    """Audit trail of AI reasoning (for safe evolution, future)."""
    __tablename__ = "reasoning_traces"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Trace content
    input_prompt = Column(Text, nullable=False)
    reasoning_steps = Column(JSON, nullable=False)  # step-by-step reasoning
    final_output = Column(Text, nullable=False)
    
    # Metadata
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    model_version = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class EvolutionProposal(Base):
    """Proposals for AI system improvements (safe evolution, future)."""
    __tablename__ = "evolution_proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Proposal content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    proposed_change = Column(JSON, nullable=False)  # structured change description
    
    # Rationale
    rationale = Column(Text, nullable=False)
    wisdom_alignment_analysis = Column(Text)  # how it aligns with 7 values
    potential_risks = Column(JSON)  # identified risks
    
    # Status
    status = Column(String(50), default="proposed")  # proposed, testing, approved, rejected, implemented
    
    # Voting/consensus (future multi-user)
    votes_for = Column(Integer, default=0)
    votes_against = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvolutionLog(Base):
    """Log of actual system changes (safe evolution, future)."""
    __tablename__ = "evolution_log"
    
    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("evolution_proposals.id"), nullable=True)
    
    # Change details
    change_type = Column(String(100), nullable=False)  # philosophy_update, feature_addition, etc.
    change_description = Column(Text, nullable=False)
    previous_state = Column(JSON)  # state before change
    new_state = Column(JSON)  # state after change
    
    # Reversibility
    is_reversible = Column(Boolean, default=True)
    rollback_instructions = Column(JSON)
    
    # Outcome tracking
    success_metrics = Column(JSON)  # how to measure if change was good
    actual_outcomes = Column(JSON)  # measured results
    
    # Timestamps
    implemented_at = Column(DateTime, default=datetime.utcnow)
    reverted_at = Column(DateTime, nullable=True)
