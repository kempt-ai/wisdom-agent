"""
Argument Builder Pydantic Models

Request/response schemas for:
- Parsed resources (structured extraction results)
- Extracted claims (with classification and verification)
- Extracted evidence (supporting claims)
- Argument modules (user-created structures)
- Module evidence links
- Parsing operations

Follows patterns from knowledge_models.py
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ClaimType(str, Enum):
    """Classification of claim types"""
    FACTUAL = "factual"           # Verifiable fact about the world
    INTERPRETIVE = "interpretive" # Analysis or interpretation of facts
    PRESCRIPTIVE = "prescriptive" # Recommendation or call to action


class VerificationStatus(str, Enum):
    """Status of claim verification"""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    PARTIALLY_VERIFIED = "partially_verified"


class EvidenceType(str, Enum):
    """Types of evidence"""
    STATISTIC = "statistic"
    QUOTE = "quote"
    CITATION = "citation"
    EXAMPLE = "example"
    DATA = "data"
    TESTIMONY = "testimony"


class ModuleType(str, Enum):
    """Types of argument modules"""
    THESIS = "thesis"           # Top-level claim
    ARGUMENT = "argument"       # Supporting argument
    COUNTER = "counter"         # Counter-argument
    REBUTTAL = "rebuttal"       # Response to counter-argument
    EVIDENCE = "evidence"       # Evidence container


class ModuleStatus(str, Enum):
    """Status of argument modules"""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EvidenceRelation(str, Enum):
    """Relationship between evidence and modules"""
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    CONTEXTUALIZES = "contextualizes"


# ============================================================================
# EVIDENCE MODELS
# ============================================================================

class EvidenceBase(BaseModel):
    """Base evidence model"""
    evidence_type: EvidenceType
    content: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_author: Optional[str] = None
    source_date: Optional[str] = None


class EvidenceCreate(EvidenceBase):
    """Create evidence (used in parsing results)"""
    pass


class Evidence(EvidenceBase):
    """Full evidence model with ID"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    claim_id: int
    position: int = 0
    created_at: datetime
    
    # Future-ready
    created_by: Optional[str] = None
    derived_from: Optional[Dict[str, Any]] = None
    license: str = "private"


# ============================================================================
# CLAIM MODELS
# ============================================================================

class ClaimBase(BaseModel):
    """Base claim model"""
    claim_text: str
    claim_type: ClaimType = ClaimType.FACTUAL
    context: Optional[str] = None
    source_quote: Optional[str] = None
    argument_title: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ClaimCreate(ClaimBase):
    """Create claim (used in parsing)"""
    evidence: List[EvidenceCreate] = []
    sub_claims: List["ClaimCreate"] = []  # Nested claims


class ClaimUpdate(BaseModel):
    """Update claim (for verification, etc.)"""
    claim_text: Optional[str] = None
    claim_type: Optional[ClaimType] = None
    verification_status: Optional[VerificationStatus] = None
    verification_sources: Optional[List[Dict[str, Any]]] = None
    verification_notes: Optional[str] = None


class ClaimSummary(BaseModel):
    """Brief claim summary for lists"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    claim_text: str
    claim_type: ClaimType
    argument_title: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    evidence_count: int = 0


class Claim(ClaimBase):
    """Full claim model with relationships"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    parsed_resource_id: int
    position_in_doc: Optional[int] = None
    parent_claim_id: Optional[int] = None
    
    # Verification
    verification_status: Optional[VerificationStatus] = None
    verification_sources: Optional[List[Dict[str, Any]]] = None
    verification_notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    
    # Related data
    evidence: List[Evidence] = []
    sub_claims: List["Claim"] = []
    
    created_at: datetime
    
    # Future-ready
    created_by: Optional[str] = None
    derived_from: Optional[Dict[str, Any]] = None
    license: str = "private"


# Enable forward reference for nested claims
ClaimCreate.model_rebuild()
Claim.model_rebuild()


# ============================================================================
# PARSED RESOURCE MODELS
# ============================================================================

class ParsedStructure(BaseModel):
    """
    The hierarchical structure extracted from a document.
    This is stored as JSON in structure_json field.
    """
    main_thesis: Optional[str] = None
    summary: Optional[str] = None
    arguments: List[Dict[str, Any]] = []  # Nested argument structure
    sources_cited: List[str] = []
    metadata: Dict[str, Any] = {}


class ParsedResourceBase(BaseModel):
    """Base parsed resource model"""
    main_thesis: Optional[str] = None
    summary: Optional[str] = None


