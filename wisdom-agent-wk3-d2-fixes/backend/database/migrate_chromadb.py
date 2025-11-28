#!/usr/bin/env python3
"""
Wisdom Agent - ChromaDB to PostgreSQL Migration Script

Migrates existing memory embeddings from ChromaDB to PostgreSQL + pgvector.

Usage:
    python -m backend.database.migrate_chromadb
    python -m backend.database.migrate_chromadb --user-id 1 --dry-run
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import config
from backend.services.pg_memory_repository import PostgresMemoryRepository

# Try to import ChromaDB
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None
    SentenceTransformer = None
    CHROMADB_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChromaDBMigrator:
    """Migrates memories from ChromaDB to PostgreSQL."""
    
    def __init__(self, chroma_path: Optional[str] = None, default_user_id: int = 1):
        """
        Initialize migrator.
        
        Args:
            chroma_path: Path to ChromaDB storage (uses config default if not provided)
            default_user_id: User ID to assign to migrated memories
        """
        self.chroma_path = chroma_path or str(config.CHROMA_PERSIST_DIR)
        self.default_user_id = default_user_id
        self.chroma_client = None
        self.chroma_collection = None
        self.pg_repo = None
    
    def initialize(self) -> bool:
        """
        Initialize both ChromaDB and PostgreSQL connections.
        
        Returns:
            True if successful, False otherwise
        """
        if not CHROMADB_AVAILABLE:
            logger.error("ChromaDB not available. Install with: pip install chromadb")
            return False
        
        try:
            # Initialize ChromaDB client
            logger.info(f"Connecting to ChromaDB at: {self.chroma_path}")
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            
            # Get the collection
            collections = self.chroma_client.list_collections()
            if not collections:
                logger.warning("No collections found in ChromaDB")
                return False
            
            # Use the first collection (typically 'wisdom_sessions')
            collection_name = collections[0].name
            logger.info(f"Found collection: {collection_name}")
            self.chroma_collection = self.chroma_client.get_collection(collection_name)
            
            # Initialize PostgreSQL repository
            logger.info("Initializing PostgreSQL repository...")
            self.pg_repo = PostgresMemoryRepository()
            if not self.pg_repo.initialize():
                logger.error("Failed to initialize PostgreSQL repository")
                return False
            
            logger.info("✅ Both databases initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def count_chroma_memories(self) -> int:
        """
        Count total memories in ChromaDB.
        
        Returns:
            Number of memories
        """
        try:
            count = self.chroma_collection.count()
            return count
        except Exception as e:
            logger.error(f"Error counting ChromaDB memories: {e}")
            return 0
    
    def get_all_chroma_memories(self) -> Dict:
        """
        Get all memories from ChromaDB.
        
        Returns:
            Dictionary with ids, documents, embeddings, metadatas
        """
        try:
            # Get all documents
            results = self.chroma_collection.get(include=['embeddings', 'metadatas', 'documents'])
            return results
        except Exception as e:
            logger.error(f"Error retrieving ChromaDB memories: {e}")
            return {'ids': [], 'documents': [], 'embeddings': [], 'metadatas': []}
    
    def migrate_memory(
        self,
        content: str,
        embedding: List[float],
        metadata: Dict,
        embedding_id: str
    ) -> Optional[int]:
        """
        Migrate a single memory to PostgreSQL.
        
        Args:
            content: Memory content
            embedding: Vector embedding
            metadata: Memory metadata
            embedding_id: Original ChromaDB ID
            
        Returns:
            New PostgreSQL memory ID, or None if failed
        """
        try:
            # Extract session_id and project from metadata
            session_id = metadata.get('session_id')
            project_name = metadata.get('project')
            
            # For now, we don't have project_id, so we'll store None
            # In a real migration, we'd look up or create projects first
            project_id = None
            
            # Store in PostgreSQL
            from backend.database.connection import SessionLocal
            from backend.database.models import Memory
            
            db = SessionLocal()
            try:
                pg_memory = Memory(
                    content=content,
                    embedding=embedding,
                    user_id=self.default_user_id,
                    session_id=session_id,
                    project_id=project_id,
                    meta_data=metadata
                )
                db.add(pg_memory)
                db.commit()
                db.refresh(pg_memory)
                return pg_memory.id
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error migrating memory {embedding_id}: {e}")
            return None
    
    def migrate_all(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Migrate all memories from ChromaDB to PostgreSQL.
        
        Args:
            dry_run: If True, don't actually write to PostgreSQL
            
        Returns:
            Dictionary with migration statistics
        """
        logger.info("=" * 60)
        logger.info("ChromaDB → PostgreSQL Migration")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be written")
        
        # Count memories
        total_count = self.count_chroma_memories()
        logger.info(f"Found {total_count} memories in ChromaDB")
        
        if total_count == 0:
            logger.info("No memories to migrate")
            return {'total': 0, 'migrated': 0, 'failed': 0}
        
        # Get all memories
        logger.info("Retrieving all memories from ChromaDB...")
        chroma_data = self.get_all_chroma_memories()
        
        ids = chroma_data['ids']
        documents = chroma_data['documents']
        embeddings = chroma_data['embeddings']
        metadatas = chroma_data['metadatas']
        
        logger.info(f"Retrieved {len(ids)} memories")
        
        # Migrate each memory
        migrated = 0
        failed = 0
        
        for i, (embedding_id, content, embedding, metadata) in enumerate(
            zip(ids, documents, embeddings, metadatas), 1
        ):
            logger.info(f"Migrating {i}/{len(ids)}: {embedding_id}")
            
            if dry_run:
                logger.info(f"  Content preview: {content[:100]}...")
                logger.info(f"  Metadata: {metadata}")
                migrated += 1
            else:
                pg_id = self.migrate_memory(content, embedding, metadata, embedding_id)
                if pg_id:
                    logger.info(f"  ✅ Migrated to PostgreSQL ID: {pg_id}")
                    migrated += 1
                else:
                    logger.error(f"  ❌ Failed to migrate")
                    failed += 1
        
        # Summary
        logger.info("=" * 60)
        logger.info("Migration Complete!")
        logger.info("=" * 60)
        logger.info(f"Total memories: {total_count}")
        logger.info(f"Successfully migrated: {migrated}")
        logger.info(f"Failed: {failed}")
        
        if dry_run:
            logger.info("\n⚠️  This was a DRY RUN. Run without --dry-run to actually migrate.")
        else:
            logger.info("\n✅ Migration complete! Your memories are now in PostgreSQL.")
            logger.info("You can now use the hybrid memory service with PostgreSQL backend.")
        
        return {
            'total': total_count,
            'migrated': migrated,
            'failed': failed
        }


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate memories from ChromaDB to PostgreSQL"
    )
    parser.add_argument(
        '--user-id',
        type=int,
        default=1,
        help='User ID to assign to migrated memories (default: 1)'
    )
    parser.add_argument(
        '--chroma-path',
        type=str,
        default=None,
        help='Path to ChromaDB storage (default: from config)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without writing to PostgreSQL'
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = ChromaDBMigrator(
        chroma_path=args.chroma_path,
        default_user_id=args.user_id
    )
    
    # Initialize
    if not migrator.initialize():
        logger.error("Failed to initialize migrator")
        sys.exit(1)
    
    # Migrate
    try:
        stats = migrator.migrate_all(dry_run=args.dry_run)
        
        # Exit with error if any migrations failed
        if stats['failed'] > 0 and not args.dry_run:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
