"""
Investigation Builder (AB) Database Tables

Raw SQL table creation for the Investigation Builder feature.
These tables are separate from the existing argument_tables.py
(which handles KB resource parsing/extraction).

Tables:
- ab_investigations: Top-level investigation containers
- ab_definitions: Term definitions within investigations
- ab_claims: Claims (the building blocks of arguments)
- ab_evidence: Evidence supporting claims
- ab_source_credibility: Publication-level credibility assessments
- ab_evidence_credibility: Per-piece credibility (links evidence to source)
- ab_counterarguments: Counterarguments and rebuttals
- ab_rebuttal_evidence: Evidence supporting rebuttals
- ab_investigation_changelog: Change tracking for temporal versioning

Supports PostgreSQL with SQLite fallback for development.
"""

# ============================================================================
# POSTGRESQL SQL
# ============================================================================

CREATE_AB_TABLES_SQL = """
-- Investigations: top-level container for structured investigations
CREATE TABLE IF NOT EXISTS ab_investigations (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    overview_html TEXT NOT NULL DEFAULT '',
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    version INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_ab_inv_slug ON ab_investigations(slug);
CREATE INDEX IF NOT EXISTS idx_ab_inv_status ON ab_investigations(status);

-- Definitions: explain terms used in the investigation
CREATE TABLE IF NOT EXISTS ab_definitions (
    id SERIAL PRIMARY KEY,
    investigation_id INTEGER REFERENCES ab_investigations(id) ON DELETE CASCADE NOT NULL,
    term VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    definition_html TEXT NOT NULL DEFAULT '',
    see_also JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(investigation_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_ab_def_investigation ON ab_definitions(investigation_id);
CREATE INDEX IF NOT EXISTS idx_ab_def_slug ON ab_definitions(investigation_id, slug);

-- Claims: building blocks of the argument
CREATE TABLE IF NOT EXISTS ab_claims (
    id SERIAL PRIMARY KEY,
    investigation_id INTEGER REFERENCES ab_investigations(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    claim_text TEXT NOT NULL,
    exposition_html TEXT,
    status VARCHAR(50) DEFAULT 'ongoing',
    temporal_note TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(investigation_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_ab_claim_investigation ON ab_claims(investigation_id);
CREATE INDEX IF NOT EXISTS idx_ab_claim_slug ON ab_claims(investigation_id, slug);
CREATE INDEX IF NOT EXISTS idx_ab_claim_status ON ab_claims(status);

-- Evidence: supports claims
CREATE TABLE IF NOT EXISTS ab_evidence (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES ab_claims(id) ON DELETE CASCADE NOT NULL,
    kb_resource_id INTEGER,
    source_title VARCHAR(500),
    source_url TEXT,
    source_type VARCHAR(100),
    key_quote TEXT,
    key_point TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    source_anchor_type VARCHAR(50),
    source_anchor_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_ab_ev_claim ON ab_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_ab_ev_kb ON ab_evidence(kb_resource_id);

-- Source credibility: publication-level assessments (shared across evidence)
CREATE TABLE IF NOT EXISTS ab_source_credibility (
    id SERIAL PRIMARY KEY,
    publication_name VARCHAR(255) NOT NULL UNIQUE,
    publication_type VARCHAR(100),
    founded_year INTEGER,
    affiliation TEXT,
    funding_sources TEXT,
    track_record TEXT,
    ai_assessment_publication TEXT,
    ai_assessment_generated_at TIMESTAMP,
    ai_model_used VARCHAR(100),
    user_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ab_src_cred_name ON ab_source_credibility(publication_name);

-- Evidence credibility: per-piece credibility linking evidence to source
CREATE TABLE IF NOT EXISTS ab_evidence_credibility (
    id SERIAL PRIMARY KEY,
    evidence_id INTEGER REFERENCES ab_evidence(id) ON DELETE CASCADE NOT NULL,
    source_credibility_id INTEGER REFERENCES ab_source_credibility(id),
    author_names TEXT,
    author_roles TEXT,
    published_date DATE,
    style VARCHAR(100),
    intent VARCHAR(100),
    primary_sources_cited BOOLEAN,
    primary_sources_description TEXT,
    ai_assessment_piece TEXT,
    ai_assessment_generated_at TIMESTAMP,
    user_notes TEXT,
    credibility_rating INTEGER CHECK (credibility_rating >= 1 AND credibility_rating <= 5),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ab_ev_cred_evidence ON ab_evidence_credibility(evidence_id);
CREATE INDEX IF NOT EXISTS idx_ab_ev_cred_source ON ab_evidence_credibility(source_credibility_id);

-- Counterarguments and rebuttals
CREATE TABLE IF NOT EXISTS ab_counterarguments (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES ab_claims(id) ON DELETE CASCADE NOT NULL,
    counter_text TEXT NOT NULL,
    rebuttal_text TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ab_counter_claim ON ab_counterarguments(claim_id);

-- Evidence supporting rebuttals
CREATE TABLE IF NOT EXISTS ab_rebuttal_evidence (
    id SERIAL PRIMARY KEY,
    counterargument_id INTEGER REFERENCES ab_counterarguments(id) ON DELETE CASCADE NOT NULL,
    evidence_id INTEGER REFERENCES ab_evidence(id),
    custom_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_ab_reb_ev_counter ON ab_rebuttal_evidence(counterargument_id);

-- Change log for temporal versioning
CREATE TABLE IF NOT EXISTS ab_investigation_changelog (
    id SERIAL PRIMARY KEY,
    investigation_id INTEGER REFERENCES ab_investigations(id) ON DELETE CASCADE NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW(),
    change_type VARCHAR(50),
    change_summary TEXT,
    changed_by VARCHAR(255),
    previous_state JSONB
);

CREATE INDEX IF NOT EXISTS idx_ab_changelog_inv ON ab_investigation_changelog(investigation_id);
CREATE INDEX IF NOT EXISTS idx_ab_changelog_time ON ab_investigation_changelog(changed_at);
"""

