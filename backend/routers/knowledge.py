"""
Knowledge Base API Router

REST endpoints for:
- Collection CRUD
- Resource CRUD
- Indexing with cost estimation
- Search
- Character extraction
- Author voice profiles
- Project integration
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from pydantic import BaseModel
from sqlalchemy import text
from typing import Optional, List
import logging

from backend.models.knowledge_models import (
    # Collections
    Collection, CollectionCreate, CollectionUpdate, CollectionSummary,
    # Resources
    Resource, ResourceCreate, ResourceUpdate, ResourceSummary,
    ResourceType, SourceType,
    # Indexing
    ResourceIndex, IndexEstimate, IndexRequest, IndexResult,
    IndexLevel, IndexType,
    # Characters & Authors
    CharacterProfile, CharacterProfileCreate,
    AuthorVoice, AuthorVoiceCreate,
    # Search
    SearchQuery, SearchResponse,
    # Project
    ProjectKnowledgeSettings,
    # Utility
    TokenEstimate, BulkOperationResult
)

from backend.services.knowledge_service import (
    get_knowledge_service,
    KnowledgeBaseError,
    CollectionNotFoundError,
    ResourceNotFoundError,
    BudgetExceededError,
    IndexingError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_user_id() -> int:
    """
    Get current user ID from auth context.
    TODO: Replace with actual authentication.
    """
    return 1  # Default user for development


# ============================================================================
# COLLECTIONS
# ============================================================================

@router.post("/collections", response_model=Collection, status_code=201)
async def create_collection(
    data: CollectionCreate,
    user_id: int = Depends(get_user_id)
):
    """
    Create a new knowledge collection.
    
    Collections organize related resources (documents, books, articles, etc.)
    by topic, project, or purpose.
    """
    try:
        service = get_knowledge_service()
        return await service.create_collection(user_id, data)
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=List[CollectionSummary])
async def list_collections(
    project_id: Optional[int] = Query(None, description="Filter by project"),
    collection_type: Optional[str] = Query(None, description="Filter by type"),
    user_id: int = Depends(get_user_id)
):
    """
    List user's knowledge collections.
    
    Optionally filter by project or collection type.
    """
    try:
        service = get_knowledge_service()
        return await service.list_collections(user_id, project_id, collection_type)
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_id}", response_model=Collection)
async def get_collection(
    collection_id: int,
    user_id: int = Depends(get_user_id)
):
    """Get a collection by ID with resource counts."""
    try:
        service = get_knowledge_service()
        return await service.get_collection(collection_id, user_id)
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except Exception as e:
        logger.error(f"Failed to get collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/collections/{collection_id}", response_model=Collection)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    user_id: int = Depends(get_user_id)
):
    """Update a collection's properties."""
    try:
        service = get_knowledge_service()
        return await service.update_collection(collection_id, user_id, data)
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except Exception as e:
        logger.error(f"Failed to update collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    Delete a collection and all its resources.
    
    ⚠️ This is irreversible!
    """
    try:
        service = get_knowledge_service()
        await service.delete_collection(collection_id, user_id)
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RESOURCES
# ============================================================================

@router.post("/collections/{collection_id}/resources", response_model=Resource, status_code=201)
async def add_resource(
    collection_id: int,
    data: ResourceCreate,
    user_id: int = Depends(get_user_id)
):
    """
    Add a resource to a collection.
    
    Resources can be added via:
    - **text**: Paste content directly
    - **url**: Fetch from a URL (coming soon)
    - **upload**: Upload a file (use /upload endpoint)
    """
    try:
        service = get_knowledge_service()
        return await service.add_resource(collection_id, user_id, data)
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except Exception as e:
        logger.error(f"Failed to add resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections/{collection_id}/upload", response_model=Resource, status_code=201)
async def upload_resource(
    collection_id: int,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    resource_type: str = Form("document"),
    user_id: int = Depends(get_user_id)
):
    """
    Upload a file as a resource.
    
    Supported formats:
    - Text: .txt, .md
    - Documents: .pdf, .docx (coming soon)
    - Data: .json, .csv (coming soon)
    """
    try:
        # Read file content
        content = await file.read()
        
        # Decode text content
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other encodings or handle binary
            try:
                text_content = content.decode('latin-1')
            except:
                raise HTTPException(
                    status_code=400, 
                    detail="Could not decode file. Only text files are currently supported."
                )
        
        # Create resource
        service = get_knowledge_service()
        data = ResourceCreate(
            name=name or file.filename,
            description=description,
            resource_type=ResourceType(resource_type),
            source_type=SourceType.UPLOAD,
            content=text_content
        )
        
        return await service.add_resource(collection_id, user_id, data)
        
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except Exception as e:
        logger.error(f"Failed to upload resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Pydantic model for URL resource creation
from pydantic import BaseModel, HttpUrl

class UrlResourceRequest(BaseModel):
    """Request to add a resource from a URL"""
    url: str
    name: Optional[str] = None
    description: Optional[str] = None
    resource_type: Optional[str] = "article"


class UrlResourceResponse(BaseModel):
    """Response from URL resource creation"""
    resource: Resource
    extraction: dict  # Extraction metadata


@router.post("/collections/{collection_id}/from-url", response_model=UrlResourceResponse, status_code=201)
async def add_resource_from_url(
    collection_id: int,
    request: UrlResourceRequest,
    user_id: int = Depends(get_user_id)
):
    """
    Add a resource by fetching content from a URL.
    
    Automatically:
    - **Fetches** the page content
    - **Extracts** clean text (removes navigation, ads, scripts)
    - **Pulls metadata** (title, author, publish date when available)
    - **Estimates** token count for indexing costs
    
    Supports:
    - Web pages (articles, blogs, documentation)
    - PDFs (academic papers, reports)
    - Plain text and Markdown files
    
    Note: Some sites may block automated access or require JavaScript.
    """
    try:
        service = get_knowledge_service()
        
        # Determine resource type
        res_type = ResourceType.ARTICLE
        if request.resource_type:
            try:
                res_type = ResourceType(request.resource_type)
            except ValueError:
                pass
        
        resource, extracted = await service.add_resource_from_url(
            collection_id=collection_id,
            user_id=user_id,
            url=request.url,
            name=request.name,
            description=request.description,
            resource_type=res_type
        )
        
        return UrlResourceResponse(
            resource=resource,
            extraction={
                "success": extracted.success,
                "title": extracted.title,
                "author": extracted.author,
                "publish_date": extracted.publish_date,
                "description": extracted.description,
                "word_count": extracted.word_count,
                "content_type": extracted.content_type,
                "extractor": extracted.metadata.get("extractor") if extracted.metadata else None,
            }
        )
        
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add resource from URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources/{resource_id}/refresh", response_model=UrlResourceResponse)
async def refresh_url_resource(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    Re-fetch content from a URL resource.
    
    Useful when:
    - Original fetch partially failed
    - Source content has been updated
    - Want to refresh metadata
    
    Only works for resources with a source URL.
    """
    try:
        service = get_knowledge_service()
        resource, extracted = await service.refresh_url_content(resource_id, user_id)
        
        return UrlResourceResponse(
            resource=resource,
            extraction={
                "success": extracted.success,
                "title": extracted.title,
                "author": extracted.author,
                "publish_date": extracted.publish_date,
                "description": extracted.description,
                "word_count": extracted.word_count,
                "content_type": extracted.content_type,
                "extractor": extracted.metadata.get("extractor") if extracted.metadata else None,
            }
        )
        
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refresh resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_id}/resources", response_model=List[ResourceSummary])
async def list_resources(
    collection_id: int,
    user_id: int = Depends(get_user_id)
):
    """List all resources in a collection."""
    try:
        service = get_knowledge_service()
        return await service.list_resources(collection_id, user_id)
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except Exception as e:
        logger.error(f"Failed to list resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """Get a resource by ID."""
    try:
        service = get_knowledge_service()
        return await service.get_resource(resource_id, user_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        logger.error(f"Failed to get resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/resources/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """Delete a resource and all its indexes."""
    try:
        service = get_knowledge_service()
        await service.delete_resource(resource_id, user_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        logger.error(f"Failed to delete resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INDEXING
# ============================================================================

@router.get("/resources/{resource_id}/index-estimate", response_model=IndexEstimate)
async def get_index_estimate(
    resource_id: int,
    level: IndexLevel = Query(IndexLevel.STANDARD, description="Indexing depth"),
    model_id: Optional[str] = Query(None, description="Specific model to use"),
    user_id: int = Depends(get_user_id)
):
    """
    Get cost estimate for indexing a resource.
    
    Index levels:
    - **light**: Summary + key quotes (~5% token cost)
    - **standard**: + structured breakdown + vector search (~20% token cost)
    - **full**: + chapters, themes, characters (~120% token cost)
    
    Returns estimated cost and cheaper alternatives.
    """
    try:
        service = get_knowledge_service()
        return await service.estimate_index_cost(resource_id, user_id, level, model_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        logger.error(f"Failed to estimate index cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources/{resource_id}/index", response_model=IndexResult)
async def index_resource(
    resource_id: int,
    request: IndexRequest,
    user_id: int = Depends(get_user_id)
):
    """
    Index a resource at the specified level.
    
    **Two-step process:**
    1. First call with `confirmed: false` to get cost estimate
    2. Second call with `confirmed: true` to perform indexing
    
    This ensures users approve costs before spending.
    """
    try:
        service = get_knowledge_service()
        result = await service.index_resource(resource_id, user_id, request)
        
        # If not confirmed, return 202 Accepted
        if not request.confirmed:
            return result  # Contains estimate, not final result
        
        return result
        
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except BudgetExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))  # Payment Required
    except IndexingError as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
    except Exception as e:
        logger.error(f"Failed to index resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/{resource_id}/indexes", response_model=List[ResourceIndex])
async def get_resource_indexes(
    resource_id: int,
    index_type: Optional[IndexType] = Query(None, description="Filter by index type"),
    user_id: int = Depends(get_user_id)
):
    """Get all indexes for a resource."""
    try:
        service = get_knowledge_service()
        return await service.get_resource_indexes(resource_id, user_id, index_type)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        logger.error(f"Failed to get indexes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEARCH
# ============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    query: SearchQuery,
    user_id: int = Depends(get_user_id)
):
    """
    Search across user's knowledge base.
    
    Uses semantic search (vector similarity) combined with keyword matching
    to find relevant content across indexed resources.
    """
    try:
        service = get_knowledge_service()
        return await service.search(user_id, query)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_knowledge_simple(
    q: str = Query(..., min_length=1, description="Search query"),
    collections: Optional[str] = Query(None, description="Comma-separated collection IDs"),
    types: Optional[str] = Query(None, description="Comma-separated resource types"),
    limit: int = Query(10, ge=1, le=50),
    user_id: int = Depends(get_user_id)
):
    """
    Simple GET-based search endpoint.
    
    Query params version of POST /search for easy linking.
    """
    try:
        collection_ids = None
        if collections:
            collection_ids = [int(c.strip()) for c in collections.split(',')]
        
        resource_types = None
        if types:
            resource_types = [ResourceType(t.strip()) for t in types.split(',')]
        
        query = SearchQuery(
            query=q,
            collection_ids=collection_ids,
            resource_types=resource_types,
            limit=limit
        )
        
        service = get_knowledge_service()
        return await service.search(user_id, query)
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHARACTER EXTRACTION
# ============================================================================

@router.post("/resources/{resource_id}/extract-characters", response_model=List[CharacterProfile])
async def extract_characters(
    resource_id: int,
    model_id: Optional[str] = Query(None, description="Model to use for extraction"),
    user_id: int = Depends(get_user_id)
):
    """
    Extract characters from a fiction resource.
    
    Analyzes the text to identify characters, their roles, relationships,
    voice patterns, and representative quotes.
    
    **Note:** LLM dialogue attribution is imperfect. Results should be
    treated as "best effort" and may benefit from manual review.
    
    💰 This operation uses AI tokens - cost depends on resource size and model.
    """
    try:
        service = get_knowledge_service()
        return await service.extract_characters(resource_id, user_id, model_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except BudgetExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except Exception as e:
        logger.error(f"Character extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/{resource_id}/characters", response_model=List[CharacterProfile])
async def get_characters(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """Get extracted characters for a resource."""
    try:
        service = get_knowledge_service()
        # Query character_profiles table
        cursor = service.db.execute(
            "SELECT * FROM character_profiles WHERE resource_id = ?",
            (resource_id,)
        )
        rows = cursor.fetchall()
        
        import json
        from datetime import datetime
        from models.knowledge_models import VoiceProfile, CharacterRole
        
        characters = []
        for row in rows:
            characters.append(CharacterProfile(
                id=row[0],
                resource_id=row[1],
                name=row[2],
                aliases=json.loads(row[3]) if row[3] else [],
                description=row[4],
                role=CharacterRole(row[5]) if row[5] else CharacterRole.SUPPORTING,
                voice_profile=VoiceProfile(**json.loads(row[6])) if row[6] else None,
                relationships=[],
                sample_quotes=json.loads(row[8]) if row[8] else [],
                source_work=row[9],
                source_author=row[10],
                created_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11]
            ))
        
        return characters
        
    except Exception as e:
        logger.error(f"Failed to get characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUTHOR VOICES
# ============================================================================

@router.post("/author-voices", response_model=AuthorVoice, status_code=201)
async def create_author_voice(
    data: AuthorVoiceCreate,
    model_id: Optional[str] = Query(None, description="Model for analysis"),
    user_id: int = Depends(get_user_id)
):
    """
    Generate an author voice profile from their works.
    
    Analyzes writing style including vocabulary, sentence structure,
    narrative voice, tone, and distinctive techniques.
    
    Use this profile to generate content that matches the author's style.
    
    💰 This operation uses AI tokens.
    """
    try:
        service = get_knowledge_service()
        return await service.generate_author_voice(user_id, data, model_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="One or more resources not found")
    except BudgetExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except Exception as e:
        logger.error(f"Author voice generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/author-voices", response_model=List[AuthorVoice])
async def list_author_voices(
    user_id: int = Depends(get_user_id)
):
    """List all author voice profiles."""
    try:
        service = get_knowledge_service()
        cursor = service.db.execute(
            "SELECT * FROM author_voices WHERE user_id = ? ORDER BY author_name",
            (user_id,)
        )
        rows = cursor.fetchall()
        
        import json
        from datetime import datetime
        from models.knowledge_models import WritingStyleProfile
        
        voices = []
        for row in rows:
            voices.append(AuthorVoice(
                id=row[0],
                user_id=row[1],
                author_name=row[2],
                style_profile=WritingStyleProfile(**json.loads(row[3])) if row[3] else WritingStyleProfile(),
                sample_passages=json.loads(row[4]) if row[4] else [],
                source_works=json.loads(row[5]) if row[5] else [],
                resource_ids=json.loads(row[6]) if row[6] else [],
                created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7]
            ))
        
        return voices
        
    except Exception as e:
        logger.error(f"Failed to list author voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/author-voices/{voice_id}", response_model=AuthorVoice)
async def get_author_voice(
    voice_id: int,
    user_id: int = Depends(get_user_id)
):
    """Get an author voice profile by ID."""
    try:
        service = get_knowledge_service()
        cursor = service.db.execute(
            "SELECT * FROM author_voices WHERE id = ? AND user_id = ?",
            (voice_id, user_id)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Author voice not found")
        
        import json
        from datetime import datetime
        from models.knowledge_models import WritingStyleProfile
        
        return AuthorVoice(
            id=row[0],
            user_id=row[1],
            author_name=row[2],
            style_profile=WritingStyleProfile(**json.loads(row[3])) if row[3] else WritingStyleProfile(),
            sample_passages=json.loads(row[4]) if row[4] else [],
            source_works=json.loads(row[5]) if row[5] else [],
            resource_ids=json.loads(row[6]) if row[6] else [],
            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get author voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/author-voices/{voice_id}", status_code=204)
async def delete_author_voice(
    voice_id: int,
    user_id: int = Depends(get_user_id)
):
    """Delete an author voice profile."""
    try:
        service = get_knowledge_service()
        cursor = service.db.execute(
            "DELETE FROM author_voices WHERE id = ? AND user_id = ?",
            (voice_id, user_id)
        )
        service.db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Author voice not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete author voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROJECT INTEGRATION
# ============================================================================

@router.put("/projects/{project_id}/knowledge-settings", response_model=ProjectKnowledgeSettings)
async def update_project_knowledge_settings(
    project_id: int,
    settings: ProjectKnowledgeSettings,
    user_id: int = Depends(get_user_id)
):
    """
    Configure knowledge base settings for a project.
    
    - Link collections to the project
    - Enable/disable auto-search in chat
    - Set relevance threshold
    - Configure context inclusion
    """
    try:
        service = get_knowledge_service()
        
        # Verify collections belong to user
        for coll_id in settings.linked_collections:
            try:
                await service.get_collection(coll_id, user_id)
            except CollectionNotFoundError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Collection {coll_id} not found or doesn't belong to you"
                )
        
        # Store settings (this would integrate with project service)
        # For now, store in collection settings
        for coll_id in settings.linked_collections:
            await service.update_collection(
                coll_id, 
                user_id,
                CollectionUpdate(settings={"linked_project": project_id})
            )
        
        return settings
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project KB settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/knowledge-settings", response_model=ProjectKnowledgeSettings)
async def get_project_knowledge_settings(
    project_id: int,
    user_id: int = Depends(get_user_id)
):
    """Get knowledge base settings for a project."""
    try:
        service = get_knowledge_service()
        
        # Find collections linked to this project
        collections = await service.list_collections(user_id, project_id=project_id)
        
        return ProjectKnowledgeSettings(
            project_id=project_id,
            linked_collections=[c.id for c in collections],
            auto_search_enabled=True,
            search_threshold=0.7,
            include_in_context=True,
            max_context_tokens=2000
        )
        
    except Exception as e:
        logger.error(f"Failed to get project KB settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.post("/estimate-tokens", response_model=TokenEstimate)
async def estimate_tokens(
    text: str = Form(..., description="Text to estimate tokens for")
):
    """
    Estimate token count for text.
    
    Useful for planning indexing costs before adding resources.
    """
    try:
        service = get_knowledge_service()
        return service.estimate_tokens(text)
    except Exception as e:
        logger.error(f"Token estimation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UrlPreviewRequest(BaseModel):
    """Request to preview URL extraction"""
    url: str


@router.post("/preview-url")
async def preview_url_extraction(
    request: UrlPreviewRequest
):
    """
    Preview what would be extracted from a URL without creating a resource.
    
    Use this to:
    - Verify the URL is accessible
    - See what content will be extracted
    - Check metadata (title, author, etc.)
    - Estimate token count and indexing costs
    
    Returns extraction preview without saving anything.
    """
    try:
        from backend.services.content_extractor import get_content_extractor
        
        extractor = get_content_extractor()
        extracted = await extractor.extract_from_url(request.url)
        
        # Estimate tokens
        service = get_knowledge_service()
        token_estimate = service.estimate_tokens(extracted.content) if extracted.content else None
        
        # Estimate indexing costs (rough)
        indexing_estimates = {}
        if token_estimate:
            tokens = token_estimate.estimated_tokens
            # Using approximate costs for Claude Sonnet
            indexing_estimates = {
                "light": {
                    "estimated_tokens": int(tokens * 0.05),
                    "estimated_cost": round(tokens * 0.05 / 1_000_000 * 18, 4)  # ~$18/1M for Sonnet
                },
                "standard": {
                    "estimated_tokens": int(tokens * 0.20),
                    "estimated_cost": round(tokens * 0.20 / 1_000_000 * 18, 4)
                },
                "full": {
                    "estimated_tokens": int(tokens * 1.20),
                    "estimated_cost": round(tokens * 1.20 / 1_000_000 * 18, 4)
                }
            }
        
        return {
            "success": extracted.success,
            "url": request.url,
            "title": extracted.title,
            "author": extracted.author,
            "publish_date": extracted.publish_date,
            "description": extracted.description,
            "word_count": extracted.word_count,
            "content_type": extracted.content_type,
            "content_preview": extracted.content[:1000] + "..." if extracted.content and len(extracted.content) > 1000 else extracted.content,
            "token_estimate": token_estimate.estimated_tokens if token_estimate else None,
            "indexing_cost_estimates": indexing_estimates,
            "extractor_used": extracted.metadata.get("extractor") if extracted.metadata else None,
            "error_message": extracted.error_message,
            "metadata": extracted.metadata
        }
        
    except Exception as e:
        logger.error(f"URL preview failed: {e}")
        return {
            "success": False,
            "url": request.url,
            "error_message": str(e)
        }


@router.get("/stats")
async def get_knowledge_stats(
    user_id: int = Depends(get_user_id)
):
    """
    Get user's knowledge base statistics.
    
    Returns counts, token usage, and spending summary.
    """
    try:
        service = get_knowledge_service()
        
        # Count collections
        coll_cursor = service.db.execute(
            text("SELECT COUNT(*) FROM knowledge_collections WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        collection_count = coll_cursor.fetchone()[0]
        
        # Count resources and tokens
        res_cursor = service.db.execute(
            text("""SELECT COUNT(*), COALESCE(SUM(token_count), 0), COALESCE(SUM(index_cost_dollars), 0)
               FROM knowledge_resources WHERE user_id = :user_id"""),
            {"user_id": user_id}
        )
        res_row = res_cursor.fetchone()
        
        # Count indexes
        idx_cursor = service.db.execute(
            text("""SELECT COUNT(*) FROM resource_indexes ri
               JOIN knowledge_resources r ON r.id = ri.resource_id
               WHERE r.user_id = :user_id"""),
            {"user_id": user_id}
        )
        index_count = idx_cursor.fetchone()[0]
        
        # Count characters and author voices
        char_cursor = service.db.execute(
            text("""SELECT COUNT(*) FROM character_profiles cp
               JOIN knowledge_resources r ON r.id = cp.resource_id
               WHERE r.user_id = :user_id"""),
            {"user_id": user_id}
        )
        character_count = char_cursor.fetchone()[0]
        
        voice_cursor = service.db.execute(
            text("SELECT COUNT(*) FROM author_voices WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        voice_count = voice_cursor.fetchone()[0]
        
        return {
            "collections": collection_count,
            "resources": res_row[0],
            "total_tokens": res_row[1],
            "total_indexing_cost": round(res_row[2], 2),
            "indexes": index_count,
            "characters": character_count,
            "author_voices": voice_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def knowledge_health():
    """Check Knowledge Base service health."""
    try:
        service = get_knowledge_service()
        
        # Test database connection
        service.db.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "llm_router": "available" if service.llm_router else "not configured",
            "spending_service": "available" if service.spending_service else "not configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
