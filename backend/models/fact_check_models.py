"""
Wisdom Agent - Fact & Logic Checker Database Models

SQLAlchemy models for storing fact checks, claims, analyses, and evaluations.
These integrate with the existing Wisdom Agent database schema.

Author: Wisdom Agent Team
Date: 2025-12-18
Updated: 2025-12-30 - Fixed enum handling for PostgreSQL compatibility
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, 
    ForeignKey, JSON, Enum, Index
)
from sqlalchemy.orm import relationship

# Import from existing database setup
# This assumes your project has backend/database/models.py with Base defined
from backend.database.models import Base


# ============================================================================
# ENUMS
# ============================================================================

class SourceType(str, enum.Enum):
    """Type of content source."""
    URL = "url"
    TEXT = "text"
    FILE = "file"


class ReviewStatus(str, enum.Enum):
    """Status of a fact check review."""
    PENDING = "pending"
    EXTRACTING = "extracting"      # Extracting content
    ANALYZING_CLAIMS = "analyzing_claims"
    FACT_CHECKING = "fact_checking"
    LOGIC_ANALYSIS = "logic_analysis"
    WISDOM_EVALUATION = "wisdom_evaluation"
    COMPLETED = "completed"
    FAILED = "failed"


class FactualVerdict(str, enum.Enum):
    """Verdict for factual accuracy."""
    ACCURATE = "accurate"
    MOSTLY_ACCURATE = "mostly_accurate"
    MIXED = "mixed"
    MOSTLY_INACCURATE = "mostly_inaccurate"
    INACCURATE = "inaccurate"
    UNVERIFIABLE = "unverifiable"


class WisdomVerdict(str, enum.Enum):
    """Verdict for wisdom evaluation."""
    SERVES_WISDOM = "serves_wisdom"
    MOSTLY_WISE = "mostly_wise"
    MIXED = "mixed"
    MOSTLY_UNWISE = "mostly_unwise"
    SERVES_FOLLY = "serves_folly"
    UNCERTAIN = "uncertain"


class ClaimType(str, enum.Enum):
    """Type of claim extracted from content."""
    FACTUAL = "factual"           # Verifiable fact
    LOGICAL = "logical"           # Logical premise or conclusion
    EMOTIONAL = "emotional"       # Emotional appeal
    OPINION = "opinion"           # Subjective opinion
    MIXED = "mixed"


class ClaimVerdict(str, enum.Enum):
    """Verdict for individual claim verification."""
    TRUE = "true"
    MOSTLY_TRUE = "mostly_true"
    HALF_TRUE = "half_true"
    MOSTLY_FALSE = "mostly_false"
    FALSE = "false"
    UNVERIFIABLE = "unverifiable"
    NOT_A_CLAIM = "not_a_claim"   # Opinion, not checkable


# ============================================================================
# MAIN MODELS
# ============================================================================

class ContentReview(Base):
    """
    Main fact check review record.
    
    Each review is associated with a session (following the Wisdom Agent pattern
    where all interactions are sessions). Standalone fact checks create their
    own session; mid-session fact checks belong to the parent session.
    """
    __tablename__ = "content_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to session (every fact check belongs to a session)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    
    # Optional project association
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    
    # User who created this review
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Content identification
    title = Column(String(500), nullable=True)  # Extracted or user-provided
    # Using native_enum=False stores as VARCHAR, avoiding PostgreSQL enum issues
    source_type = Column(Enum(SourceType, native_enum=False), nullable=False)
    source_url = Column(String(2000), nullable=True)
    source_content = Column(Text, nullable=False)  # Original content
    
    # Processing status
    status = Column(Enum(ReviewStatus, native_enum=False), default=ReviewStatus.PENDING)
    error_message = Column(Text, nullable=True)  # If status is FAILED
    
    # Summary results
    quick_summary = Column(Text, nullable=True)  # 2-3 sentence overview
    overall_factual_verdict = Column(Enum(FactualVerdict, native_enum=False), nullable=True)
    overall_wisdom_verdict = Column(Enum(WisdomVerdict, native_enum=False), nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="content_reviews")
    project = relationship("Project", back_populates="content_reviews")
    user = relationship("User", back_populates="content_reviews")
    
    # Child relationships
    claims = relationship("ExtractedClaim", back_populates="review", cascade="all, delete-orphan")
    source_metadata = relationship("SourceMetadata", back_populates="review", uselist=False, cascade="all, delete-orphan")
    logic_analysis = relationship("LogicAnalysis", back_populates="review", uselist=False, cascade="all, delete-orphan")
    wisdom_evaluation = relationship("WisdomEvaluation", back_populates="review", uselist=False, cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_review_session', 'session_id'),
        Index('idx_review_user', 'user_id'),
        Index('idx_review_status', 'status'),
        Index('idx_review_created', 'created_at'),
    )


class SourceMetadata(Base):
    """
    Metadata about the source of reviewed content.
    Extracted during content analysis.
    """
    __tablename__ = "source_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("content_reviews.id"), nullable=False)
    
    # Source information
    author = Column(String(500), nullable=True)
    publication = Column(String(500), nullable=True)
    publish_date = Column(DateTime, nullable=True)
    domain = Column(String(255), nullable=True)
    
    # Credibility assessment
    credibility_score = Column(Float, nullable=True)  # 0.0 to 1.0
    credibility_notes = Column(Text, nullable=True)
    
    # Additional metadata (flexible)
    extra_data = Column(JSON, nullable=True)
    
    # Relationship
    review = relationship("ContentReview", back_populates="source_metadata")


class ExtractedClaim(Base):
    """
    Individual claim extracted from reviewed content.
    Each claim can be fact-checked independently.
    """
    __tablename__ = "extracted_claims"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("content_reviews.id"), nullable=False)
    
    # Claim content
    claim_text = Column(Text, nullable=False)
    claim_type = Column(Enum(ClaimType, native_enum=False), nullable=False)
    
    # Location in source
    source_location = Column(String(100), nullable=True)  # e.g., "paragraph 3"
    source_quote = Column(Text, nullable=True)  # Original quote containing claim
    
    # Check-worthiness (from triage)
    check_worthiness_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # For future semantic search
    # embedding = Column(Vector(384), nullable=True)  # Enable when needed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    review = relationship("ContentReview", back_populates="claims")
    fact_check_result = relationship("FactCheckResult", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    
    # Index
    __table_args__ = (
        Index('idx_claim_review', 'review_id'),
    )


class FactCheckResult(Base):
    """
    Result of fact-checking an individual claim.
    Stores verdicts from various providers.
    """
    __tablename__ = "fact_check_results"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("extracted_claims.id"), nullable=False)
    
    # Verdict
    verdict = Column(Enum(ClaimVerdict, native_enum=False), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    explanation = Column(Text, nullable=True)
    
    # Provider results (which services contributed)
    providers_used = Column(JSON, nullable=True)  # List of provider names
    
    # External fact-check matches (from Google Fact Check API, ClaimBuster, etc.)
    external_matches = Column(JSON, nullable=True)  # [{source, verdict, url}, ...]
    
    # Web search evidence
    web_sources = Column(JSON, nullable=True)  # [{title, url, snippet}, ...]
    
    # LLM analysis
    llm_analysis = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    claim = relationship("ExtractedClaim", back_populates="fact_check_result")


class LogicAnalysis(Base):
    """
    Logical analysis of the entire reviewed content.
    Covers argument structure, fallacies, validity assessment.
    """
    __tablename__ = "logic_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("content_reviews.id"), nullable=False)
    
    # Argument structure
    main_conclusion = Column(Text, nullable=True)
    premises = Column(JSON, nullable=True)  # List of premise statements
    unstated_assumptions = Column(JSON, nullable=True)  # List of assumptions
    
    # Fallacies detected
    fallacies_found = Column(JSON, nullable=True)  # [{name, description, quote, confidence}, ...]
    
    # Validity assessment
    validity_assessment = Column(Text, nullable=True)  # Does conclusion follow from premises?
    soundness_assessment = Column(Text, nullable=True)  # Are premises true AND logic valid?
    
    # Alternative interpretations
    alternative_interpretations = Column(JSON, nullable=True)
    
    # Overall assessment
    logic_quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    confidence = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    review = relationship("ContentReview", back_populates="logic_analysis")


class WisdomEvaluation(Base):
    """
    Wisdom evaluation against 7 Universal Values and Something Deeperism.
    This is what makes the Wisdom Agent's analysis unique.
    """
    __tablename__ = "wisdom_evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("content_reviews.id"), nullable=False)
    
    # 7 Universal Values assessments (1-5 scale)
    awareness_score = Column(Integer, nullable=True)
    awareness_notes = Column(Text, nullable=True)
    
    honesty_score = Column(Integer, nullable=True)
    honesty_notes = Column(Text, nullable=True)
    
    accuracy_score = Column(Integer, nullable=True)
    accuracy_notes = Column(Text, nullable=True)
    
    competence_score = Column(Integer, nullable=True)
    competence_notes = Column(Text, nullable=True)
    
    compassion_score = Column(Integer, nullable=True)
    compassion_notes = Column(Text, nullable=True)
    
    loving_kindness_score = Column(Integer, nullable=True)
    loving_kindness_notes = Column(Text, nullable=True)
    
    joyful_sharing_score = Column(Integer, nullable=True)
    joyful_sharing_notes = Column(Text, nullable=True)
    
    # Something Deeperism assessment
    something_deeperism_assessment = Column(Text, nullable=True)
    claims_unwarranted_certainty = Column(Boolean, nullable=True)
    treats_complex_truths_dogmatically = Column(Boolean, nullable=True)
    acknowledges_limits_of_understanding = Column(Boolean, nullable=True)
    serves_pure_love = Column(Boolean, nullable=True)
    fosters_or_squelches_sd = Column(String(50), nullable=True)  # "fosters", "squelches", "neutral"
    
    # Final wisdom verdict
    overall_wisdom_score = Column(Float, nullable=True)  # 0.0 to 1.0
    serves_wisdom_or_folly = Column(Enum(WisdomVerdict, native_enum=False), nullable=True)
    final_reflection = Column(Text, nullable=True)
    
    # The three questions
    is_it_true_assessment = Column(Text, nullable=True)
    is_it_reasonable_assessment = Column(Text, nullable=True)
    does_it_serve_wisdom_assessment = Column(Text, nullable=True)
    three_questions_interaction = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    review = relationship("ContentReview", back_populates="wisdom_evaluation")


# ============================================================================
# RELATIONSHIP ADDITIONS TO EXISTING MODELS
# ============================================================================
# 
# Add these relationships to your existing models in backend/database/models.py:
#
# In Session class:
#     content_reviews = relationship("ContentReview", back_populates="session")
#
# In Project class:
#     content_reviews = relationship("ContentReview", back_populates="project")
#
# In User class:
#     content_reviews = relationship("ContentReview", back_populates="user")
#
# ============================================================================
