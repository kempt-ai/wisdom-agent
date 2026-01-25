"""
Knowledge Base Database Tables

SQLAlchemy models and raw SQL for:
- knowledge_collections
- knowledge_resources  
- resource_indexes
- character_profiles
- author_voices
- learning_progress

Supports PostgreSQL with pgvector for semantic search,
with SQLite fallback for development.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, 
    DateTime, ForeignKey, JSON, Index, CheckConstraint,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
import enum

# Use the existing base from your database setup
# from database.connection import Base
Base = declarative_base()


# ============================================================================
# ENUMS (matching Pydantic models)
# ============================================================================

class CollectionTypeEnum(str, enum.Enum):
    RESEARCH = "research"
    FICTION = "fiction"
    LEARNING = "learning"
    GENERAL = "general"


class ResourceTypeEnum(str, enum.Enum):
    DOCUMENT = "document"
    FICTION_BOOK = "fiction_book"
    NONFICTION_BOOK = "nonfiction_book"
    ARTICLE = "article"
    LEARNING_MODULE = "learning_module"


class SourceTypeEnum(str, enum.Enum):
    UPLOAD = "upload"
    URL = "url"
    TEXT = "text"
    API = "api"


class IndexLevelEnum(str, enum.Enum):
    NONE = "none"
    LIGHT = "light"
    STANDARD = "standard"
    FULL = "full"


class IndexStatusEnum(str, enum.Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class VisibilityEnum(str, enum.Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class IndexTypeEnum(str, enum.Enum):
    SUMMARY = "summary"
    STRUCTURED = "structured"
    VECTOR = "vector"
    CHARACTERS = "characters"
    CHAPTERS = "chapters"
    THEMES = "themes"
    QUOTES = "quotes"


class CharacterRoleEnum(str, enum.Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    NARRATOR = "narrator"


# ============================================================================
# SQLALCHEMY MODELS
# ============================================================================

class KnowledgeCollection(Base):
    """
    A collection of related resources.
    Examples: "Research on AI Ethics", "Tolkien's Works", "Spanish Vocabulary"
    """
    __tablename__ = "knowledge_collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=True, index=True)  # Optional link to project
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    collection_type = Column(String(50), default="general")
    visibility = Column(String(20), default="private")
    tags = Column(JSON, default=list)  # List of tag strings
    settings = Column(JSON, default=dict)  # Flexible settings
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resources = relationship("KnowledgeResource", back_populates="collection", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_collection_user_type", "user_id", "collection_type"),
        Index("idx_collection_project", "project_id"),
    )


class KnowledgeResource(Base):
    """
    A single resource (document, book, article, etc.) within a collection.
    """
    __tablename__ = "knowledge_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resource_type = Column(String(50), default="document")
    
    # Source info
    source_type = Column(String(50), nullable=False)  # upload, url, text, api
    source_url = Column(Text, nullable=True)
    original_content = Column(Text, nullable=True)  # Raw content (for smaller items)
    content_hash = Column(String(64), nullable=True)  # For deduplication
    
    # Token/size info
    token_count = Column(Integer, default=0)
    
    # Indexing status
    index_level = Column(String(20), default="none")
    index_status = Column(String(20), default="pending")
    index_cost_tokens = Column(Integer, default=0)
    index_cost_dollars = Column(Float, default=0.0)
    index_error = Column(Text, nullable=True)  # Error message if failed
    
    visibility = Column(String(20), default="private")
    resource_metadata = Column('metadata', JSON, default=dict)  # 'metadata' is reserved in SQLAlchemy, so use different attr name
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collection = relationship("KnowledgeCollection", back_populates="resources")
    indexes = relationship("ResourceIndex", back_populates="resource", cascade="all, delete-orphan")
    characters = relationship("CharacterProfile", back_populates="resource", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_resource_collection", "collection_id"),
        Index("idx_resource_user_type", "user_id", "resource_type"),
        Index("idx_resource_status", "index_status"),
    )


class ResourceIndex(Base):
    """
    Indexed data for a resource. Multiple indexes per resource (summary, vectors, etc.)
    """
    __tablename__ = "resource_indexes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("knowledge_resources.id", ondelete="CASCADE"), nullable=False)
    
    index_type = Column(String(50), nullable=False)  # summary, structured, vector, characters, chapters
    content = Column(JSON, nullable=True)  # Structured data
    text_content = Column(Text, nullable=True)  # Full text for search
    
    # Vector embedding - stored as JSON for SQLite compatibility
    # For PostgreSQL with pgvector, this would be: embedding = Column(Vector(384))
    embedding = Column(JSON, nullable=True)  # List of floats
    embedding_model = Column(String(100), nullable=True)  # Model used for embedding
    
    chunk_index = Column(Integer, nullable=True)  # For chunked content
    chunk_total = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    resource = relationship("KnowledgeResource", back_populates="indexes")

    # Indexes
    __table_args__ = (
        Index("idx_resindex_resource_type", "resource_id", "index_type"),
    )


class CharacterProfile(Base):
    """
    Character extracted from fiction for interaction/analysis.
    """
    __tablename__ = "character_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("knowledge_resources.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    aliases = Column(JSON, default=list)  # Alternative names
    description = Column(Text, nullable=True)
    role = Column(String(100), default="supporting")  # protagonist, antagonist, etc.
    
    voice_profile = Column(JSON, nullable=True)  # {vocabulary, speech_patterns, concerns, tone}
    relationships = Column(JSON, default=list)  # [{character_id, relationship_type, description}]
    sample_quotes = Column(JSON, default=list)  # Up to 10 representative quotes
    
    source_work = Column(String(255), nullable=True)
    source_author = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    resource = relationship("KnowledgeResource", back_populates="characters")

    # Indexes
    __table_args__ = (
        Index("idx_character_resource", "resource_id"),
        Index("idx_character_name", "name"),
    )


class AuthorVoice(Base):
    """
    Author writing style profile for generating content in their style.
    """
    __tablename__ = "author_voices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    author_name = Column(String(255), nullable=False)
    style_profile = Column(JSON, default=dict)  # {vocabulary_range, sentence_structure, etc.}
    sample_passages = Column(JSON, default=list)  # Representative passages
    source_works = Column(JSON, default=list)  # List of work titles
    resource_ids = Column(JSON, default=list)  # Resources used to create profile
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_author_user", "user_id"),
        Index("idx_author_name", "author_name"),
    )


class LearningProgress(Base):
    """
    User's progress through a learning module resource.
    """
    __tablename__ = "learning_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("knowledge_resources.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False)
    
    items_total = Column(Integer, default=0)
    items_learned = Column(Integer, default=0)
    items_mastered = Column(Integer, default=0)
    
    last_session = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)
    streak_days = Column(Integer, default=0)
    
    item_states = Column(JSON, default=dict)  # Per-item learning state
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_learning_user_resource", "user_id", "resource_id", unique=True),
    )


# ============================================================================
# RAW SQL FOR MIGRATIONS
# ============================================================================

CREATE_TABLES_SQL = """
-- Knowledge Collections
CREATE TABLE IF NOT EXISTS knowledge_collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    collection_type VARCHAR(50) DEFAULT 'general',
    visibility VARCHAR(20) DEFAULT 'private',
    tags JSONB DEFAULT '[]',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_collection_user_type ON knowledge_collections(user_id, collection_type);
