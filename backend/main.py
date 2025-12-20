"""
Wisdom Agent - FastAPI Backend

Main entry point for the Wisdom Agent API server.
Updated: Week 3 Day 3 - Auto-initialize services on startup
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
    Now includes auto-initialization of all services.
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
    
    # ============================================
    # AUTO-INITIALIZE SERVICES (Week 3 Day 3)
    # ============================================
    print("\n" + "-" * 40)
    print("Initializing Services...")
    print("-" * 40)
    
    # 1. Initialize LLM Router (required by other services)
    try:
        from backend.services.llm_router import get_llm_router
        llm_router = get_llm_router()
        print("✓ LLM Router initialized")
        print(f"  Active provider: {llm_router.active_provider}")
        print(f"  Available providers: {llm_router.get_available_providers()}")
    except Exception as e:
        print(f"⚠ LLM Router initialization failed: {e}")
        llm_router = None
    
    # 2. Initialize Memory Service
    try:
        from backend.services.memory_service import initialize_memory_service
        memory_service = initialize_memory_service()
        if memory_service:
            print("✓ Memory Service initialized (ChromaDB)")
        else:
            print("⚠ Memory Service not available (missing dependencies)")
    except Exception as e:
        print(f"⚠ Memory Service initialization failed: {e}")
    
    # 3. Initialize Reflection Service (requires LLM Router)
    if llm_router:
        try:
            from backend.services.reflection_service import initialize_reflection_service
            from backend.services.philosophy_loader import philosophy_loader
            
            # Load philosophy text for grounding
            philosophy_text = philosophy_loader.get_combined_philosophy()
            
            reflection_service = initialize_reflection_service(
                llm_router=llm_router,
                philosophy_text=philosophy_text
            )
            if reflection_service:
                print("✓ Reflection Service initialized")
        except Exception as e:
            print(f"⚠ Reflection Service initialization failed: {e}")
    else:
        print("⚠ Reflection Service skipped (no LLM Router)")
    
    # 4. Initialize Pedagogy Service (if it exists)
    try:
        from backend.services.pedagogy_service import initialize_pedagogy_service
        pedagogy_service = initialize_pedagogy_service(llm_router=llm_router)
        if pedagogy_service:
            print("✓ Pedagogy Service initialized")
    except ImportError:
        print("⚠ Pedagogy Service not found (optional)")
    except Exception as e:
        print(f"⚠ Pedagogy Service initialization failed: {e}")
    
    # 5. Initialize Conversation Service (for sessions)
    try:
        from backend.services.conversation_service import initialize_conversation_service
        conv_service = initialize_conversation_service(llm_router=llm_router)
        if conv_service:
            print("✓ Conversation Service initialized")
    except ImportError:
        print("⚠ Conversation Service not found")
    except Exception as e:
        print(f"⚠ Conversation Service initialization failed: {e}")
    
    # 6. Create default "Wisdom Sessions" project if it doesn't exist
    try:
        from backend.services.project_service import get_project_service
        project_service = get_project_service()
        
        # Check if Wisdom Sessions project exists
        existing = project_service.get_project("Wisdom Sessions")
        if not existing:
            project_service.create_project(
                name="Wisdom Sessions",
                project_type="wisdom",
                description="Default project for wisdom-focused conversations"
            )
            print("✓ Created default 'Wisdom Sessions' project")
        else:
            print("✓ Default 'Wisdom Sessions' project exists")
    except Exception as e:
        print(f"⚠ Could not create default project: {e}")
    
    print("-" * 40)
    print("Service initialization complete")
    print("-" * 40 + "\n")
    
    # ============================================
    
    print("=" * 60)
    print("🚀 Wisdom Agent Ready!")
    print(f"📍 Running at http://{config.HOST}:{config.PORT}")
    print("📚 API docs at http://{config.HOST}:{config.PORT}/docs")
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
    # Check service status
    services_status = {
        "api": True,
        "anthropic": config.ANTHROPIC_API_KEY is not None,
        "openai": config.OPENAI_API_KEY is not None,
        "nebius": config.NEBIUS_API_KEY is not None,
    }
    
    # Check if services are initialized
    try:
        from backend.services.memory_service import get_memory_service
        memory = get_memory_service()
        services_status["memory"] = memory is not None and memory._initialized
    except:
        services_status["memory"] = False
    
    try:
        from backend.services.reflection_service import get_reflection_service
        reflection = get_reflection_service()
        services_status["reflection"] = reflection is not None
    except:
        services_status["reflection"] = False
    
    try:
        from backend.services.conversation_service import get_conversation_service
        conv = get_conversation_service()
        services_status["conversation"] = conv is not None and conv.is_initialized()
    except:
        services_status["conversation"] = False
    
    return {
        "status": "healthy",
        "services": services_status,
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
from backend.routers.sessions import router as sessions_router
from backend.routers.projects import router as projects_router
from backend.routers.files import router as files_router
from backend.routers.pedagogy import router as pedagogy_router
from backend.routers.reflection import router as reflection_router
from backend.routers.review_router import router as review_router

app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(memory_router, tags=["Memory"])  # Already has /api/memory prefix
app.include_router(sessions_router, tags=["Sessions"])  # Already has /api/sessions prefix
app.include_router(projects_router, tags=["Projects"])  # Already has /api/projects prefix
app.include_router(files_router, tags=["Files"])  # Already has /api/files prefix
app.include_router(pedagogy_router, tags=["Pedagogy"])  # Already has /api/pedagogy prefix
app.include_router(reflection_router, tags=["Reflection"])  # Already has /api/reflection prefix
app.include_router(review_router)  # Already has /api/reviews prefix


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
