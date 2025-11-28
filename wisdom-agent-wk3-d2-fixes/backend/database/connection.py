"""
Wisdom Agent - Database Connection Management

Handles PostgreSQL connection, session management, and pgvector setup.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
import logging

from backend.config import config

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    config.DATABASE_URL,
    poolclass=NullPool,  # Start with no connection pooling for simplicity
    echo=config.DEBUG,   # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def init_pgvector_extension():
    """
    Initialize the pgvector extension in PostgreSQL.
    
    This must be run with superuser privileges or by a user with CREATE EXTENSION permission.
    """
    try:
        with engine.connect() as conn:
            # Enable pgvector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("✅ pgvector extension enabled")
    except Exception as e:
        logger.warning(f"⚠️  Could not enable pgvector extension: {e}")
        logger.warning("You may need to run this as a database superuser")


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.
    
    Usage in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """
    Initialize the database schema.
    
    Creates all tables defined in models.py if they don't exist.
    Should be called on application startup.
    """
    try:
        # Import all models here to ensure they're registered
        from backend.database import models
        
        # Enable pgvector extension
        init_pgvector_extension()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# Event listener to set up connection
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Configure connection on connect."""
    logger.debug("Database connection established")