CREATE INDEX IF NOT EXISTS idx_collection_project ON knowledge_collections(project_id);

-- Knowledge Resources
CREATE TABLE IF NOT EXISTS knowledge_resources (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) DEFAULT 'document',
    source_type VARCHAR(50) NOT NULL,
    source_url TEXT,
    original_content TEXT,
    content_hash VARCHAR(64),
    token_count INTEGER DEFAULT 0,
    index_level VARCHAR(20) DEFAULT 'none',
    index_status VARCHAR(20) DEFAULT 'pending',
    index_cost_tokens INTEGER DEFAULT 0,
    index_cost_dollars DECIMAL(10,6) DEFAULT 0,
    index_error TEXT,
    visibility VARCHAR(20) DEFAULT 'private',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resource_collection ON knowledge_resources(collection_id);
CREATE INDEX IF NOT EXISTS idx_resource_user_type ON knowledge_resources(user_id, resource_type);
CREATE INDEX IF NOT EXISTS idx_resource_status ON knowledge_resources(index_status);

-- Resource Indexes (embedding stored as JSONB for compatibility)
CREATE TABLE IF NOT EXISTS resource_indexes (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    index_type VARCHAR(50) NOT NULL,
    content JSONB,
    text_content TEXT,
    embedding JSONB,  -- Vector stored as JSON array upgrade to pgvector later if needed
    embedding_model VARCHAR(100),
    chunk_index INTEGER,
    chunk_total INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resindex_resource_type ON resource_indexes(resource_id, index_type);
-- For semantic search (pgvector)
-- CREATE INDEX IF NOT EXISTS idx_resindex_embedding ON resource_indexes USING ivfflat (embedding vector_cosine_ops);

-- Character Profiles
CREATE TABLE IF NOT EXISTS character_profiles (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    aliases JSONB DEFAULT '[]',
    description TEXT,
    role VARCHAR(100) DEFAULT 'supporting',
    voice_profile JSONB,
    relationships JSONB DEFAULT '[]',
    sample_quotes JSONB DEFAULT '[]',
    source_work VARCHAR(255),
    source_author VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_character_resource ON character_profiles(resource_id);
CREATE INDEX IF NOT EXISTS idx_character_name ON character_profiles(name);

-- Author Voices
CREATE TABLE IF NOT EXISTS author_voices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    style_profile JSONB DEFAULT '{}',
    sample_passages JSONB DEFAULT '[]',
    source_works JSONB DEFAULT '[]',
    resource_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_author_user ON author_voices(user_id);
CREATE INDEX IF NOT EXISTS idx_author_name ON author_voices(author_name);

-- Learning Progress
CREATE TABLE IF NOT EXISTS learning_progress (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    items_total INTEGER DEFAULT 0,
    items_learned INTEGER DEFAULT 0,
    items_mastered INTEGER DEFAULT 0,
    last_session TIMESTAMP,
    next_review TIMESTAMP,
    streak_days INTEGER DEFAULT 0,
    item_states JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, resource_id)
);

CREATE INDEX IF NOT EXISTS idx_learning_user_resource ON learning_progress(user_id, resource_id);
"""

# SQLite-compatible version (no JSONB, no vector)
CREATE_TABLES_SQLITE = """
-- Knowledge Collections
CREATE TABLE IF NOT EXISTS knowledge_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    collection_type VARCHAR(50) DEFAULT 'general',
    visibility VARCHAR(20) DEFAULT 'private',
    tags TEXT DEFAULT '[]',
    settings TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collection_user_type ON knowledge_collections(user_id, collection_type);
CREATE INDEX IF NOT EXISTS idx_collection_project ON knowledge_collections(project_id);

-- Knowledge Resources
CREATE TABLE IF NOT EXISTS knowledge_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) DEFAULT 'document',
    source_type VARCHAR(50) NOT NULL,
    source_url TEXT,
    original_content TEXT,
    content_hash VARCHAR(64),
    token_count INTEGER DEFAULT 0,
    index_level VARCHAR(20) DEFAULT 'none',
    index_status VARCHAR(20) DEFAULT 'pending',
    index_cost_tokens INTEGER DEFAULT 0,
    index_cost_dollars REAL DEFAULT 0,
    index_error TEXT,
    visibility VARCHAR(20) DEFAULT 'private',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resource_collection ON knowledge_resources(collection_id);
