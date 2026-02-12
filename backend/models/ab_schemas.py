"""
Investigation Builder (AB) Pydantic Schemas

Request/response models for the Investigation Builder feature.
Covers investigations, definitions, claims, evidence, credibility,
counterarguments, and changelog.

Follows patterns from knowledge_models.py and argument_models.py.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class InvestigationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ClaimStatus(str, Enum):
    ONGOING = "ongoing"
    RESOLVED = "resolved"
    HISTORICAL = "historical"
    SUPERSEDED = "superseded"


class SourceType(str, Enum):
    PRIMARY_SOURCE = "primary_source"
    NEWS = "news"
    ANALYSIS = "analysis"
    THINK_TANK = "think_tank"
    ACADEMIC = "academic"
    GOVERNMENT = "government"


class PublicationType(str, Enum):
    NEWS = "news"
    THINK_TANK = "think_tank"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    ADVOCACY = "advocacy"


class PieceStyle(str, Enum):
    REPORT = "report"
    OPINION = "opinion"
    NEWS = "news"
    ANALYSIS = "analysis"
    EDITORIAL = "editorial"


class PieceIntent(str, Enum):
    INFORM = "inform"
    PERSUADE = "persuade"
    DOCUMENT = "document"
    ADVOCATE = "advocate"


# ============================================================================
# INVESTIGATION MODELS
# ============================================================================

class InvestigationCreate(BaseModel):
    """Create a new investigation"""
    title: str = Field(..., min_length=1, max_length=255)
    overview_html: str = ""
    status: InvestigationStatus = InvestigationStatus.DRAFT


class InvestigationUpdate(BaseModel):
    """Update an investigation (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    overview_html: Optional[str] = None
    status: Optional[InvestigationStatus] = None


class InvestigationSummary(BaseModel):
    """Brief investigation for lists"""
    id: int
    title: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime
    definition_count: int = 0
    claim_count: int = 0


class Investigation(BaseModel):
    """Full investigation with all fields"""
    id: int
    title: str
    slug: str
    overview_html: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    version: int = 1
    definitions: List["Definition"] = []
    claims: List["ABClaim"] = []


# ============================================================================
# DEFINITION MODELS
# ============================================================================

class DefinitionCreate(BaseModel):
    """Create a definition"""
    term: str = Field(..., min_length=1, max_length=255)
    definition_html: str = ""
    see_also: List[str] = []


class DefinitionUpdate(BaseModel):
    """Update a definition (all fields optional)"""
    term: Optional[str] = Field(None, min_length=1, max_length=255)
    definition_html: Optional[str] = None
    see_also: Optional[List[str]] = None


class Definition(BaseModel):
    """Full definition"""
    id: int
    investigation_id: int
    term: str
    slug: str
    definition_html: str
    see_also: List[str] = []
    created_at: datetime
    updated_at: datetime


# ============================================================================
# CLAIM MODELS
# ============================================================================

class ABClaimCreate(BaseModel):
    """Create a claim within an investigation"""
    title: str = Field(..., min_length=1, max_length=500)
    claim_text: str
    exposition_html: Optional[str] = None
    status: ClaimStatus = ClaimStatus.ONGOING
    temporal_note: Optional[str] = None
    position: int = 0


class ABClaimUpdate(BaseModel):
    """Update a claim (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    claim_text: Optional[str] = None
    exposition_html: Optional[str] = None
    status: Optional[ClaimStatus] = None
    temporal_note: Optional[str] = None
    position: Optional[int] = None


class ABClaim(BaseModel):
    """Full claim with evidence and counterarguments"""
    id: int
    investigation_id: int
    title: str
    slug: str
    claim_text: str
    exposition_html: Optional[str] = None
    status: str = "ongoing"
    temporal_note: Optional[str] = None
    position: int = 0
    created_at: datetime
    updated_at: datetime
    evidence: List["ABEvidence"] = []
    counterarguments: List["Counterargument"] = []


# ============================================================================
# EVIDENCE MODELS
# ============================================================================

class ABEvidenceCreate(BaseModel):
    """Add evidence to a claim"""
    kb_resource_id: Optional[int] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    key_quote: Optional[str] = None
    key_point: Optional[str] = None
    position: int = 0
    source_anchor_type: Optional[str] = None
    source_anchor_data: Optional[Dict[str, Any]] = None


class ABEvidenceUpdate(BaseModel):
    """Update evidence (all fields optional)"""
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    key_quote: Optional[str] = None
    key_point: Optional[str] = None
    position: Optional[int] = None
    source_anchor_type: Optional[str] = None
    source_anchor_data: Optional[Dict[str, Any]] = None


class ABEvidence(BaseModel):
    """Full evidence item"""
    id: int
    claim_id: int
    kb_resource_id: Optional[int] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    key_quote: Optional[str] = None
    key_point: Optional[str] = None
    position: int = 0
    created_at: datetime
    source_anchor_type: Optional[str] = None
    source_anchor_data: Optional[Dict[str, Any]] = None


# ============================================================================
# CREDIBILITY MODELS
# ============================================================================

class SourceCredibilityCreate(BaseModel):
    """Create or update publication credibility"""
    publication_name: str = Field(..., min_length=1, max_length=255)
    publication_type: Optional[str] = None
    founded_year: Optional[int] = None
    affiliation: Optional[str] = None
    funding_sources: Optional[str] = None
    track_record: Optional[str] = None
    user_notes: Optional[str] = None


class SourceCredibility(BaseModel):
    """Full publication credibility"""
    id: int
    publication_name: str
    publication_type: Optional[str] = None
    founded_year: Optional[int] = None
    affiliation: Optional[str] = None
    funding_sources: Optional[str] = None
    track_record: Optional[str] = None
    ai_assessment_publication: Optional[str] = None
    ai_assessment_generated_at: Optional[datetime] = None
    ai_model_used: Optional[str] = None
    user_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EvidenceCredibilityCreate(BaseModel):
    """Set evidence-specific credibility"""
    source_credibility_id: Optional[int] = None
    author_names: Optional[str] = None
    author_roles: Optional[str] = None
    published_date: Optional[date] = None
    style: Optional[str] = None
    intent: Optional[str] = None
    primary_sources_cited: Optional[bool] = None
    primary_sources_description: Optional[str] = None
    user_notes: Optional[str] = None
    credibility_rating: Optional[int] = Field(None, ge=1, le=5)


class EvidenceCredibility(BaseModel):
    """Full evidence credibility"""
    id: int
    evidence_id: int
    source_credibility_id: Optional[int] = None
    author_names: Optional[str] = None
    author_roles: Optional[str] = None
    published_date: Optional[date] = None
    style: Optional[str] = None
    intent: Optional[str] = None
    primary_sources_cited: Optional[bool] = None
    primary_sources_description: Optional[str] = None
    ai_assessment_piece: Optional[str] = None
    ai_assessment_generated_at: Optional[datetime] = None
    user_notes: Optional[str] = None
    credibility_rating: Optional[int] = None
    created_at: datetime


# ============================================================================
# COUNTERARGUMENT MODELS
# ============================================================================

class CounterargumentCreate(BaseModel):
    """Add a counterargument to a claim"""
    counter_text: str
    rebuttal_text: Optional[str] = None
    position: int = 0


class CounterargumentUpdate(BaseModel):
    """Update a counterargument"""
    counter_text: Optional[str] = None
    rebuttal_text: Optional[str] = None
    position: Optional[int] = None


class Counterargument(BaseModel):
    """Full counterargument"""
    id: int
    claim_id: int
    counter_text: str
    rebuttal_text: Optional[str] = None
    position: int = 0
    created_at: datetime


# ============================================================================
# CHANGELOG MODELS
# ============================================================================

class ChangelogEntry(BaseModel):
    """A single changelog entry"""
    id: int
    investigation_id: int
    changed_at: datetime
    change_type: Optional[str] = None
    change_summary: Optional[str] = None
    changed_by: Optional[str] = None


# ============================================================================
# REBUILD FORWARD REFS
# ============================================================================

Investigation.model_rebuild()
ABClaim.model_rebuild()