# ============================================================================
# SQLITE SQL
# ============================================================================

CREATE_AB_TABLES_SQLITE = """
-- Investigations
CREATE TABLE IF NOT EXISTS ab_investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    overview_html TEXT NOT NULL DEFAULT '',
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    version INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_ab_inv_slug ON ab_investigations(slug);
CREATE INDEX IF NOT EXISTS idx_ab_inv_status ON ab_investigations(status);

-- Definitions
CREATE TABLE IF NOT EXISTS ab_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER REFERENCES ab_investigations(id) ON DELETE CASCADE NOT NULL,
    term VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    definition_html TEXT NOT NULL DEFAULT '',
    see_also TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(investigation_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_ab_def_investigation ON ab_definitions(investigation_id);

-- Claims
CREATE TABLE IF NOT EXISTS ab_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER REFERENCES ab_investigations(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    claim_text TEXT NOT NULL,
    exposition_html TEXT,
    status VARCHAR(50) DEFAULT 'ongoing',
    temporal_note TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(investigation_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_ab_claim_investigation ON ab_claims(investigation_id);
CREATE INDEX IF NOT EXISTS idx_ab_claim_status ON ab_claims(status);

-- Evidence
CREATE TABLE IF NOT EXISTS ab_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER REFERENCES ab_claims(id) ON DELETE CASCADE NOT NULL,
    kb_resource_id INTEGER,
    source_title VARCHAR(500),
    source_url TEXT,
    source_type VARCHAR(100),
    key_quote TEXT,
    key_point TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_anchor_type VARCHAR(50),
    source_anchor_data TEXT
);

CREATE INDEX IF NOT EXISTS idx_ab_ev_claim ON ab_evidence(claim_id);

-- Source credibility
CREATE TABLE IF NOT EXISTS ab_source_credibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_name VARCHAR(255) NOT NULL UNIQUE,
    publication_type VARCHAR(100),
    founded_year INTEGER,
    affiliation TEXT,
    funding_sources TEXT,
    track_record TEXT,
    ai_assessment_publication TEXT,
    ai_assessment_generated_at TIMESTAMP,
    ai_model_used VARCHAR(100),
    user_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evidence credibility
CREATE TABLE IF NOT EXISTS ab_evidence_credibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id INTEGER REFERENCES ab_evidence(id) ON DELETE CASCADE NOT NULL,
    source_credibility_id INTEGER REFERENCES ab_source_credibility(id),
    author_names TEXT,
    author_roles TEXT,
    published_date DATE,
    style VARCHAR(100),
    intent VARCHAR(100),
    primary_sources_cited BOOLEAN,
    primary_sources_description TEXT,
    ai_assessment_piece TEXT,
    ai_assessment_generated_at TIMESTAMP,
    user_notes TEXT,
    credibility_rating INTEGER CHECK (credibility_rating >= 1 AND credibility_rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ab_ev_cred_evidence ON ab_evidence_credibility(evidence_id);

-- Counterarguments
CREATE TABLE IF NOT EXISTS ab_counterarguments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER REFERENCES ab_claims(id) ON DELETE CASCADE NOT NULL,
    counter_text TEXT NOT NULL,
    rebuttal_text TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ab_counter_claim ON ab_counterarguments(claim_id);

-- Rebuttal evidence
CREATE TABLE IF NOT EXISTS ab_rebuttal_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    counterargument_id INTEGER REFERENCES ab_counterarguments(id) ON DELETE CASCADE NOT NULL,
    evidence_id INTEGER REFERENCES ab_evidence(id),
    custom_note TEXT
);

-- Change log
CREATE TABLE IF NOT EXISTS ab_investigation_changelog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER REFERENCES ab_investigations(id) ON DELETE CASCADE NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_type VARCHAR(50),
    change_summary TEXT,
    changed_by VARCHAR(255),
    previous_state TEXT
);

CREATE INDEX IF NOT EXISTS idx_ab_changelog_inv ON ab_investigation_changelog(investigation_id);
"""


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================

