"""
Wisdom Agent - Database Connection Management

Handles PostgreSQL connection, session management, and pgvector setup.
SQLite fallback is available for testing when PostgreSQL is unavailable.

Updated 2025-12-30: Added sync_schema() to automatically add missing columns.
"""

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, StaticPool
from typing import Generator
import logging
import os

from backend.config import config

logger = logging.getLogger(__name__)

# Check if we should use SQLite
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

# Determine database URL
if USE_SQLITE:
    db_url = f"sqlite:///{config.SQLITE_PATH}"
    logger.info(f"📁 Using SQLite database: {config.SQLITE_PATH}")
    # Create SQLAlchemy engine for SQLite
    engine = create_engine(
        db_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=config.DEBUG,
    )
else:
    db_url = config.DATABASE_URL
    logger.info(f"🐘 Using PostgreSQL database")
    # Create SQLAlchemy engine for PostgreSQL
    engine = create_engine(
        db_url,
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
    Skipped when using SQLite.
    """
    if USE_SQLITE:
        logger.info("⭕ Skipping pgvector extension (SQLite mode)")
        return
        
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


def get_db_session() -> Session:
    """
    Get a database session directly (not as a generator).
    
    Used by repositories that manage their own session lifecycle.
    Caller is responsible for closing the session.
    
    Returns:
        Database session
    """
    return SessionLocal()


def sync_schema():
    """
    Synchronize database schema by adding any missing columns.
    
    This handles the case where models have been updated with new columns
    but existing databases don't have them. SQLAlchemy's create_all() only
    creates new tables, it doesn't add columns to existing tables.
    
    This function inspects all models and adds any missing columns.
    Safe to run multiple times (idempotent).
    """
    # Import models to ensure they're all registered
    from backend.database import models
    
    inspector = inspect(engine)
    
    # Get all tables defined in our models
    for table_name, table in Base.metadata.tables.items():
        # Check if table exists in database
        if not inspector.has_table(table_name):
            # Table doesn't exist, create_all will handle it
            continue
        
        # Get existing columns in database
        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
        
        # Get columns defined in model
        model_columns = {col.name for col in table.columns}
        
        # Find missing columns
        missing_columns = model_columns - existing_columns
        
        if missing_columns:
            logger.info(f"📊 Table '{table_name}' missing columns: {missing_columns}")
            
            # Add each missing column
            with engine.connect() as conn:
                for col_name in missing_columns:
                    col = table.columns[col_name]
                    
                    # Determine SQL type
                    col_type = _get_sql_type(col)
                    
                    # Build ALTER TABLE statement
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    default = ""
                    if col.default is not None:
                        default = f" DEFAULT {_get_default_value(col)}"
                    
                    # For NOT NULL columns without defaults, we need to allow NULL first
                    # then update, then set NOT NULL (if there's existing data)
                    if not col.nullable and col.default is None:
                        # Add as nullable first to handle existing rows
                        sql = f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col_name}" {col_type} NULL'
                    else:
                        sql = f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col_name}" {col_type} {nullable}{default}'
                    
                    try:
                        conn.execute(text(sql))
                        conn.commit()
                        logger.info(f"  ✅ Added column '{col_name}' to '{table_name}'")
                    except Exception as e:
                        logger.warning(f"  ⚠️  Could not add column '{col_name}': {e}")


def _get_sql_type(column) -> str:
    """Convert SQLAlchemy column type to SQL type string."""
    from sqlalchemy import Integer, String, Text, Boolean, Float, DateTime, JSON, Enum, LargeBinary
    
    col_type = type(column.type)
    
    if col_type == Integer:
        return "INTEGER"
    elif col_type == String:
        length = getattr(column.type, 'length', 255) or 255
        return f"VARCHAR({length})"
    elif col_type == Text:
        return "TEXT"
    elif col_type == Boolean:
        return "BOOLEAN"
    elif col_type == Float:
        return "FLOAT"
    elif col_type == DateTime:
        return "TIMESTAMP"
    elif col_type == JSON:
        return "JSON" if not USE_SQLITE else "TEXT"
    elif col_type == LargeBinary:
        return "BYTEA" if not USE_SQLITE else "BLOB"
    elif hasattr(column.type, 'impl'):
        # Handle Enum types
        return "VARCHAR(100)"
    else:
        # Default fallback
        return "TEXT"


def _get_default_value(column) -> str:
    """Get SQL default value for a column."""
    if column.default is None:
        return "NULL"
    
    default = column.default.arg
    if callable(default):
        return "NULL"  # Can't translate Python functions to SQL defaults
    elif isinstance(default, bool):
        return "TRUE" if default else "FALSE"
    elif isinstance(default, (int, float)):
        return str(default)
    elif isinstance(default, str):
        return f"'{default}'"
    else:
        return "NULL"


def init_database():
    """
    Initialize the database schema.
    
    Creates all tables defined in models.py if they don't exist,
    then syncs schema to add any missing columns.
    Also ensures a default user exists for the application.
    Should be called on application startup.
    """
    try:
        # Import all models here to ensure they're registered
        from backend.database import models
        
        # Enable pgvector extension
        init_pgvector_extension()
        
        # Create all tables (only creates new tables, doesn't modify existing)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized")
        
        # Sync schema to add any missing columns to existing tables
        sync_schema()
        logger.info("✅ Database schema synchronized")
        
        # Ensure default user exists
        _ensure_default_user()
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False


def _ensure_default_user():
    """
    Ensure a default user exists in the database.
    
    Many parts of the app currently use user_id=1 as a placeholder
    until proper authentication is implemented. This function ensures
    that user exists so foreign key constraints don't fail.
    """
    try:
        from backend.database.models import User
        
        session = SessionLocal()
        try:
            # Check if user with ID 1 exists
            user = session.query(User).filter(User.id == 1).first()
            
            if not user:
                # Create default user
                default_user = User(
                    id=1,
                    username="default_user",
                    email="default@wisdomagent.local",
                    hashed_password="not_a_real_password",  # Placeholder
                    full_name="Default User",
                    is_active=True,
                    is_verified=True,
                )
                session.add(default_user)
                session.commit()
                logger.info("✅ Created default user (id=1)")
            else:
                logger.info("✅ Default user exists")
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"⚠️  Could not ensure default user: {e}")


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
