"""
Knowledge Base Pydantic Models

Defines data structures for:
- Collections (organizing resources by topic)
- Resources (documents, books, articles, learning modules)
- Indexes (summaries, embeddings, structured data)
- Character Profiles (extracted from fiction)
- Author Voices (writing style profiles)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================

class CollectionType(str, Enum):
    """Types of knowledge collections"""
    RESEARCH = "research"
    FICTION = "fiction"
    LEARNING = "learning"
    GENERAL = "general"


class ResourceType(str, Enum):
    """Types of resources that can be indexed"""
    DOCUMENT = "document"
    FICTION_BOOK = "fiction_book"
    NONFICTION_BOOK = "nonfiction_book"
    ARTICLE = "article"
    LEARNING_MODULE = "learning_module"


class SourceType(str, Enum):
    """How the resource was added"""
    UPLOAD = "upload"
    URL = "url"
    TEXT = "text"
    API = "api"


class IndexLevel(str, Enum):
    """
    Indexing depth options:
    - NONE: Just store, no AI processing
    - LIGHT: Summary + key passages (~5% of content tokens)
    - STANDARD: Structured breakdown + searchable chunks (~20% tokens)  
    - FULL: Complete semantic embedding + deep analysis (~120% tokens)
    """
    NONE = "none"
    LIGHT = "light"
    STANDARD = "standard"
    FULL = "full"


class IndexStatus(str, Enum):
    """Status of resource indexing"""
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class Visibility(str, Enum):
    """Resource/collection visibility"""
    PRIVATE = "private"
    UNLISTED = "unlisted"  # Accessible by link
    PUBLIC = "public"      # Searchable by community


class IndexType(str, Enum):
    """Types of indexes created for resources"""
    SUMMARY = "summary"
    STRUCTURED = "structured"
    VECTOR = "vector"
    CHARACTERS = "characters"
    CHAPTERS = "chapters"
    THEMES = "themes"
    QUOTES = "quotes"


class CharacterRole(str, Enum):
    """Character roles in fiction"""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    NARRATOR = "narrator"


# ============================================================================
# COLLECTION MODELS
# ============================================================================

class CollectionBase(BaseModel):
    """Base fields for a knowledge collection"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    collection_type: CollectionType = CollectionType.GENERAL
    visibility: Visibility = Visibility.PRIVATE
    tags: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)


class CollectionCreate(CollectionBase):
    """Creating a new collection"""
    project_id: Optional[int] = None


class CollectionUpdate(BaseModel):
    """Updating an existing collection (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    collection_type: Optional[CollectionType] = None
    visibility: Optional[Visibility] = None
    tags: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None


class Collection(CollectionBase):
    """Full collection with database fields"""
    id: int
    user_id: int
    project_id: Optional[int] = None
    resource_count: int = 0
    total_tokens: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionSummary(BaseModel):
    """Lightweight collection info for lists"""
    id: int
    name: str
    collection_type: CollectionType
    resource_count: int
    updated_at: datetime


# ============================================================================
# RESOURCE MODELS
# ============================================================================

class ResourceBase(BaseModel):
    """Base fields for a knowledge resource"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    resource_type: ResourceType = ResourceType.DOCUMENT
    visibility: Visibility = Visibility.PRIVATE
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResourceCreate(ResourceBase):
    """Creating a new resource"""
    source_type: SourceType
    source_url: Optional[str] = None
    content: Optional[str] = None  # For text/upload content


