#!/usr/bin/env python3
"""
Wisdom Agent - Database Setup & Testing Script

Run this to:
1. Test database connection
2. Initialize pgvector extension
3. Create all tables
4. Optionally seed test data

Usage:
    python -m backend.database.setup_db
    python -m backend.database.setup_db --seed-test-data
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import init_database, check_database_connection
from backend.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main setup function."""
    logger.info("=" * 60)
    logger.info("Wisdom Agent - Database Setup")
    logger.info("=" * 60)
    
    # Show configuration
    logger.info(f"Database URL: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else config.DATABASE_URL}")
    logger.info(f"Vector Dimension: {config.VECTOR_DIMENSION}")
    
    # Step 1: Test connection
    logger.info("\n📡 Testing database connection...")
    if not check_database_connection():
        logger.error("❌ Database connection failed!")
        logger.error("Make sure PostgreSQL is running:")
        logger.error("  docker-compose up -d")
        return False
    logger.info("✅ Database connection successful!")
    
    # Step 2: Initialize database (create tables)
    logger.info("\n🏗️  Initializing database schema...")
    if not init_database():
        logger.error("❌ Database initialization failed!")
        return False
    logger.info("✅ Database initialized!")
    
    # Step 3: Seed test data (optional)
    if "--seed-test-data" in sys.argv:
        logger.info("\n🌱 Seeding test data...")
        seed_test_data()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Database setup complete!")
    logger.info("=" * 60)
    
    return True


def seed_test_data():
    """Seed database with test data (optional)."""
    from backend.database import SessionLocal
    from backend.database.models import User, Project, SessionType
    from datetime import datetime
    
    db = SessionLocal()
    try:
        # Check if test user already exists
        existing_user = db.query(User).filter(User.username == "test_user").first()
        if existing_user:
            logger.info("Test data already exists, skipping...")
            return
        
        # Create test user
        test_user = User(
            username="test_user",
            email="test@wisdomagent.dev",
            hashed_password="not_a_real_hash",  # In production, use proper hashing
            full_name="Test User",
            is_active=True,
            is_verified=True,
        )
        db.add(test_user)
        db.flush()  # Get the user ID
        
        # Create test project
        test_project = Project(
            name="Test Spanish Learning",
            slug="test_spanish_learning",
            description="A test project for learning Spanish",
            session_type=SessionType.LANGUAGE_LEARNING,
            subject="Spanish",
            current_level="Beginner",
            learning_goal="Conversational fluency",
            time_commitment="30 min/day",
            user_id=test_user.id,
        )
        db.add(test_project)
        
        db.commit()
        logger.info("✅ Test data seeded successfully!")
        logger.info(f"   - Test user: {test_user.username}")
        logger.info(f"   - Test project: {test_project.name}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to seed test data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
