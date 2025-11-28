"""
Wisdom Agent Services

All backend services for the Wisdom Agent platform.
"""

from backend.services.philosophy_loader import (
    PhilosophyLoader,
    philosophy_loader,
    get_base_philosophy,
    get_philosophy_context,
)

from backend.services.llm_router import (
    LLMRouter,
    LLMProvider,
    initialize_llm_router,
    get_llm_router,
)

from backend.services.memory_service import (
    MemoryService,
    initialize_memory_service,
    get_memory_service,
    memory_dependencies_available,
)

from backend.services.project_service import (
    Project,
    ProjectService,
    initialize_project_service,
    get_project_service,
)

from backend.services.file_service import (
    FileService,
    initialize_file_service,
    get_file_service,
)

from backend.services.pedagogy_service import (
    PedagogyService,
    initialize_pedagogy_service,
    get_pedagogy_service,
)

from backend.services.reflection_service import (
    ReflectionService,
    initialize_reflection_service,
    get_reflection_service,
)

__all__ = [
    # Philosophy
    "PhilosophyLoader",
    "philosophy_loader", 
    "get_base_philosophy",
    "get_philosophy_context",
    # LLM
    "LLMRouter",
    "LLMProvider",
    "initialize_llm_router",
    "get_llm_router",
    # Memory
    "MemoryService",
    "initialize_memory_service",
    "get_memory_service",
    "memory_dependencies_available",
    # Projects
    "Project",
    "ProjectService",
    "initialize_project_service",
    "get_project_service",
    # Files
    "FileService",
    "initialize_file_service",
    "get_file_service",
    # Pedagogy
    "PedagogyService",
    "initialize_pedagogy_service",
    "get_pedagogy_service",
    # Reflection
    "ReflectionService",
    "initialize_reflection_service",
    "get_reflection_service",
]