class ResourceUpdate(BaseModel):
    """Updating a resource (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    visibility: Optional[Visibility] = None
    metadata: Optional[Dict[str, Any]] = None


class Resource(ResourceBase):
    """Full resource with database fields"""
    id: int
    collection_id: int
    user_id: int
    source_type: SourceType
    source_url: Optional[str] = None
    token_count: int = 0
    index_level: IndexLevel = IndexLevel.NONE
    index_status: IndexStatus = IndexStatus.PENDING
    index_cost_tokens: int = 0
    index_cost_dollars: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceSummary(BaseModel):
    """Lightweight resource info for lists"""
    id: int
    name: str
    resource_type: ResourceType
    token_count: int
    index_level: IndexLevel
    index_status: IndexStatus
    updated_at: datetime


# ============================================================================
# INDEXING MODELS
# ============================================================================

class IndexEstimate(BaseModel):
    """Cost estimate for indexing a resource"""
    resource_id: int
    resource_name: str
    token_count: int
    index_level: IndexLevel
    model_id: str
    model_name: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    budget_remaining: float
    can_afford: bool
    warning_message: Optional[str] = None
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)


class IndexRequest(BaseModel):
    """Request to index a resource"""
    index_level: IndexLevel
    model_id: Optional[str] = None  # Use default if not specified
    confirmed: bool = False  # Must confirm cost


class IndexResult(BaseModel):
    """Result of indexing operation"""
    resource_id: int
    index_level: IndexLevel
    status: IndexStatus
    actual_cost: float
    input_tokens: int
    output_tokens: int
    indexes_created: List[IndexType]
    error_message: Optional[str] = None


class ResourceIndex(BaseModel):
    """Index data for a resource"""
    id: int
    resource_id: int
    index_type: IndexType
    content: Optional[Dict[str, Any]] = None
    text_content: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CHARACTER MODELS (for fiction)
# ============================================================================

class VoiceProfile(BaseModel):
    """How a character speaks"""
    vocabulary_level: str = "standard"  # formal, casual, archaic, etc.
    speech_patterns: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    tone: str = "neutral"
    distinctive_phrases: List[str] = Field(default_factory=list)


class RelationshipInfo(BaseModel):
    """Relationship between characters"""
    character_name: str
    relationship_type: str  # friend, enemy, family, romantic, etc.
    description: Optional[str] = None


class CharacterProfileBase(BaseModel):
    """Base character profile fields"""
    name: str = Field(..., min_length=1, max_length=255)
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    role: CharacterRole = CharacterRole.SUPPORTING
    voice_profile: Optional[VoiceProfile] = None
    relationships: List[RelationshipInfo] = Field(default_factory=list)
    sample_quotes: List[str] = Field(default_factory=list, max_length=10)
    source_work: Optional[str] = None
    source_author: Optional[str] = None


class CharacterProfileCreate(CharacterProfileBase):
    """Creating a character profile"""
    resource_id: int


class CharacterProfile(CharacterProfileBase):
    """Full character profile"""
    id: int
    resource_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# AUTHOR VOICE MODELS
# ============================================================================

class WritingStyleProfile(BaseModel):
    """Author's writing style characteristics"""
    vocabulary_range: str = "moderate"  # simple, moderate, extensive, specialized
    sentence_structure: str = "varied"  # simple, complex, varied, stream-of-consciousness
    narrative_voice: str = "third_person"  # first_person, third_person, omniscient
    tone_range: List[str] = Field(default_factory=list)  # humorous, dark, hopeful, etc.
    distinctive_techniques: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)


class AuthorVoiceBase(BaseModel):
    """Base author voice fields"""
    author_name: str = Field(..., min_length=1, max_length=255)
    style_profile: WritingStyleProfile = Field(default_factory=WritingStyleProfile)
    sample_passages: List[str] = Field(default_factory=list, max_length=5)
    source_works: List[str] = Field(default_factory=list)


class AuthorVoiceCreate(AuthorVoiceBase):
    """Creating an author voice profile"""
    resource_ids: List[int] = Field(default_factory=list)  # Resources to analyze


class AuthorVoice(AuthorVoiceBase):
    """Full author voice profile"""
    id: int
    user_id: int
    resource_ids: List[int] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SEARCH MODELS
# ============================================================================

class SearchQuery(BaseModel):
    """Search request"""
    query: str = Field(..., min_length=1)
    collection_ids: Optional[List[int]] = None  # None = all user's collections
    resource_types: Optional[List[ResourceType]] = None
    limit: int = Field(default=10, ge=1, le=50)
    include_content: bool = False  # Include full matched content?
    semantic: bool = True  # Use vector search?


class SearchResult(BaseModel):
    """Single search result"""
    resource_id: int
    resource_name: str
    resource_type: ResourceType
    collection_id: int
    collection_name: str
    match_type: str  # "semantic", "keyword", "summary"
    relevance_score: float
    matched_text: Optional[str] = None
    context: Optional[str] = None  # Surrounding context
    index_type: Optional[IndexType] = None


class SearchResponse(BaseModel):
    """Search response with results"""
    query: str
    total_results: int
    results: List[SearchResult]
    search_time_ms: float


# ============================================================================
# LEARNING MODULE MODELS
# ============================================================================

class LearningModuleConfig(BaseModel):
    """Configuration for a learning module resource"""
    module_type: str = "vocabulary"  # vocabulary, grammar, concepts, skills
    source_language: Optional[str] = None  # For language learning
    target_language: Optional[str] = None
    difficulty_level: str = "intermediate"
    spaced_repetition: bool = True
    audio_enabled: bool = False


class LearningProgress(BaseModel):
    """User's progress through a learning module"""
    resource_id: int
    user_id: int
    items_total: int
    items_learned: int
    items_mastered: int
    last_session: Optional[datetime] = None
    next_review: Optional[datetime] = None
    streak_days: int = 0


# ============================================================================
# PROJECT INTEGRATION
# ============================================================================

class ProjectKnowledgeSettings(BaseModel):
    """Knowledge base settings for a project"""
    project_id: int
    linked_collections: List[int] = Field(default_factory=list)
    auto_search_enabled: bool = True
    search_threshold: float = 0.7  # Minimum relevance score
    include_in_context: bool = True  # Include KB results in chat context
    max_context_tokens: int = 2000


# ============================================================================
# UTILITY MODELS
# ============================================================================

class TokenEstimate(BaseModel):
    """Token count estimate for content"""
    text_length: int
    estimated_tokens: int
    method: str  # "tiktoken", "character_ratio", etc.


class BulkOperationResult(BaseModel):
    """Result of a bulk operation"""
    total: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
