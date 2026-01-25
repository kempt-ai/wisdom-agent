"""
Argument Builder Database Tables

SQLAlchemy models and raw SQL for:
- parsed_resources (structured extraction from KB resources)
- argument_claims (individual claims with classification)
- argument_evidence (evidence supporting claims)
- argument_modules (user-created argument structures)
- module_evidence (links between modules and evidence)

Supports PostgreSQL with SQLite fallback for development.

Future-ready fields included:
- created_by: For multi-user collaboration
- derived_from: For attribution tracking (micropayment economy)
- license: For usage rights

Updated: 2025-01-19 - Renamed tables to avoid conflict with F/L/W Checker
  - extracted_claims → argument_claims
  - extracted_evidence → argument_evidence
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, ForeignKey, JSON, Index, CheckConstraint,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

# Use the existing base from your database setup
# from backend.database.connection import Base
Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class ClaimTypeEnum(str, enum.Enum):
    """Classification of claim types"""
    FACTUAL = "factual"           # Verifiable fact about the world
    INTERPRETIVE = "interpretive" # Analysis or interpretation of facts
    PRESCRIPTIVE = "prescriptive" # Recommendation or call to action


class VerificationStatusEnum(str, enum.Enum):
    """Status of claim verification"""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    PARTIALLY_VERIFIED = "partially_verified"


class EvidenceTypeEnum(str, enum.Enum):
    """Types of evidence"""
    STATISTIC = "statistic"
    QUOTE = "quote"
    CITATION = "citation"
    EXAMPLE = "example"
    DATA = "data"
    TESTIMONY = "testimony"


class ModuleTypeEnum(str, enum.Enum):
    """Types of argument modules"""
    THESIS = "thesis"           # Top-level claim
    ARGUMENT = "argument"       # Supporting argument
    COUNTER = "counter"         # Counter-argument
    REBUTTAL = "rebuttal"       # Response to counter-argument
    EVIDENCE = "evidence"       # Evidence container


class ModuleStatusEnum(str, enum.Enum):
    """Status of argument modules"""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EvidenceRelationEnum(str, enum.Enum):
    """Relationship between evidence and modules"""
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    CONTEXTUALIZES = "contextualizes"


# ============================================================================
# SQLALCHEMY MODELS
# ============================================================================

class ParsedResource(Base):
    """
    Structured extraction from a KB resource.
    
    When a resource is parsed, this stores:
    - The main thesis identified
    - A summary of the content
    - The full hierarchical structure as JSON
    - Metadata about the parsing process
    """
    __tablename__ = "parsed_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("knowledge_resources.id", ondelete="CASCADE"), nullable=False)
    
    main_thesis = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    structure_json = Column(JSON, nullable=True)  # Full hierarchical structure
    
    # Parsing metadata
    parsed_at = Column(DateTime, default=datetime.utcnow)
    parser_model = Column(String(100), nullable=True)  # Which LLM did the parsing
    parser_version = Column(String(50), nullable=True)  # Version of parsing prompt
    parsing_cost_tokens = Column(Integer, default=0)
    parsing_cost_dollars = Column(Float, default=0.0)
    
    # Sources cited in the document
    sources_cited = Column(JSON, default=list)  # List of URLs/references
    
    # Future-ready fields
    created_by = Column(String(100), nullable=True)  # For multi-user
    derived_from = Column(JSON, nullable=True)  # Attribution tracking
    license = Column(String(100), default="private")  # Usage rights
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    claims = relationship("ArgumentClaim", back_populates="parsed_resource", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_parsed_resource", "resource_id"),
        Index("idx_parsed_at", "parsed_at"),
    )


class ArgumentClaim(Base):
    """
    Individual claims extracted from resources.
    
    Each claim is:
    - Classified by type (factual, interpretive, prescriptive)
    - Linked to its source context
    - Optionally verified through fact-checking
    
    Note: Renamed from ExtractedClaim to avoid conflict with F/L/W Checker
    """
    __tablename__ = "argument_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parsed_resource_id = Column(Integer, ForeignKey("parsed_resources.id", ondelete="CASCADE"), nullable=False)
    
    # The claim itself
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String(50), default="factual")  # factual, interpretive, prescriptive
    
    # Context and source
    context = Column(Text, nullable=True)  # Surrounding text for context
    source_quote = Column(Text, nullable=True)  # Original quote if available
    position_in_doc = Column(Integer, nullable=True)  # For ordering
    
    # Parser confidence
    confidence = Column(Float, default=1.0)  # Parser's confidence in extraction
    
    # Argument hierarchy (for nested arguments)
    parent_claim_id = Column(Integer, ForeignKey("argument_claims.id", ondelete="SET NULL"), nullable=True)
    argument_title = Column(String(255), nullable=True)  # Brief title for the argument
    
    # Verification (from fact-checker)
    verification_status = Column(String(50), nullable=True)  # verified, disputed, unverified
    verification_sources = Column(JSON, nullable=True)  # Sources used to verify
    verification_notes = Column(Text, nullable=True)  # Notes from verification
    verified_at = Column(DateTime, nullable=True)
    
    # Vector embedding for semantic search (stored as JSON for SQLite compatibility)
    embedding = Column(JSON, nullable=True)
    embedding_model = Column(String(100), nullable=True)
    
    # Future-ready fields
    created_by = Column(String(100), nullable=True)
    derived_from = Column(JSON, nullable=True)
    license = Column(String(100), default="private")
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    parsed_resource = relationship("ParsedResource", back_populates="claims")
    evidence = relationship("ArgumentEvidence", back_populates="claim", cascade="all, delete-orphan")
    sub_claims = relationship("ArgumentClaim", backref="parent_claim", remote_side=[id])

    # Indexes
    __table_args__ = (
        Index("idx_argclaim_parsed_resource", "parsed_resource_id"),
        Index("idx_argclaim_type", "claim_type"),
        Index("idx_argclaim_verification", "verification_status"),
        Index("idx_argclaim_parent", "parent_claim_id"),
    )


class ArgumentEvidence(Base):
    """
    Evidence supporting claims.
    
    Evidence can be:
    - Statistics and data
    - Quotes from sources
    - Citations to external works
    - Examples and case studies
    
    Note: Renamed from ExtractedEvidence to avoid conflict with F/L/W Checker
    """
    __tablename__ = "argument_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("argument_claims.id", ondelete="CASCADE"), nullable=False)
    
    # Evidence content
    evidence_type = Column(String(50), nullable=False)  # statistic, quote, citation, example
    content = Column(Text, nullable=False)
    
    # Source attribution
    source_url = Column(Text, nullable=True)
    source_title = Column(String(500), nullable=True)
    source_author = Column(String(255), nullable=True)
    source_date = Column(String(100), nullable=True)  # Flexible date format
    
    # Ordering
    position = Column(Integer, default=0)
    
    # Future-ready fields
    created_by = Column(String(100), nullable=True)
    derived_from = Column(JSON, nullable=True)
    license = Column(String(100), default="private")
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    claim = relationship("ArgumentClaim", back_populates="evidence")

    # Indexes
    __table_args__ = (
        Index("idx_argevidence_claim", "claim_id"),
        Index("idx_argevidence_type", "evidence_type"),
    )


class ArgumentModule(Base):
    """
    User-created argument structures.
    
    Allows users to:
    - Build their own argument hierarchies
    - Compose arguments from extracted claims
    - Create thesis → argument → evidence structures
    """
    __tablename__ = "argument_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Module content
    title = Column(String(500), nullable=False)
    thesis = Column(Text, nullable=True)  # The main claim this module makes
    description = Column(Text, nullable=True)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey("argument_modules.id", ondelete="SET NULL"), nullable=True)
    position = Column(Integer, default=0)  # Order among siblings
    
    # Classification
    module_type = Column(String(50), default="argument")  # thesis, argument, counter, rebuttal
    status = Column(String(50), default="draft")  # draft, review, published
    
    # Tags for organization
    tags = Column(JSON, default=list)
    
    # Future-ready fields
    created_by = Column(String(100), nullable=True)
    derived_from = Column(JSON, nullable=True)  # Track what this was built from
    license = Column(String(100), default="private")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    children = relationship("ArgumentModule", backref="parent", remote_side=[id])
    evidence_links = relationship("ModuleEvidence", back_populates="module", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_module_user", "user_id"),
        Index("idx_module_parent", "parent_id"),
        Index("idx_module_type", "module_type"),
        Index("idx_module_status", "status"),
    )


class ModuleEvidence(Base):
    """
    Links between argument modules and evidence.
    
    Allows modules to reference:
    - Extracted claims from parsed resources
    - Entire KB resources
    - Custom notes/annotations
    """
    __tablename__ = "module_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_id = Column(Integer, ForeignKey("argument_modules.id", ondelete="CASCADE"), nullable=False)
    
    # Link to extracted claim (optional)
    claim_id = Column(Integer, ForeignKey("argument_claims.id", ondelete="SET NULL"), nullable=True)
    
    # Link to KB resource directly (optional)
    resource_id = Column(Integer, ForeignKey("knowledge_resources.id", ondelete="SET NULL"), nullable=True)
    
    # Custom content (if not linking to existing claim/resource)
    custom_note = Column(Text, nullable=True)
    custom_source = Column(String(500), nullable=True)
    
    # Relationship type
    relation_type = Column(String(50), default="supports")  # supports, opposes, contextualizes
    
    # Ordering
    position = Column(Integer, default=0)
    
    # Annotation
    annotation = Column(Text, nullable=True)  # User's note about why this evidence matters
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    module = relationship("ArgumentModule", back_populates="evidence_links")

    # Indexes
    __table_args__ = (
        Index("idx_modevidence_module", "module_id"),
        Index("idx_modevidence_claim", "claim_id"),
        Index("idx_modevidence_resource", "resource_id"),
    )


# ============================================================================
# RAW SQL FOR MIGRATIONS
# ============================================================================

CREATE_ARGUMENT_TABLES_SQL = """
-- Parsed Resources (structured extraction from KB resources)
CREATE TABLE IF NOT EXISTS parsed_resources (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    main_thesis TEXT,
    summary TEXT,
    structure_json JSONB,
    parsed_at TIMESTAMP DEFAULT NOW(),
    parser_model VARCHAR(100),
    parser_version VARCHAR(50),
    parsing_cost_tokens INTEGER DEFAULT 0,
    parsing_cost_dollars DECIMAL(10,6) DEFAULT 0,
    sources_cited JSONB DEFAULT '[]',
    created_by VARCHAR(100),
    derived_from JSONB,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parsed_resource ON parsed_resources(resource_id);
CREATE INDEX IF NOT EXISTS idx_parsed_at ON parsed_resources(parsed_at);

-- Argument Claims (individual claims from resources)
-- Note: Renamed from extracted_claims to avoid conflict with F/L/W Checker
CREATE TABLE IF NOT EXISTS argument_claims (
    id SERIAL PRIMARY KEY,
    parsed_resource_id INTEGER REFERENCES parsed_resources(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    claim_type VARCHAR(50) DEFAULT 'factual',
    context TEXT,
    source_quote TEXT,
    position_in_doc INTEGER,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    parent_claim_id INTEGER REFERENCES argument_claims(id) ON DELETE SET NULL,
    argument_title VARCHAR(255),
    verification_status VARCHAR(50),
    verification_sources JSONB,
    verification_notes TEXT,
    verified_at TIMESTAMP,
    embedding JSONB,
    embedding_model VARCHAR(100),
    created_by VARCHAR(100),
    derived_from JSONB,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_argclaim_parsed_resource ON argument_claims(parsed_resource_id);
CREATE INDEX IF NOT EXISTS idx_argclaim_type ON argument_claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_argclaim_verification ON argument_claims(verification_status);
CREATE INDEX IF NOT EXISTS idx_argclaim_parent ON argument_claims(parent_claim_id);

-- Argument Evidence (evidence supporting claims)
-- Note: Renamed from extracted_evidence to avoid conflict with F/L/W Checker
CREATE TABLE IF NOT EXISTS argument_evidence (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES argument_claims(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    source_title VARCHAR(500),
    source_author VARCHAR(255),
    source_date VARCHAR(100),
    position INTEGER DEFAULT 0,
    created_by VARCHAR(100),
    derived_from JSONB,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_argevidence_claim ON argument_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_argevidence_type ON argument_evidence(evidence_type);

-- Argument Modules (user-created argument structures)
CREATE TABLE IF NOT EXISTS argument_modules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    thesis TEXT,
    description TEXT,
    parent_id INTEGER REFERENCES argument_modules(id) ON DELETE SET NULL,
    position INTEGER DEFAULT 0,
    module_type VARCHAR(50) DEFAULT 'argument',
    status VARCHAR(50) DEFAULT 'draft',
    tags JSONB DEFAULT '[]',
    created_by VARCHAR(100),
    derived_from JSONB,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_module_user ON argument_modules(user_id);
CREATE INDEX IF NOT EXISTS idx_module_parent ON argument_modules(parent_id);
CREATE INDEX IF NOT EXISTS idx_module_type ON argument_modules(module_type);
CREATE INDEX IF NOT EXISTS idx_module_status ON argument_modules(status);

-- Module Evidence (links between modules and evidence)
CREATE TABLE IF NOT EXISTS module_evidence (
    id SERIAL PRIMARY KEY,
    module_id INTEGER REFERENCES argument_modules(id) ON DELETE CASCADE,
    claim_id INTEGER REFERENCES argument_claims(id) ON DELETE SET NULL,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE SET NULL,
    custom_note TEXT,
    custom_source VARCHAR(500),
    relation_type VARCHAR(50) DEFAULT 'supports',
    position INTEGER DEFAULT 0,
    annotation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modevidence_module ON module_evidence(module_id);
CREATE INDEX IF NOT EXISTS idx_modevidence_claim ON module_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_modevidence_resource ON module_evidence(resource_id);
"""

# SQLite-compatible version (no JSONB, no DECIMAL)
CREATE_ARGUMENT_TABLES_SQLITE = """
-- Parsed Resources (structured extraction from KB resources)
CREATE TABLE IF NOT EXISTS parsed_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE CASCADE,
    main_thesis TEXT,
    summary TEXT,
    structure_json TEXT,
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parser_model VARCHAR(100),
    parser_version VARCHAR(50),
    parsing_cost_tokens INTEGER DEFAULT 0,
    parsing_cost_dollars REAL DEFAULT 0,
    sources_cited TEXT DEFAULT '[]',
    created_by VARCHAR(100),
    derived_from TEXT,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_parsed_resource ON parsed_resources(resource_id);
CREATE INDEX IF NOT EXISTS idx_parsed_at ON parsed_resources(parsed_at);

-- Argument Claims (individual claims from resources)
-- Note: Renamed from extracted_claims to avoid conflict with F/L/W Checker
CREATE TABLE IF NOT EXISTS argument_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parsed_resource_id INTEGER REFERENCES parsed_resources(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    claim_type VARCHAR(50) DEFAULT 'factual',
    context TEXT,
    source_quote TEXT,
    position_in_doc INTEGER,
    confidence REAL DEFAULT 1.0,
    parent_claim_id INTEGER REFERENCES argument_claims(id) ON DELETE SET NULL,
    argument_title VARCHAR(255),
    verification_status VARCHAR(50),
    verification_sources TEXT,
    verification_notes TEXT,
    verified_at TIMESTAMP,
    embedding TEXT,
    embedding_model VARCHAR(100),
    created_by VARCHAR(100),
    derived_from TEXT,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_argclaim_parsed_resource ON argument_claims(parsed_resource_id);
CREATE INDEX IF NOT EXISTS idx_argclaim_type ON argument_claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_argclaim_verification ON argument_claims(verification_status);
CREATE INDEX IF NOT EXISTS idx_argclaim_parent ON argument_claims(parent_claim_id);

-- Argument Evidence (evidence supporting claims)
-- Note: Renamed from extracted_evidence to avoid conflict with F/L/W Checker
CREATE TABLE IF NOT EXISTS argument_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER REFERENCES argument_claims(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    source_title VARCHAR(500),
    source_author VARCHAR(255),
    source_date VARCHAR(100),
    position INTEGER DEFAULT 0,
    created_by VARCHAR(100),
    derived_from TEXT,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_argevidence_claim ON argument_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_argevidence_type ON argument_evidence(evidence_type);

-- Argument Modules (user-created argument structures)
CREATE TABLE IF NOT EXISTS argument_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    thesis TEXT,
    description TEXT,
    parent_id INTEGER REFERENCES argument_modules(id) ON DELETE SET NULL,
    position INTEGER DEFAULT 0,
    module_type VARCHAR(50) DEFAULT 'argument',
    status VARCHAR(50) DEFAULT 'draft',
    tags TEXT DEFAULT '[]',
    created_by VARCHAR(100),
    derived_from TEXT,
    license VARCHAR(100) DEFAULT 'private',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_module_user ON argument_modules(user_id);
CREATE INDEX IF NOT EXISTS idx_module_parent ON argument_modules(parent_id);
CREATE INDEX IF NOT EXISTS idx_module_type ON argument_modules(module_type);
CREATE INDEX IF NOT EXISTS idx_module_status ON argument_modules(status);

-- Module Evidence (links between modules and evidence)
CREATE TABLE IF NOT EXISTS module_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER REFERENCES argument_modules(id) ON DELETE CASCADE,
    claim_id INTEGER REFERENCES argument_claims(id) ON DELETE SET NULL,
    resource_id INTEGER REFERENCES knowledge_resources(id) ON DELETE SET NULL,
    custom_note TEXT,
    custom_source VARCHAR(500),
    relation_type VARCHAR(50) DEFAULT 'supports',
    position INTEGER DEFAULT 0,
    annotation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_modevidence_module ON module_evidence(module_id);
CREATE INDEX IF NOT EXISTS idx_modevidence_claim ON module_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_modevidence_resource ON module_evidence(resource_id);
"""


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================

def create_argument_tables(connection, use_postgres: bool = True):
    """
    Execute table creation SQL for argument builder tables.
    
    Args:
        connection: Database connection (SQLAlchemy connection object)
        use_postgres: True for PostgreSQL, False for SQLite
    """
    from sqlalchemy import text
    
    sql = CREATE_ARGUMENT_TABLES_SQL if use_postgres else CREATE_ARGUMENT_TABLES_SQLITE
    
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
    
    print(f"Argument Builder tables created/verified ({'PostgreSQL' if use_postgres else 'SQLite'})")


def drop_argument_tables(connection):
    """Drop all argument builder tables (use carefully!)"""
    from sqlalchemy import text
    
    tables = [
        "module_evidence",
        "argument_modules",
        "argument_evidence",
        "argument_claims",
        "parsed_resources"
    ]
    
    for table in tables:
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        except Exception as e:
            print(f"Warning: Could not drop {table}: {e}")
    
    print("Argument Builder tables dropped")
