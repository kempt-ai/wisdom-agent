"""
Wisdom Agent - Fact Checker Pydantic Models

These models define the API request/response schemas for the fact checker.
They handle validation and serialization.

Author: Wisdom Agent Team
Date: 2025-12-18
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# ENUMS (mirror the database enums)
# ============================================================================

class SourceType(str, Enum):
    URL = "url"
    TEXT = "text"
    FILE = "file"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING_CLAIMS = "analyzing_claims"
    FACT_CHECKING = "fact_checking"
    LOGIC_ANALYSIS = "logic_analysis"
    WISDOM_EVALUATION = "wisdom_evaluation"
    COMPLETED = "completed"
    FAILED = "failed"


class FactualVerdict(str, Enum):
    ACCURATE = "accurate"
    MOSTLY_ACCURATE = "mostly_accurate"
    MIXED = "mixed"
    MOSTLY_INACCURATE = "mostly_inaccurate"
    INACCURATE = "inaccurate"
    UNVERIFIABLE = "unverifiable"


class WisdomVerdict(str, Enum):
    SERVES_WISDOM = "serves_wisdom"
    MOSTLY_WISE = "mostly_wise"
    MIXED = "mixed"
    MOSTLY_UNWISE = "mostly_unwise"
    SERVES_FOLLY = "serves_folly"
    UNCERTAIN = "uncertain"


class ClaimType(str, Enum):
    FACTUAL = "factual"
    LOGICAL = "logical"
    EMOTIONAL = "emotional"
    OPINION = "opinion"
    MIXED = "mixed"


class ClaimVerdict(str, Enum):
    TRUE = "true"
    MOSTLY_TRUE = "mostly_true"
    HALF_TRUE = "half_true"
    MOSTLY_FALSE = "mostly_false"
    FALSE = "false"
    UNVERIFIABLE = "unverifiable"
    NOT_A_CLAIM = "not_a_claim"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class ReviewCreateRequest(BaseModel):
    """Request to create a new fact check review."""
    source_type: SourceType
    source_url: Optional[str] = Field(None, description="URL if source_type is 'url'")
    source_content: Optional[str] = Field(None, description="Text content if source_type is 'text'")
    file_id: Optional[str] = Field(None, description="File ID if source_type is 'file'")
    session_id: Optional[int] = Field(None, description="Link to existing session (for mid-session fact checks)")
    project_id: Optional[int] = Field(None, description="Optional project association")
    title: Optional[str] = Field(None, description="Optional title (will be extracted if not provided)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "url",
                "source_url": "https://example.com/article",
                "project_id": None
            }
        }


class ReviewListRequest(BaseModel):
    """Request parameters for listing reviews."""
    project_id: Optional[int] = None
    session_id: Optional[int] = None
    status: Optional[ReviewStatus] = None
    factual_verdict: Optional[FactualVerdict] = None
    wisdom_verdict: Optional[WisdomVerdict] = None
    search: Optional[str] = Field(None, description="Search in title and URL")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


# ============================================================================
# RESPONSE MODELS - Nested Components
# ============================================================================

class SourceMetadataResponse(BaseModel):
    """Metadata about the source."""
    author: Optional[str] = None
    publication: Optional[str] = None
    publish_date: Optional[datetime] = None
    domain: Optional[str] = None
    credibility_score: Optional[float] = None
    credibility_notes: Optional[str] = None


class FactCheckResultResponse(BaseModel):
    """Result of checking a single claim."""
    verdict: ClaimVerdict
    confidence: float
    explanation: Optional[str] = None
    providers_used: Optional[List[str]] = None
    external_matches: Optional[List[Dict[str, Any]]] = None
    web_sources: Optional[List[Dict[str, Any]]] = None


class ExtractedClaimResponse(BaseModel):
    """A claim extracted from the content."""
    id: int
    claim_text: str
    claim_type: ClaimType
    source_location: Optional[str] = None
    source_quote: Optional[str] = None
    check_worthiness_score: Optional[float] = None
    fact_check_result: Optional[FactCheckResultResponse] = None


class FallacyFinding(BaseModel):
    """A logical fallacy found in the content."""
    name: str
    description: str
    quote: Optional[str] = None
    confidence: float


class LogicAnalysisResponse(BaseModel):
    """Logic analysis results."""
    main_conclusion: Optional[str] = None
    premises: Optional[List[str]] = None
    unstated_assumptions: Optional[List[str]] = None
    fallacies_found: Optional[List[FallacyFinding]] = None
    validity_assessment: Optional[str] = None
    soundness_assessment: Optional[str] = None
    alternative_interpretations: Optional[List[str]] = None
    logic_quality_score: Optional[float] = None
    confidence: Optional[float] = None


class ValueAssessment(BaseModel):
    """Assessment of a single Universal Value."""
    score: int = Field(..., ge=1, le=5)
    notes: str


class WisdomEvaluationResponse(BaseModel):
    """Wisdom evaluation results."""
    # 7 Universal Values
    awareness: Optional[ValueAssessment] = None
    honesty: Optional[ValueAssessment] = None
    accuracy: Optional[ValueAssessment] = None
    competence: Optional[ValueAssessment] = None
    compassion: Optional[ValueAssessment] = None
    loving_kindness: Optional[ValueAssessment] = None
    joyful_sharing: Optional[ValueAssessment] = None
    
    # Something Deeperism
    something_deeperism_assessment: Optional[str] = None
    claims_unwarranted_certainty: Optional[bool] = None
    treats_complex_truths_dogmatically: Optional[bool] = None
    acknowledges_limits_of_understanding: Optional[bool] = None
    serves_pure_love: Optional[bool] = None
    fosters_or_squelches_sd: Optional[str] = None  # "fosters", "squelches", "neutral"
    
    # Overall wisdom assessment
    overall_wisdom_score: Optional[float] = None
    serves_wisdom_or_folly: Optional[WisdomVerdict] = None
    final_reflection: Optional[str] = None
    
    # The three questions
    is_it_true: Optional[str] = None
    is_it_reasonable: Optional[str] = None
    does_it_serve_wisdom: Optional[str] = None
    three_questions_interaction: Optional[str] = None


# ============================================================================
# RESPONSE MODELS - Main
# ============================================================================

class ReviewSummaryResponse(BaseModel):
    """Summary view of a review (for lists)."""
    id: int
    title: Optional[str]
    source_type: SourceType
    source_url: Optional[str]
    status: ReviewStatus
    quick_summary: Optional[str]
    overall_factual_verdict: Optional[FactualVerdict]
    overall_wisdom_verdict: Optional[WisdomVerdict]
    confidence_score: Optional[float]
    session_id: int
    project_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ReviewDetailResponse(BaseModel):
    """Full detail view of a review."""
    id: int
    title: Optional[str]
    source_type: SourceType
    source_url: Optional[str]
    source_content: str
    status: ReviewStatus
    error_message: Optional[str]
    
    # Summary results
    quick_summary: Optional[str]
    overall_factual_verdict: Optional[FactualVerdict]
    overall_wisdom_verdict: Optional[WisdomVerdict]
    confidence_score: Optional[float]
    
    # Session and project info
    session_id: int
    project_id: Optional[int]
    user_id: int
    
    # Nested analysis results
    source_metadata: Optional[SourceMetadataResponse]
    claims: List[ExtractedClaimResponse]
    logic_analysis: Optional[LogicAnalysisResponse]
    wisdom_evaluation: Optional[WisdomEvaluationResponse]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""
    items: List[ReviewSummaryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ReviewStatusResponse(BaseModel):
    """Current status of a review (for polling during analysis)."""
    id: int
    status: ReviewStatus
    error_message: Optional[str]
    progress_message: Optional[str] = None
    completed_at: Optional[datetime]


# ============================================================================
# SESSION LINK MODELS
# ============================================================================

class SessionLinkRequest(BaseModel):
    """Request to link a review to a session."""
    session_id: int
    link_context: Optional[str] = Field(None, description="Why this review relates to the session")


class SessionLinkResponse(BaseModel):
    """Response after linking review to session."""
    review_id: int
    session_id: int
    linked_at: datetime
    link_context: Optional[str]
