"""
Wisdom Agent - Fact Checker Database Migration

Run this script to create the fact checker tables in your database.
This adds to the existing Wisdom Agent database schema.

Usage:
    python -m backend.database.migrations.create_fact_check_tables

Author: Wisdom Agent Team
Date: 2025-12-18
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from backend.database.connection import engine, init_database
from backend.database.models import Base

# Import the new fact checker models so they're registered with Base
from backend.database.fact_check_models import (
    ContentReview, SourceMetadata, ExtractedClaim,
    FactCheckResult, LogicAnalysis, WisdomEvaluation
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create the fact checker tables."""
    logger.info("=" * 60)
    logger.info("FACT CHECKER DATABASE MIGRATION")
    logger.info("=" * 60)
    
    try:
        # Initialize database connection
        logger.info("Connecting to database...")
        init_database()
        
        # Create tables that don't exist yet
        logger.info("Creating fact checker tables...")
        
        # Get list of tables to create
        tables_to_create = [
            ContentReview.__table__,
            SourceMetadata.__table__,
            ExtractedClaim.__table__,
            FactCheckResult.__table__,
            LogicAnalysis.__table__,
            WisdomEvaluation.__table__,
        ]
        
        for table in tables_to_create:
            table_name = table.name
            
            # Check if table already exists
            with engine.connect() as conn:
                result = conn.execute(text(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
                ))
                exists = result.scalar()
                
                if exists:
                    logger.info(f"  ✓ Table '{table_name}' already exists")
                else:
                    # Create the table
                    table.create(engine, checkfirst=True)
                    logger.info(f"  ✓ Created table '{table_name}'")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("MIGRATION COMPLETE!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Tables created:")
        logger.info("  - content_reviews (main fact check records)")
        logger.info("  - source_metadata (source information)")
        logger.info("  - extracted_claims (individual claims)")
        logger.info("  - fact_check_results (verification results)")
        logger.info("  - logic_analyses (logical analysis)")
        logger.info("  - wisdom_evaluations (7 Values + SD assessment)")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Update your existing models.py to add relationships")
        logger.info("  2. Run Day 2 tasks to create Pydantic models")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.exception("Full traceback:")
        return False


def run_migration_sqlite():
    """Create tables for SQLite (simpler, no information_schema)."""
    logger.info("=" * 60)
    logger.info("FACT CHECKER DATABASE MIGRATION (SQLite)")
    logger.info("=" * 60)
    
    try:
        # Initialize database connection
        logger.info("Connecting to database...")
        init_database()
        
        # Create all tables (SQLite version)
        logger.info("Creating fact checker tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("MIGRATION COMPLETE!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.exception("Full traceback:")
        return False


if __name__ == "__main__":
    import os
    
    # Check if using SQLite
    use_sqlite = os.environ.get("USE_SQLITE", "false").lower() == "true"
    
    if use_sqlite:
        success = run_migration_sqlite()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
