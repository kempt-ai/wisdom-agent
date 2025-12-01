"""
Wisdom Agent - Configuration Management

Central configuration for all paths, settings, and environment variables.
Updated: Week 3 Day 3 - Fixed Nebius configuration
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent  # wisdom-agent/
    BACKEND_DIR = Path(__file__).parent       # wisdom-agent/backend/
    DATA_DIR = BASE_DIR / "data"
    CONFIG_DIR = BASE_DIR / "config"
    
    # Philosophy paths (layered system)
    PHILOSOPHY_DIR = DATA_DIR / "philosophy"
    PHILOSOPHY_BASE = PHILOSOPHY_DIR / "base"           # Something Deeperism core
    PHILOSOPHY_DOMAINS = PHILOSOPHY_DIR / "domains"     # democracy/, corporate/, etc.
    PHILOSOPHY_ORGS = PHILOSOPHY_DIR / "organizations"  # org-specific overlays
    
    # Data paths
    CONVERSATIONS_DIR = DATA_DIR / "conversations"
    PROJECTS_DIR = DATA_DIR / "projects"
    UPLOADS_DIR = DATA_DIR / "uploads"
    EXPORTS_DIR = DATA_DIR / "exports"
    KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
    
    # LLM Configuration
    LLM_CONFIG_FILE = CONFIG_DIR / "llm_providers.json"
    
    # Database (Week 2 - PostgreSQL + pgvector)
    DB_USER: str = os.getenv("DB_USER", "wisdom_agent")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "wisdom_dev_pass")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "wisdom_agent_db")
    
    # SQLite fallback for testing when PostgreSQL unavailable
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() == "true"
    SQLITE_PATH: Path = DATA_DIR / "wisdom_agent.db"
    
    # Construct DATABASE_URL from components if not directly provided
    @classmethod
    def get_database_url(cls) -> str:
        """Get the database URL, with SQLite fallback."""
        if cls.USE_SQLITE:
            return f"sqlite:///{cls.SQLITE_PATH}"
        return os.getenv(
            "DATABASE_URL",
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    # Vector settings for pgvector
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "384"))  # all-MiniLM-L6-v2
    
    # Vector DB (ChromaDB for now, PostgreSQL+pgvector in Week 2)
    CHROMA_PERSIST_DIR = DATA_DIR / "memory" / "vector_db"
    
    # API Keys (from environment)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    NEBIUS_API_KEY: Optional[str] = os.getenv("NEBIUS_API_KEY")
    
    # Nebius Configuration (Updated Week 3 Day 3)
    # The API endpoint changed - now uses tokenfactory
    NEBIUS_BASE_URL: str = os.getenv(
        "NEBIUS_BASE_URL", 
        "https://api.studio.nebius.com/v1"  # Updated URL
    )
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Session settings
    DEFAULT_MAX_TOKENS: int = 4096
    DEFAULT_TEMPERATURE: float = 1.0
    
    @classmethod
    def ensure_directories(cls):
        """Create all necessary directories if they don't exist."""
        directories = [
            cls.DATA_DIR,
            cls.PHILOSOPHY_BASE,
            cls.PHILOSOPHY_DOMAINS,
            cls.PHILOSOPHY_ORGS,
            cls.CONVERSATIONS_DIR,
            cls.PROJECTS_DIR,
            cls.UPLOADS_DIR,
            cls.EXPORTS_DIR,
            cls.KNOWLEDGE_BASE_DIR,
            cls.CONFIG_DIR,
            cls.CHROMA_PERSIST_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_philosophy_files(cls, layer: str = "base") -> list[Path]:
        """
        Get philosophy files for a specific layer.
        
        Args:
            layer: 'base', 'domains', or 'organizations'
            
        Returns:
            List of Path objects for .txt files in that layer
        """
        layer_paths = {
            "base": cls.PHILOSOPHY_BASE,
            "domains": cls.PHILOSOPHY_DOMAINS,
            "organizations": cls.PHILOSOPHY_ORGS,
        }
        
        layer_path = layer_paths.get(layer)
        if not layer_path or not layer_path.exists():
            return []
        
        return list(layer_path.glob("*.txt"))


# Create a singleton config instance
config = Config()

# Ensure directories exist on import
config.ensure_directories()
