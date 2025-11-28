"""
Wisdom Agent - FastAPI Backend

Main entry point for the Wisdom Agent API server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print("=" * 60)
    print("🧠 Wisdom Agent Starting...")
    print("=" * 60)
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Log configuration
    print(f"📁 Data directory: {config.DATA_DIR}")
    print(f"📚 Philosophy base: {config.PHILOSOPHY_BASE}")
    
    # Check API keys
    if config.ANTHROPIC_API_KEY:
        print("✓ Anthropic API key configured")
    else:
        print("⚠ Anthropic API key not set")
    
    if config.OPENAI_API_KEY:
        print("✓ OpenAI API key configured")
    
    if config.NEBIUS_API_KEY:
        print("✓ Nebius API key configured")
    
    print("=" * 60)
    print("🚀 Wisdom Agent Ready!")
    print(f"📍 Running at http://{config.HOST}:{config.PORT}")
    print("=" * 60)
    
    yield  # Server runs here
    
    # Shutdown
    print("\n" + "=" * 60)
    print("🧠 Wisdom Agent Shutting Down...")
    print("=" * 60)


# Create FastAPI app
app = FastAPI(
    title="Wisdom Agent",
    description="""
    An AI system designed to help individuals and groups grow in wisdom.
    
    Grounded in Something Deeperism philosophy:
    - Poetic (not literal) relation to Truth
    - Pure Love = Reality
    - 7 Universal Values: Awareness, Honesty, Accuracy, Competence, 
      Compassion, Loving-kindness, Joyful-sharing
    
    Core Questions:
    1. How can AI best help humans select for wisdom?
    2. How can AI pursue this without overstepping?
    """,
    version="2.0.0",
    lifespan=lifespan,
)


# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - basic health check."""
    return {
        "status": "healthy",
        "service": "Wisdom Agent",
        "version": "2.0.0",
        "philosophy": "Something Deeperism",
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "api": True,
            "anthropic": config.ANTHROPIC_API_KEY is not None,
            "openai": config.OPENAI_API_KEY is not None,
            "nebius": config.NEBIUS_API_KEY is not None,
        },
        "paths": {
            "data_exists": config.DATA_DIR.exists(),
            "philosophy_exists": config.PHILOSOPHY_BASE.exists(),
        }
    }


@app.get("/philosophy")
async def get_philosophy_info():
    """Get information about loaded philosophy."""
    from backend.services.philosophy_loader import philosophy_loader
    
    return {
        "base_files": [f.name for f in config.get_philosophy_files("base")],
        "available_domains": philosophy_loader.get_available_domains(),
        "available_organizations": philosophy_loader.get_available_organizations(),
    }


# Include routers
from backend.routers.chat import router as chat_router
from backend.routers.memory import router as memory_router
from backend.routers.projects import router as projects_router
from backend.routers.files import router as files_router
from backend.routers.pedagogy import router as pedagogy_router
from backend.routers.reflection import router as reflection_router

app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(memory_router, tags=["Memory"])  # Already has /api/memory prefix
app.include_router(projects_router, tags=["Projects"])  # Already has /api/projects prefix
app.include_router(files_router, tags=["Files"])  # Already has /api/files prefix
app.include_router(pedagogy_router, tags=["Pedagogy"])  # Already has /api/pedagogy prefix
app.include_router(reflection_router, tags=["Reflection"])  # Already has /api/reflection prefix


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