def create_ab_tables(connection, use_postgres: bool = True):
    """
    Execute table creation SQL for Investigation Builder tables.

    Args:
        connection: Database connection (SQLAlchemy connection object)
        use_postgres: True for PostgreSQL, False for SQLite
    """
    from sqlalchemy import text

    sql = CREATE_AB_TABLES_SQL if use_postgres else CREATE_AB_TABLES_SQLITE

    # Split by statement and execute each
    statements = [s.strip() for s in sql.split(';') if s.strip()]

    for statement in statements:
        # Remove SQL comments (lines starting with --)
        lines = statement.split('\n')
        non_comment_lines = [l for l in lines if not l.strip().startswith('--')]
        cleaned_statement = '\n'.join(non_comment_lines).strip()

        if not cleaned_statement:
            continue

        try:
            connection.execute(text(cleaned_statement))
            connection.commit()
        except Exception as e:
            connection.rollback()
            error_str = str(e).lower()
            if 'already exists' not in error_str and 'duplicate' not in error_str:
                print(f"Warning: Could not execute: {cleaned_statement[:50]}... Error: {e}")

    print(f"Investigation Builder tables created/verified ({'PostgreSQL' if use_postgres else 'SQLite'})")


def drop_ab_tables(connection):
    """Drop all Investigation Builder tables (use carefully!)"""
    from sqlalchemy import text

    tables = [
        "ab_investigation_changelog",
        "ab_rebuttal_evidence",
        "ab_counterarguments",
        "ab_evidence_credibility",
        "ab_source_credibility",
        "ab_evidence",
        "ab_claims",
        "ab_definitions",
        "ab_investigations",
    ]

    for table in tables:
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        except Exception as e:
            print(f"Warning: Could not drop {table}: {e}")

    print("Investigation Builder tables dropped")