class ParsedResourceCreate(ParsedResourceBase):
    """Created by the parsing service"""
    resource_id: int
    structure_json: Optional[Dict[str, Any]] = None
    sources_cited: List[str] = []
    parser_model: Optional[str] = None
    parser_version: Optional[str] = None
    parsing_cost_tokens: int = 0
    parsing_cost_dollars: float = 0.0


class ParsedResourceSummary(BaseModel):
    """Brief summary for lists"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    resource_id: int
    main_thesis: Optional[str] = None
    summary: Optional[str] = None
    parsed_at: datetime
    claim_count: int = 0


class ParsedResource(ParsedResourceBase):
    """Full parsed resource with claims"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    resource_id: int
    structure_json: Optional[Dict[str, Any]] = None
    
    parsed_at: datetime
    parser_model: Optional[str] = None
    parser_version: Optional[str] = None
    parse_level: str = "standard"  # ADDED: light, standard, or full
    parsing_cost_tokens: int = 0
    parsing_cost_dollars: float = 0.0
    
    sources_cited: List[str] = []
    claims: List[Claim] = []
    
    created_at: datetime
    updated_at: datetime
    
    # Future-ready
    created_by: Optional[str] = None
    derived_from: Optional[Dict[str, Any]] = None
    license: str = "private"


# ============================================================================
# ARGUMENT MODULE MODELS
# ============================================================================

class ModuleEvidenceLinkBase(BaseModel):
    """Base for linking evidence to modules"""
    claim_id: Optional[int] = None
    resource_id: Optional[int] = None
    custom_note: Optional[str] = None
    custom_source: Optional[str] = None
    relation_type: EvidenceRelation = EvidenceRelation.SUPPORTS
    annotation: Optional[str] = None


class ModuleEvidenceLinkCreate(ModuleEvidenceLinkBase):
    """Create evidence link"""
    pass


class ModuleEvidenceLink(ModuleEvidenceLinkBase):
    """Full evidence link with ID"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    module_id: int
    position: int = 0
    created_at: datetime
    
    # Expanded data (optionally populated)
    claim: Optional[ClaimSummary] = None


class ArgumentModuleBase(BaseModel):
    """Base argument module model"""
    title: str
    thesis: Optional[str] = None
    description: Optional[str] = None
    module_type: ModuleType = ModuleType.ARGUMENT
    tags: List[str] = []


class ArgumentModuleCreate(ArgumentModuleBase):
    """Create argument module"""
    parent_id: Optional[int] = None
    position: int = 0


class ArgumentModuleUpdate(BaseModel):
    """Update argument module"""
    title: Optional[str] = None
    thesis: Optional[str] = None
    description: Optional[str] = None
    module_type: Optional[ModuleType] = None
    status: Optional[ModuleStatus] = None
    parent_id: Optional[int] = None
    position: Optional[int] = None
    tags: Optional[List[str]] = None


class ArgumentModuleSummary(BaseModel):
    """Brief module summary for lists"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    thesis: Optional[str] = None
    module_type: ModuleType
    status: ModuleStatus
    child_count: int = 0
    evidence_count: int = 0