CREATE INDEX IF NOT EXISTS idx_resource_user_type ON knowledge_resources(user_id, resource_type);
CREATE INDEX IF NOT EXISTS idx_resource_status ON knowledge_resources(index_status);

-- Resource Indexes
CREATE TABLE IF NOT EXISTS resource_indexes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    index_type VARCHAR(50) NOT NULL,
    content TEXT,
    text_content TEXT,
    embedding TEXT,
    embedding_model VARCHAR(100),
    chunk_index INTEGER,
    chunk_total INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resindex_resource_type ON resource_indexes(resource_id, index_type);

-- Character Profiles
CREATE TABLE IF NOT EXISTS character_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    aliases TEXT DEFAULT '[]',
    description TEXT,
    role VARCHAR(100) DEFAULT 'supporting',
    voice_profile TEXT,
    relationships TEXT DEFAULT '[]',
    sample_quotes TEXT DEFAULT '[]',
    source_work VARCHAR(255),
    source_author VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_character_resource ON character_profiles(resource_id);
CREATE INDEX IF NOT EXISTS idx_character_name ON character_profiles(name);

-- Author Voices
CREATE TABLE IF NOT EXISTS author_voices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    style_profile TEXT DEFAULT '{}',
    sample_passages TEXT DEFAULT '[]',
    source_works TEXT DEFAULT '[]',
    resource_ids TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_author_user ON author_voices(user_id);
