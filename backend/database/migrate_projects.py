"""
Wisdom Agent - Project Migration Script

Migrates file-based projects to PostgreSQL database.

This script:
1. Scans the data/projects directory for project.json files
2. Creates corresponding database entries
3. Preserves all project metadata and settings
4. Can run in dry-run mode for testing

Author: Wisdom Agent Team
Date: 2025-11-24
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from backend.config import config
from backend.services.project_repository import get_project_repository
from backend.database.models import SessionType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectMigration:
    """Handles migration of file-based projects to PostgreSQL."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize migration.
        
        Args:
            dry_run: If True, only simulate migration without making changes
        """
        self.dry_run = dry_run
        self.project_repo = get_project_repository()
        self.stats = {
            "total_projects": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0
        }
    
    def initialize(self) -> bool:
        """Initialize database connection."""
        if self.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info("=" * 60)
        
        if not self.project_repo.initialize():
            logger.error("Failed to initialize project repository")
            return False
        
        return True
    
    def find_projects(self) -> List[Path]:
        """
        Find all project.json files in the projects directory.
        
        Returns:
            List of paths to project.json files
        """
        projects_dir = config.PROJECTS_DIR
        if not projects_dir.exists():
            logger.warning(f"Projects directory not found: {projects_dir}")
            return []
        
        project_files = []
        for item in projects_dir.iterdir():
            if item.is_dir():
                project_json = item / "project.json"
                if project_json.exists():
                    project_files.append(project_json)
        
        logger.info(f"Found {len(project_files)} project(s) to process")
        return project_files
    
    def load_project_json(self, project_path: Path) -> Optional[Dict]:
        """
        Load project data from JSON file.
        
        Args:
            project_path: Path to project.json file
            
        Returns:
            Dict with project data or None if error
        """
        try:
            with open(project_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {project_path}: {e}")
            return None
    
    def map_session_type(self, project_type: str) -> SessionType:
        """
        Map file-based project type to database SessionType enum.
        
        Args:
            project_type: Project type string
            
        Returns:
            SessionType enum value
        """
        type_mapping = {
            "learning": SessionType.GENERAL,
            "language_learning": SessionType.LANGUAGE_LEARNING,
            "technical_learning": SessionType.TECHNICAL_LEARNING,
            "creative_writing": SessionType.CREATIVE_WRITING,
            "research": SessionType.GENERAL,
            "wisdom": SessionType.PHILOSOPHY,
            "reflection": SessionType.REFLECTION,
            "philosophy": SessionType.PHILOSOPHY
        }
        return type_mapping.get(project_type.lower(), SessionType.GENERAL)
    
    def project_exists(self, user_id: int, slug: str) -> bool:
        """
        Check if project already exists in database.
        
        Args:
            user_id: User ID
            slug: Project slug
            
        Returns:
            bool: True if project exists
        """
        try:
            existing = self.project_repo.get_project_by_slug(user_id, slug)
            return existing is not None
        except Exception as e:
            logger.error(f"Error checking if project exists: {e}")
            return False
    
    def migrate_project(self, project_data: Dict, user_id: int = 1) -> bool:
        """
        Migrate a single project to database.
        
        Args:
            project_data: Project data dictionary
            user_id: User ID (default: 1 for single-user mode)
            
        Returns:
            bool: True if successful
        """
        try:
            name = project_data.get('name', 'Unknown Project')
            slug = name.lower().replace(' ', '_').replace('-', '_')
            
            # Check if already exists
            if self.project_exists(user_id, slug):
                logger.info(f"  ⏭  Project '{name}' already exists (skipping)")
                self.stats["skipped"] += 1
                return True
            
            # Extract project metadata
            description = project_data.get('description', '')
            project_type = project_data.get('type', 'learning')
            session_type = self.map_session_type(project_type)
            
            # Extract learning plan data
            learning_plan = project_data.get('learning_plan')
            subject = None
            learning_goal = None
            current_level = None
            time_commitment = None
            
            if learning_plan:
                subject = learning_plan.get('subject')
                learning_goal = learning_plan.get('learning_goal')
                current_level = learning_plan.get('current_level')
                time_commitment = learning_plan.get('time_commitment')
            
            if self.dry_run:
                logger.info(f"  [DRY RUN] Would create project:")
                logger.info(f"    Name: {name}")
                logger.info(f"    Slug: {slug}")
                logger.info(f"    Type: {session_type.value}")
                logger.info(f"    Subject: {subject}")
                logger.info(f"    Learning Goal: {learning_goal}")
                self.stats["migrated"] += 1
                return True
            
            # Create project in database
            project = self.project_repo.create_project(
                name=name,
                user_id=user_id,
                slug=slug,
                description=description,
                session_type=session_type,
                subject=subject,
                current_level=current_level,
                learning_goal=learning_goal,
                time_commitment=time_commitment,
                philosophy_overlay=project_data.get('philosophy_overlay'),
            )
            
            if not project:
                logger.error(f"  ❌ Failed to create project '{name}'")
                self.stats["errors"] += 1
                return False
            
            # Update learning plan if present
            if learning_plan:
                self.project_repo.update_learning_plan(project.id, learning_plan)
            
            logger.info(f"  âœ… Migrated project '{name}' (ID: {project.id})")
            self.stats["migrated"] += 1
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Error migrating project: {e}")
            self.stats["errors"] += 1
            return False
    
    def run(self, user_id: int = 1) -> Dict[str, int]:
        """
        Run the migration process.
        
        Args:
            user_id: User ID for all projects (default: 1)
            
        Returns:
            Dict with migration statistics
        """
        logger.info("=" * 60)
        logger.info("Project Migration to PostgreSQL")
        logger.info("=" * 60)
        
        # Initialize
        if not self.initialize():
            logger.error("Failed to initialize")
            return self.stats
        
        # Find projects
        project_files = self.find_projects()
        if not project_files:
            logger.warning("No projects found to migrate")
            return self.stats
        
        self.stats["total_projects"] = len(project_files)
        
        # Migrate each project
        logger.info(f"\nMigrating {len(project_files)} project(s)...\n")
        
        for project_file in project_files:
            logger.info(f"Processing: {project_file.parent.name}")
            project_data = self.load_project_json(project_file)
            
            if project_data:
                self.migrate_project(project_data, user_id)
            else:
                self.stats["errors"] += 1
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Migration Complete")
        logger.info("=" * 60)
        logger.info(f"Total projects found: {self.stats['total_projects']}")
        logger.info(f"Successfully migrated: {self.stats['migrated']}")
        logger.info(f"Skipped (already exist): {self.stats['skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("\nThis was a DRY RUN - no changes were made to the database")
        
        return self.stats


def main():
    """Main entry point for migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate file-based projects to PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no changes made)"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="User ID for all projects (default: 1)"
    )
    
    args = parser.parse_args()
    
    migration = ProjectMigration(dry_run=args.dry_run)
    stats = migration.run(user_id=args.user_id)
    
    # Exit with error code if there were errors
    if stats["errors"] > 0:
        exit(1)


if __name__ == "__main__":
    main()