class ArgumentModule(ArgumentModuleBase):
    """Full argument module with relationships"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    parent_id: Optional[int] = None
    position: int = 0
    status: ModuleStatus = ModuleStatus.DRAFT
    
    # Related data
    children: List["ArgumentModule"] = []
    evidence_links: List[ModuleEvidenceLink] = []
    
    created_at: datetime
    updated_at: datetime
    
    # Future-ready
    created_by: Optional[str] = None
    derived_from: Optional[Dict[str, Any]] = None
    license: str = "private"


# Enable forward reference
ArgumentModule.model_rebuild()


# ============================================================================
# PARSING REQUEST/RESPONSE MODELS
# ============================================================================

class ParseRequest(BaseModel):
    """Request to parse a KB resource"""
    resource_id: int
    model_id: Optional[str] = None  # LLM to use (defaults to router recommendation)
    parse_level: str = "standard"   # light, standard, or full
    force_reparse: bool = False     # Re-parse even if already parsed
    extract_claims: bool = True     # Store individual claims in DB
    generate_embeddings: bool = False  # Generate vector embeddings for claims


class ParseEstimate(BaseModel):
    """Estimate for parsing a resource"""
    resource_id: int
    resource_name: str
    token_count: int
    estimated_parsing_tokens: int
    estimated_cost_dollars: float
    model_id: str
    already_parsed: bool = False


class ParseResult(BaseModel):
    """Result of parsing operation"""
    success: bool
    parsed_resource_id: Optional[int] = None
    resource_id: int
    main_thesis: Optional[str] = None
    summary: Optional[str] = None
    claim_count: int = 0
    evidence_count: int = 0
    
    # Cost tracking
    tokens_used: int = 0
    cost_dollars: float = 0.0
    model_used: Optional[str] = None
    
    # Timing
    parse_time_seconds: float = 0.0
    
    # Error info
    error_message: Optional[str] = None


class BulkParseRequest(BaseModel):
    """Request to parse multiple resources"""
    resource_ids: List[int]
    model_id: Optional[str] = None
    force_reparse: bool = False


class BulkParseResult(BaseModel):
    """Result of bulk parsing"""
    total_requested: int
    successful: int
    failed: int
    skipped: int  # Already parsed and force_reparse=False
    results: List[ParseResult]
    total_cost_dollars: float = 0.0


# ============================================================================
# VERIFICATION REQUEST/RESPONSE MODELS
# ============================================================================

class VerifyClaimsRequest(BaseModel):
    """Request to verify claims from a parsed resource"""
    parsed_resource_id: int
    claim_ids: Optional[List[int]] = None  # Specific claims, or all if None
    claim_types: Optional[List[ClaimType]] = None  # Filter by type
    model_id: Optional[str] = None


class VerifyClaimResult(BaseModel):
    """Result of verifying a single claim"""
    claim_id: int
    claim_text: str
    verification_status: VerificationStatus
    verification_sources: List[Dict[str, Any]] = []
    verification_notes: Optional[str] = None
    confidence: float = 0.0


class VerifyClaimsResult(BaseModel):
    """Result of bulk verification"""
    total_claims: int
    verified: int
    disputed: int
    unverified: int
    results: List[VerifyClaimResult]
    total_cost_dollars: float = 0.0


# ============================================================================
# SEARCH MODELS
# ============================================================================

class ClaimSearchQuery(BaseModel):
    """Search for claims across parsed resources"""
    query: str
    claim_types: Optional[List[ClaimType]] = None
    verification_status: Optional[List[VerificationStatus]] = None
    resource_ids: Optional[List[int]] = None  # Limit to specific resources
    collection_ids: Optional[List[int]] = None  # Limit to specific collections
    limit: int = Field(default=20, ge=1, le=100)
    use_semantic: bool = True  # Use vector similarity search


class ClaimSearchResult(BaseModel):
    """Single search result"""
    claim: ClaimSummary
    resource_id: int
    resource_name: str
    collection_id: Optional[int] = None
    collection_name: Optional[str] = None
    relevance_score: float = 0.0
    matched_context: Optional[str] = None


class ClaimSearchResponse(BaseModel):
    """Search response"""
    query: str
    total_results: int
    results: List[ClaimSearchResult]
    search_time_ms: float = 0.0


# ============================================================================
# EXPORT MODELS
# ============================================================================

class ExportFormat(str, Enum):
    """Supported export formats"""
    MARKDOWN = "markdown"
    JSON = "json"
    MEDIAWIKI = "mediawiki"
    HTML = "html"


class ExportRequest(BaseModel):
    """Request to export argument module"""
    module_id: int
    format: ExportFormat = ExportFormat.MARKDOWN
    include_evidence: bool = True
    include_sources: bool = True
    max_depth: Optional[int] = None  # How deep to traverse hierarchy


class ExportResult(BaseModel):
    """Export result"""
    module_id: int
    format: ExportFormat
    content: str
    filename: str
    

# ============================================================================
# OUTLINE VIEW MODEL (for frontend tree display)
# ============================================================================

class OutlineNode(BaseModel):
    """
    A node in the argument outline tree.
    Used for the collapsible tree view in the frontend.
    """
    id: str  # Unique ID for the node (e.g., "claim-123", "evidence-456")
    node_type: str  # "thesis", "argument", "claim", "evidence"
    title: str
    content: Optional[str] = None
    claim_type: Optional[ClaimType] = None
    verification_status: Optional[VerificationStatus] = None
    source_url: Optional[str] = None
    children: List["OutlineNode"] = []
    metadata: Dict[str, Any] = {}


OutlineNode.model_rebuild()


class ParsedResourceOutline(BaseModel):
    """
    Complete outline view of a parsed resource.
    Ready for rendering as a collapsible tree.
    """
    parsed_resource_id: int
    resource_id: int
    resource_name: str
    main_thesis: Optional[str] = None
    summary: Optional[str] = None
    outline: List[OutlineNode]
    
    # Stats
    total_claims: int = 0
    total_evidence: int = 0
    verified_claims: int = 0
    
    parsed_at: datetime
    sources_cited: List[str] = []
    
    # ADDED: Model info (for display in UI)
    parser_model: Optional[str] = None
    parse_level: Optional[str] = None