CREATE INDEX IF NOT EXISTS idx_author_name ON author_voices(author_name);

-- Learning Progress
CREATE TABLE IF NOT EXISTS learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    items_total INTEGER DEFAULT 0,
    items_learned INTEGER DEFAULT 0,
    items_mastered INTEGER DEFAULT 0,
    last_session TIMESTAMP,
    next_review TIMESTAMP,
    streak_days INTEGER DEFAULT 0,
    item_states TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, resource_id)
);

CREATE INDEX IF NOT EXISTS idx_learning_user_resource ON learning_progress(user_id, resource_id);
"""


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================

def create_knowledge_tables(connection, use_postgres: bool = True):
    """
    Execute table creation SQL.
    
    Args:
        connection: Database connection (SQLAlchemy connection object)
        use_postgres: True for PostgreSQL, False for SQLite
    """
    from sqlalchemy import text
    
    sql = CREATE_TABLES_SQL if use_postgres else CREATE_TABLES_SQLITE
    
    # Split by statement and execute each
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    for statement in statements:
        # Remove SQL comments (lines starting with --)
        lines = statement.split('\n')
        non_comment_lines = [l for l in lines if not l.strip().startswith('--')]
        cleaned_statement = '\n'.join(non_comment_lines).strip()
        
        # Skip if nothing left after removing comments
        if not cleaned_statement:
            continue
            
        try:
            connection.execute(text(cleaned_statement))
            connection.commit()  # Commit each statement individually
        except Exception as e:
            connection.rollback()  # Rollback failed statement to reset transaction
            error_str = str(e).lower()
            if 'already exists' not in error_str and 'duplicate' not in error_str:
                print(f"Warning: Could not execute: {cleaned_statement[:50]}... Error: {e}")
    
    print(f"Knowledge Base tables created/verified ({'PostgreSQL' if use_postgres else 'SQLite'})")


def drop_knowledge_tables(connection):
    """Drop all knowledge base tables (use carefully!)"""
    from sqlalchemy import text
    
    tables = [
        "learning_progress",
        "author_voices", 
        "character_profiles",
        "resource_indexes",
        "knowledge_resources",
        "knowledge_collections"
    ]
    
    for table in tables:
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        except Exception as e:
            print(f"Warning: Could not drop {table}: {e}")
    
    print("Knowledge Base tables dropped")
