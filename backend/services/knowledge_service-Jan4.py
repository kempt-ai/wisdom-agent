"""
Knowledge Base Service

Core business logic for:
- Collection management (CRUD)
- Resource management (CRUD + file handling)
- Indexing with cost estimation and spending integration
- Semantic search across collections
- Character extraction from fiction
- Author voice profile generation

Integrates with:
- SpendingService for budget enforcement
- LLMRouter for model selection
- MemoryService for vector storage (ChromaDB/pgvector)
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from sqlalchemy import text

# Import models
from backend.models.knowledge_models import (
    Collection, CollectionCreate, CollectionUpdate, CollectionSummary,
    Resource, ResourceCreate, ResourceUpdate, ResourceSummary,
    ResourceIndex, IndexEstimate, IndexRequest, IndexResult,
    CharacterProfile, CharacterProfileCreate, VoiceProfile,
    AuthorVoice, AuthorVoiceCreate, WritingStyleProfile,
    SearchQuery, SearchResult, SearchResponse,
    IndexLevel, IndexStatus, IndexType, ResourceType, SourceType,
    TokenEstimate, BulkOperationResult
)

# Import content extractor for URL handling
from backend.services.content_extractor import get_content_extractor, ExtractedContent

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Token estimation ratios for indexing
INDEX_TOKEN_RATIOS = {
    IndexLevel.LIGHT: 0.05,      # ~5% of content tokens
    IndexLevel.STANDARD: 0.20,   # ~20% of content tokens
    IndexLevel.FULL: 1.20,       # ~120% of content tokens (full embedding + analysis)
}

# What indexes are created at each level
INDEX_OUTPUTS = {
    IndexLevel.LIGHT: [IndexType.SUMMARY, IndexType.QUOTES],
    IndexLevel.STANDARD: [IndexType.SUMMARY, IndexType.STRUCTURED, IndexType.QUOTES, IndexType.VECTOR],
    IndexLevel.FULL: [IndexType.SUMMARY, IndexType.STRUCTURED, IndexType.QUOTES, IndexType.VECTOR, 
                      IndexType.CHAPTERS, IndexType.THEMES, IndexType.CHARACTERS],
}

# Character ratio for token estimation (when tiktoken unavailable)
CHARS_PER_TOKEN = 4


# ============================================================================
# EXCEPTIONS
# ============================================================================

class KnowledgeBaseError(Exception):
    """Base exception for Knowledge Base errors"""
    pass


class CollectionNotFoundError(KnowledgeBaseError):
    """Collection not found"""
    pass


class ResourceNotFoundError(KnowledgeBaseError):
    """Resource not found"""
    pass


class BudgetExceededError(KnowledgeBaseError):
    """User's budget would be exceeded"""
    pass


class IndexingError(KnowledgeBaseError):
    """Error during indexing operation"""
    pass


class SearchError(KnowledgeBaseError):
    """Error during search operation"""
    pass


# ============================================================================
# KNOWLEDGE BASE SERVICE
# ============================================================================

class KnowledgeBaseService:
    """
    Service for managing the Knowledge Base.
    
    The Knowledge Base allows users to:
    1. Organize resources into collections
    2. Index resources at varying depth/cost levels
    3. Search semantically across their knowledge
    4. Extract characters from fiction for interaction
    5. Create author voice profiles for style matching
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.db = None  # Set by initialize()
        self.spending_service = None
        self.llm_router = None
        self.memory_service = None  # For vector operations
        self._initialized = True
        
        logger.info("KnowledgeBaseService initialized")
    
    def initialize(self, db_connection, spending_service=None, llm_router=None, memory_service=None):
        """
        Initialize with dependencies.
        
        Args:
            db_connection: Database connection (SQLAlchemy session or raw connection)
            spending_service: SpendingService instance for cost tracking
            llm_router: LLMRouter instance for AI operations
            memory_service: MemoryService for vector storage
        """
        self.db = db_connection
        self.spending_service = spending_service
        self.llm_router = llm_router
        self.memory_service = memory_service
        
        # Create tables if needed
        self._ensure_tables()
        
        logger.info("KnowledgeBaseService dependencies initialized")
    
    def _ensure_tables(self):
        """Ensure knowledge base tables exist"""
        try:
            from database.knowledge_tables import create_knowledge_tables
            # Detect database type
            is_postgres = hasattr(self.db, 'dialect') and 'postgres' in str(self.db.dialect.name)
            create_knowledge_tables(self.db, use_postgres=is_postgres)
        except Exception as e:
            logger.warning(f"Could not auto-create tables: {e}")
    
    def _exec(self, query: str, params: tuple = None):
        """
        Execute a SQL query with SQLAlchemy 2.0 compatibility.
        
        Converts ? placeholders to named parameters and wraps in text().
        """
        if params:
            # Convert ? placeholders to :p0, :p1, etc.
            param_dict = {}
            new_query = query
            for i, p in enumerate(params):
                new_query = new_query.replace('?', f':p{i}', 1)
                param_dict[f'p{i}'] = p
            return self._exec(text(new_query), param_dict)
        return self._exec(text(query))
    
    # ========================================================================
    # TOKEN ESTIMATION
    # ========================================================================
    
    def estimate_tokens(self, text: str) -> TokenEstimate:
        """
        Estimate token count for text.
        
        Uses tiktoken if available, falls back to character ratio.
        """
        text_length = len(text)
        
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")  # GPT-4/Claude encoding
            tokens = len(enc.encode(text))
            return TokenEstimate(
                text_length=text_length,
                estimated_tokens=tokens,
                method="tiktoken"
            )
        except ImportError:
            # Fallback to character ratio
            tokens = text_length // CHARS_PER_TOKEN
            return TokenEstimate(
                text_length=text_length,
                estimated_tokens=tokens,
                method="character_ratio"
            )
    
    # ========================================================================
    # COLLECTION CRUD
    # ========================================================================
    
    async def create_collection(self, user_id: int, data: CollectionCreate) -> Collection:
        """Create a new knowledge collection"""
        now = datetime.utcnow()
        
        # Insert into database
        query = """
            INSERT INTO knowledge_collections 
            (user_id, project_id, name, description, collection_type, visibility, tags, settings, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            user_id,
            data.project_id,
            data.name,
            data.description,
            data.collection_type.value,
            data.visibility.value,
            json.dumps(data.tags),
            json.dumps(data.settings),
            now.isoformat(),
            now.isoformat()
        )
        
        cursor = self._exec(query, values)
        self.db.commit()
        collection_id = cursor.lastrowid
        
        logger.info(f"Created collection {collection_id} for user {user_id}")
        
        return Collection(
            id=collection_id,
            user_id=user_id,
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            collection_type=data.collection_type,
            visibility=data.visibility,
            tags=data.tags,
            settings=data.settings,
            resource_count=0,
            total_tokens=0,
            created_at=now,
            updated_at=now
        )
    
    async def get_collection(self, collection_id: int, user_id: int) -> Collection:
        """Get a collection by ID"""
        query = """
            SELECT c.*, 
                   COUNT(r.id) as resource_count,
                   COALESCE(SUM(r.token_count), 0) as total_tokens
            FROM knowledge_collections c
            LEFT JOIN knowledge_resources r ON r.collection_id = c.id
            WHERE c.id = ? AND c.user_id = ?
            GROUP BY c.id
        """
        
        cursor = self._exec(query, (collection_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            raise CollectionNotFoundError(f"Collection {collection_id} not found")
        
        return self._row_to_collection(row)
    
    async def list_collections(
        self, 
        user_id: int, 
        project_id: Optional[int] = None,
        collection_type: Optional[str] = None
    ) -> List[CollectionSummary]:
        """List user's collections with optional filters"""
        
        query = """
            SELECT c.id, c.name, c.collection_type, c.updated_at,
                   COUNT(r.id) as resource_count
            FROM knowledge_collections c
            LEFT JOIN knowledge_resources r ON r.collection_id = c.id
            WHERE c.user_id = ?
        """
        params = [user_id]
        
        if project_id is not None:
            query += " AND c.project_id = ?"
            params.append(project_id)
        
        if collection_type:
            query += " AND c.collection_type = ?"
            params.append(collection_type)
        
        query += " GROUP BY c.id ORDER BY c.updated_at DESC"
        
        cursor = self._exec(query, params)
        rows = cursor.fetchall()
        
        return [
            CollectionSummary(
                id=row[0],
                name=row[1],
                collection_type=row[2],
                resource_count=row[4],
                updated_at=datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3]
            )
            for row in rows
        ]
    
    async def update_collection(
        self, 
        collection_id: int, 
        user_id: int, 
        data: CollectionUpdate
    ) -> Collection:
        """Update a collection"""
        # Build UPDATE query dynamically
        updates = []
        values = []
        
        if data.name is not None:
            updates.append("name = ?")
            values.append(data.name)
        if data.description is not None:
            updates.append("description = ?")
            values.append(data.description)
        if data.collection_type is not None:
            updates.append("collection_type = ?")
            values.append(data.collection_type.value)
        if data.visibility is not None:
            updates.append("visibility = ?")
            values.append(data.visibility.value)
        if data.tags is not None:
            updates.append("tags = ?")
            values.append(json.dumps(data.tags))
        if data.settings is not None:
            updates.append("settings = ?")
            values.append(json.dumps(data.settings))
        
        if not updates:
            return await self.get_collection(collection_id, user_id)
        
        updates.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        
        query = f"""
            UPDATE knowledge_collections 
            SET {', '.join(updates)}
            WHERE id = ? AND user_id = ?
        """
        values.extend([collection_id, user_id])
        
        cursor = self._exec(query, values)
        self.db.commit()
        
        if cursor.rowcount == 0:
            raise CollectionNotFoundError(f"Collection {collection_id} not found")
        
        return await self.get_collection(collection_id, user_id)
    
    async def delete_collection(self, collection_id: int, user_id: int) -> bool:
        """Delete a collection and all its resources"""
        query = "DELETE FROM knowledge_collections WHERE id = ? AND user_id = ?"
        cursor = self._exec(query, (collection_id, user_id))
        self.db.commit()
        
        if cursor.rowcount == 0:
            raise CollectionNotFoundError(f"Collection {collection_id} not found")
        
        logger.info(f"Deleted collection {collection_id}")
        return True
    
    # ========================================================================
    # RESOURCE CRUD
    # ========================================================================
    
    async def add_resource(
        self, 
        collection_id: int, 
        user_id: int, 
        data: ResourceCreate
    ) -> Resource:
        """Add a resource to a collection"""
        # Verify collection exists and belongs to user
        await self.get_collection(collection_id, user_id)
        
        # Get content and estimate tokens
        content = data.content or ""
        token_estimate = self.estimate_tokens(content)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32] if content else None
        
        now = datetime.utcnow()
        
        query = """
            INSERT INTO knowledge_resources
            (collection_id, user_id, name, description, resource_type, source_type, 
             source_url, original_content, content_hash, token_count, 
             visibility, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            collection_id,
            user_id,
            data.name,
            data.description,
            data.resource_type.value,
            data.source_type.value,
            data.source_url,
            content if len(content) < 1_000_000 else None,  # Don't store huge content in DB
            content_hash,
            token_estimate.estimated_tokens,
            data.visibility.value,
            json.dumps(data.metadata),
            now.isoformat(),
            now.isoformat()
        )
        
        cursor = self._exec(query, values)
        self.db.commit()
        resource_id = cursor.lastrowid
        
        logger.info(f"Added resource {resource_id} to collection {collection_id}")
        
        return Resource(
            id=resource_id,
            collection_id=collection_id,
            user_id=user_id,
            name=data.name,
            description=data.description,
            resource_type=data.resource_type,
            source_type=data.source_type,
            source_url=data.source_url,
            visibility=data.visibility,
            metadata=data.metadata,
            token_count=token_estimate.estimated_tokens,
            index_level=IndexLevel.NONE,
            index_status=IndexStatus.PENDING,
            index_cost_tokens=0,
            index_cost_dollars=0.0,
            created_at=now,
            updated_at=now
        )
    
    async def add_resource_from_url(
        self,
        collection_id: int,
        user_id: int,
        url: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        resource_type: ResourceType = ResourceType.ARTICLE
    ) -> Tuple[Resource, ExtractedContent]:
        """
        Add a resource by fetching content from a URL.
        
        Automatically:
        - Fetches the URL content
        - Extracts clean text (removes navigation, ads, etc.)
        - Pulls metadata (title, author, publish date)
        - Estimates token count
        - Creates the resource
        
        Returns both the resource and the extraction result for transparency.
        """
        # Verify collection exists and belongs to user
        await self.get_collection(collection_id, user_id)
        
        # Fetch and extract content
        extractor = get_content_extractor()
        extracted = await extractor.extract_from_url(url)
        
        if not extracted.success:
            raise KnowledgeBaseError(f"Failed to extract content from URL: {extracted.error_message}")
        
        if not extracted.content or len(extracted.content.strip()) < 50:
            raise KnowledgeBaseError("Extracted content is too short or empty. The page may require JavaScript or have access restrictions.")
        
        # Use extracted metadata if not provided
        resource_name = name or extracted.title or self._generate_name_from_url(url)
        resource_description = description or extracted.description
        
        # Detect resource type from content/URL if not specified
        if resource_type == ResourceType.ARTICLE:
            resource_type = self._detect_resource_type(url, extracted)
        
        # Build metadata from extraction
        metadata = {
            "source_url": url,
            "extracted_at": datetime.utcnow().isoformat(),
            "extractor": extracted.metadata.get("extractor", "unknown"),
            "word_count": extracted.word_count,
        }
        if extracted.author:
            metadata["author"] = extracted.author
        if extracted.publish_date:
            metadata["publish_date"] = extracted.publish_date
        if extracted.metadata:
            metadata["extraction_metadata"] = extracted.metadata
        
        # Create the resource
        data = ResourceCreate(
            name=resource_name,
            description=resource_description,
            resource_type=resource_type,
            source_type=SourceType.URL,
            source_url=url,
            content=extracted.content,
            metadata=metadata
        )
        
        resource = await self.add_resource(collection_id, user_id, data)
        
        logger.info(f"Added URL resource {resource.id}: {url} ({extracted.word_count} words)")
        
        return resource, extracted
    
    def _generate_name_from_url(self, url: str) -> str:
        """Generate a resource name from URL if title extraction fails"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        
        # Try to get meaningful path
        path = parsed.path.strip("/")
        if path:
            # Get last path segment
            segments = path.split("/")
            name = segments[-1]
            # Clean up
            name = name.replace("-", " ").replace("_", " ")
            name = name.rsplit(".", 1)[0]  # Remove extension
            if name:
                return name.title()[:100]
        
        # Fall back to domain
        return parsed.netloc[:100]
    
    def _detect_resource_type(self, url: str, extracted: ExtractedContent) -> ResourceType:
        """Detect resource type from URL and content"""
        url_lower = url.lower()
        
        # Check for PDF
        if ".pdf" in url_lower or extracted.content_type == "application/pdf":
            # Try to guess if it's a book or document
            if extracted.word_count > 20000:
                return ResourceType.NONFICTION_BOOK
            return ResourceType.DOCUMENT
        
        # Check for known patterns
        if "arxiv.org" in url_lower:
            return ResourceType.ARTICLE
        if "medium.com" in url_lower or "substack.com" in url_lower:
            return ResourceType.ARTICLE
        if "github.com" in url_lower:
            return ResourceType.DOCUMENT
        
        # Check content length
        if extracted.word_count > 30000:
            return ResourceType.NONFICTION_BOOK
        elif extracted.word_count > 5000:
            return ResourceType.ARTICLE
        
        return ResourceType.ARTICLE
    
    async def refresh_url_content(
        self,
        resource_id: int,
        user_id: int
    ) -> Tuple[Resource, ExtractedContent]:
        """
        Re-fetch content from a URL resource.
        
        Useful when:
        - Original fetch failed
        - Content has been updated
        - Want to refresh metadata
        """
        resource = await self.get_resource(resource_id, user_id)
        
        if not resource.source_url:
            raise KnowledgeBaseError("Resource has no source URL")
        
        # Fetch fresh content
        extractor = get_content_extractor()
        extracted = await extractor.extract_from_url(resource.source_url)
        
        if not extracted.success:
            raise KnowledgeBaseError(f"Failed to refresh content: {extracted.error_message}")
        
        # Update resource
        token_estimate = self.estimate_tokens(extracted.content)
        content_hash = hashlib.sha256(extracted.content.encode()).hexdigest()[:32]
        
        # Merge metadata
        existing_metadata = resource.metadata or {}
        existing_metadata.update({
            "refreshed_at": datetime.utcnow().isoformat(),
            "word_count": extracted.word_count,
        })
        if extracted.author:
            existing_metadata["author"] = extracted.author
        if extracted.publish_date:
            existing_metadata["publish_date"] = extracted.publish_date
        
        self._exec(
            """UPDATE knowledge_resources 
               SET original_content = ?, content_hash = ?, token_count = ?,
                   metadata = ?, updated_at = ?
               WHERE id = ? AND user_id = ?""",
            (
                extracted.content if len(extracted.content) < 1_000_000 else None,
                content_hash,
                token_estimate.estimated_tokens,
                json.dumps(existing_metadata),
                datetime.utcnow().isoformat(),
                resource_id,
                user_id
            )
        )
        self.db.commit()
        
        # Get updated resource
        updated_resource = await self.get_resource(resource_id, user_id)
        
        logger.info(f"Refreshed URL resource {resource_id}: {extracted.word_count} words")
        
        return updated_resource, extracted
    
    async def get_resource(self, resource_id: int, user_id: int) -> Resource:
        """Get a resource by ID"""
        query = """
            SELECT * FROM knowledge_resources 
            WHERE id = ? AND user_id = ?
        """
        cursor = self._exec(query, (resource_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            raise ResourceNotFoundError(f"Resource {resource_id} not found")
        
        return self._row_to_resource(row)
    
    async def list_resources(
        self, 
        collection_id: int, 
        user_id: int
    ) -> List[ResourceSummary]:
        """List resources in a collection"""
        query = """
            SELECT id, name, resource_type, token_count, index_level, index_status, updated_at
            FROM knowledge_resources
            WHERE collection_id = ? AND user_id = ?
            ORDER BY updated_at DESC
        """
        cursor = self._exec(query, (collection_id, user_id))
        rows = cursor.fetchall()
        
        return [
            ResourceSummary(
                id=row[0],
                name=row[1],
                resource_type=ResourceType(row[2]),
                token_count=row[3],
                index_level=IndexLevel(row[4]),
                index_status=IndexStatus(row[5]),
                updated_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6]
            )
            for row in rows
        ]
    
    async def delete_resource(self, resource_id: int, user_id: int) -> bool:
        """Delete a resource"""
        query = "DELETE FROM knowledge_resources WHERE id = ? AND user_id = ?"
        cursor = self._exec(query, (resource_id, user_id))
        self.db.commit()
        
        if cursor.rowcount == 0:
            raise ResourceNotFoundError(f"Resource {resource_id} not found")
        
        logger.info(f"Deleted resource {resource_id}")
        return True
    
    # ========================================================================
    # INDEXING
    # ========================================================================
    
    async def estimate_index_cost(
        self,
        resource_id: int,
        user_id: int,
        index_level: IndexLevel,
        model_id: Optional[str] = None
    ) -> IndexEstimate:
        """
        Estimate the cost of indexing a resource.
        
        Returns cost estimate with alternatives for user approval.
        """
        resource = await self.get_resource(resource_id, user_id)
        
        if not self.llm_router or not self.spending_service:
            raise KnowledgeBaseError("Service not properly initialized with LLM and Spending")
        
        # Get model info (use specified or get recommendation)
        if model_id:
            model_info = self.llm_router.get_model_info(model_id)
        else:
            task_type = f"indexing_{index_level.value}"
            model_id = self.llm_router.recommend_model_for_task(task_type)
            model_info = self.llm_router.get_model_info(model_id)
        
        # Calculate estimated tokens
        input_tokens = resource.token_count
        ratio = INDEX_TOKEN_RATIOS.get(index_level, 0.2)
        output_tokens = int(input_tokens * ratio)
        
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * model_info.get('input_cost_per_1m', 3.0)
        output_cost = (output_tokens / 1_000_000) * model_info.get('output_cost_per_1m', 15.0)
        estimated_cost = input_cost + output_cost
        
        # Check budget
        budget_status = self.spending_service.check_can_spend(user_id, estimated_cost)
        
        # Get cheaper alternatives
        alternatives = self._get_indexing_alternatives(input_tokens, output_tokens, model_id)
        
        return IndexEstimate(
            resource_id=resource_id,
            resource_name=resource.name,
            token_count=resource.token_count,
            index_level=index_level,
            model_id=model_id,
            model_name=model_info.get('name', model_id),
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost=round(estimated_cost, 4),
            budget_remaining=budget_status.remaining,
            can_afford=budget_status.allowed,
            warning_message=budget_status.message if not budget_status.allowed else None,
            alternatives=alternatives
        )
    
    def _get_indexing_alternatives(
        self, 
        input_tokens: int, 
        output_tokens: int,
        exclude_model: str
    ) -> List[Dict[str, Any]]:
        """Get alternative models with lower costs"""
        if not self.llm_router:
            return []
        
        alternatives = []
        
        # Get all models and calculate costs
        for provider in self.llm_router.get_available_providers():
            for model in self.llm_router.get_provider_models(provider):
                if model['id'] == exclude_model:
                    continue
                
                input_cost = (input_tokens / 1_000_000) * model.get('input_cost_per_1m', 3.0)
                output_cost = (output_tokens / 1_000_000) * model.get('output_cost_per_1m', 15.0)
                total_cost = input_cost + output_cost
                
                alternatives.append({
                    'model_id': model['id'],
                    'model_name': model.get('name', model['id']),
                    'provider': provider,
                    'tier': model.get('tier', 'standard'),
                    'estimated_cost': round(total_cost, 4)
                })
        
        # Sort by cost and return top 3 cheaper options
        alternatives.sort(key=lambda x: x['estimated_cost'])
        return alternatives[:3]
    
    async def index_resource(
        self,
        resource_id: int,
        user_id: int,
        request: IndexRequest
    ) -> IndexResult:
        """
        Index a resource at the specified level.
        
        If not confirmed, returns cost estimate requiring confirmation.
        If confirmed, performs indexing and records spending.
        """
        resource = await self.get_resource(resource_id, user_id)
        
        # Get cost estimate first
        estimate = await self.estimate_index_cost(
            resource_id, user_id, request.index_level, request.model_id
        )
        
        # If not confirmed, return estimate
        if not request.confirmed:
            return IndexResult(
                resource_id=resource_id,
                index_level=request.index_level,
                status=IndexStatus.PENDING,
                actual_cost=estimate.estimated_cost,
                input_tokens=estimate.estimated_input_tokens,
                output_tokens=estimate.estimated_output_tokens,
                indexes_created=[],
                error_message="Confirmation required. Review cost estimate and confirm."
            )
        
        # Check budget
        if not estimate.can_afford:
            raise BudgetExceededError(estimate.warning_message or "Budget exceeded")
        
        # Update status to indexing
        self._exec(
            "UPDATE knowledge_resources SET index_status = ? WHERE id = ?",
            (IndexStatus.INDEXING.value, resource_id)
        )
        self.db.commit()
        
        try:
            # Perform the actual indexing
            result = await self._perform_indexing(
                resource, 
                request.index_level,
                request.model_id or estimate.model_id
            )
            
            # Record spending
            if self.spending_service:
                self.spending_service.record_spending(
                    user_id=user_id,
                    amount=result.actual_cost,
                    operation=f"knowledge_index_{request.index_level.value}",
                    model_id=request.model_id or estimate.model_id,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    details={"resource_id": resource_id, "resource_name": resource.name}
                )
            
            # Update resource status
            self._exec(
                """UPDATE knowledge_resources 
                   SET index_level = ?, index_status = ?, 
                       index_cost_tokens = ?, index_cost_dollars = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (
                    request.index_level.value,
                    IndexStatus.COMPLETED.value,
                    result.input_tokens + result.output_tokens,
                    result.actual_cost,
                    datetime.utcnow().isoformat(),
                    resource_id
                )
            )
            self.db.commit()
            
            logger.info(f"Indexed resource {resource_id} at {request.index_level.value} level")
            return result
            
        except Exception as e:
            # Update status to failed
            self._exec(
                "UPDATE knowledge_resources SET index_status = ?, index_error = ? WHERE id = ?",
                (IndexStatus.FAILED.value, str(e), resource_id)
            )
            self.db.commit()
            
            raise IndexingError(f"Indexing failed: {e}")
    
    async def _perform_indexing(
        self,
        resource: Resource,
        index_level: IndexLevel,
        model_id: str
    ) -> IndexResult:
        """
        Actually perform the indexing using LLM.
        
        Creates appropriate indexes based on level:
        - LIGHT: Summary + key quotes
        - STANDARD: + structured breakdown + vector chunks
        - FULL: + chapters + themes + character extraction
        """
        if not self.llm_router:
            raise IndexingError("LLM router not initialized")
        
        # Get content
        content = await self._get_resource_content(resource)
        
        indexes_created = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        
        # Determine what to create based on level
        index_types = INDEX_OUTPUTS.get(index_level, [IndexType.SUMMARY])
        
        for index_type in index_types:
            try:
                result = await self._create_index(
                    resource, content, index_type, model_id
                )
                indexes_created.append(index_type)
                total_input_tokens += result.get('input_tokens', 0)
                total_output_tokens += result.get('output_tokens', 0)
                total_cost += result.get('cost', 0)
            except Exception as e:
                logger.warning(f"Failed to create {index_type} index: {e}")
        
        return IndexResult(
            resource_id=resource.id,
            index_level=index_level,
            status=IndexStatus.COMPLETED,
            actual_cost=round(total_cost, 4),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            indexes_created=indexes_created
        )
    
    async def _create_index(
        self,
        resource: Resource,
        content: str,
        index_type: IndexType,
        model_id: str
    ) -> Dict[str, Any]:
        """Create a single index type for a resource"""
        
        # Build prompt based on index type
        prompts = {
            IndexType.SUMMARY: f"""Summarize this {resource.resource_type.value} in 2-3 paragraphs, 
                capturing the main points, themes, and significance. Be concise but comprehensive.
                
                Content:
                {content[:50000]}""",
            
            IndexType.QUOTES: f"""Extract 10-20 notable quotes from this content that capture key ideas,
                memorable phrases, or important statements. Return as JSON array of strings.
                
                Content:
                {content[:50000]}""",
            
            IndexType.STRUCTURED: f"""Create a structured breakdown of this content including:
                1. Main sections/chapters
                2. Key concepts mentioned
                3. Important entities (people, places, organizations)
                4. Central arguments or themes
                Return as JSON object.
                
                Content:
                {content[:50000]}""",
            
            IndexType.THEMES: f"""Identify the major themes in this work. For each theme:
                1. Name the theme
                2. Explain how it manifests in the content
                3. Rate its prominence (major/minor)
                Return as JSON array.
                
                Content:
                {content[:50000]}""",
            
            IndexType.CHAPTERS: f"""Break this content into logical chapters or sections.
                For each section provide:
                1. Title
                2. Brief summary (1-2 sentences)
                3. Key points
                Return as JSON array.
                
                Content:
                {content[:80000]}""",
            
            IndexType.CHARACTERS: f"""Extract all characters from this fiction work.
                For each character provide:
                1. Name and aliases
                2. Role (protagonist, antagonist, supporting, minor)
                3. Brief description
                4. Key relationships
                5. 2-3 representative quotes
                Return as JSON array.
                
                Content:
                {content[:80000]}"""
        }
        
        prompt = prompts.get(index_type, prompts[IndexType.SUMMARY])
        
        # Call LLM
        response = await self.llm_router.complete(
            prompt,
            model=model_id,
            system="You are a careful analyst extracting structured information from content."
        )
        
        # Parse response
        response_text = response.get('content', '')
        
        # Try to parse as JSON for structured types
        content_data = None
        if index_type in [IndexType.QUOTES, IndexType.STRUCTURED, IndexType.THEMES, 
                          IndexType.CHAPTERS, IndexType.CHARACTERS]:
            try:
                # Find JSON in response
                import re
                json_match = re.search(r'\[[\s\S]*\]|\{[\s\S]*\}', response_text)
                if json_match:
                    content_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                content_data = {"raw": response_text}
        
        # Store in database
        self._exec(
            """INSERT INTO resource_indexes 
               (resource_id, index_type, content, text_content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                resource.id,
                index_type.value,
                json.dumps(content_data) if content_data else None,
                response_text if not content_data else None,
                datetime.utcnow().isoformat()
            )
        )
        self.db.commit()
        
        return {
            'input_tokens': response.get('usage', {}).get('input_tokens', 0),
            'output_tokens': response.get('usage', {}).get('output_tokens', 0),
            'cost': response.get('cost', 0)
        }
    
    async def _get_resource_content(self, resource: Resource) -> str:
        """Get the full text content of a resource"""
        # Check if stored in DB
        cursor = self._exec(
            "SELECT original_content FROM knowledge_resources WHERE id = ?",
            (resource.id,)
        )
        row = cursor.fetchone()
        
        if row and row[0]:
            return row[0]
        
        # Fetch from URL if needed
        if resource.source_url:
            try:
                extractor = get_content_extractor()
                result = await extractor.extract_from_url(resource.source_url)
                
                if result.success and result.content:
                    # Cache the content in the database
                    self._exec(
                        """UPDATE knowledge_resources 
                           SET original_content = ?, token_count = ?, updated_at = ?
                           WHERE id = ?""",
                        (
                            result.content if len(result.content) < 1_000_000 else None,
                            self.estimate_tokens(result.content).estimated_tokens,
                            datetime.utcnow().isoformat(),
                            resource.id
                        )
                    )
                    self.db.commit()
                    return result.content
                else:
                    logger.warning(f"Failed to fetch URL {resource.source_url}: {result.error_message}")
            except Exception as e:
                logger.error(f"Error fetching URL content: {e}")
        
        return ""
    
    async def get_resource_indexes(
        self,
        resource_id: int,
        user_id: int,
        index_type: Optional[IndexType] = None
    ) -> List[ResourceIndex]:
        """Get indexes for a resource"""
        # Verify ownership
        await self.get_resource(resource_id, user_id)
        
        query = "SELECT * FROM resource_indexes WHERE resource_id = ?"
        params = [resource_id]
        
        if index_type:
            query += " AND index_type = ?"
            params.append(index_type.value)
        
        cursor = self._exec(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_index(row) for row in rows]
    
    # ========================================================================
    # SEARCH
    # ========================================================================
    
    async def search(
        self,
        user_id: int,
        query: SearchQuery
    ) -> SearchResponse:
        """
        Search across user's knowledge base.
        
        Uses combination of:
        - Semantic/vector search (if available)
        - Full-text search on summaries and content
        - Keyword matching
        """
        import time
        start_time = time.time()
        
        results = []
        
        # Get user's collections
        if query.collection_ids:
            collection_ids = query.collection_ids
        else:
            collections = await self.list_collections(user_id)
            collection_ids = [c.id for c in collections]
        
        if not collection_ids:
            return SearchResponse(
                query=query.query,
                total_results=0,
                results=[],
                search_time_ms=0
            )
        
        # Search indexed content
        placeholders = ','.join(['?' for _ in collection_ids])
        
        # Search summaries and text content
        search_query = f"""
            SELECT r.id, r.name, r.resource_type, r.collection_id, c.name as collection_name,
                   ri.index_type, ri.text_content, ri.content
            FROM knowledge_resources r
            JOIN knowledge_collections c ON c.id = r.collection_id
            LEFT JOIN resource_indexes ri ON ri.resource_id = r.id
            WHERE r.collection_id IN ({placeholders})
            AND r.user_id = ?
            AND (
                r.name LIKE ? 
                OR r.description LIKE ?
                OR ri.text_content LIKE ?
            )
        """
        
        search_term = f"%{query.query}%"
        params = collection_ids + [user_id, search_term, search_term, search_term]
        
        if query.resource_types:
            type_placeholders = ','.join(['?' for _ in query.resource_types])
            search_query += f" AND r.resource_type IN ({type_placeholders})"
            params.extend([rt.value for rt in query.resource_types])
        
        search_query += f" LIMIT {query.limit}"
        
        cursor = self._exec(search_query, params)
        rows = cursor.fetchall()
        
        # Process results
        seen_resources = set()
        for row in rows:
            resource_id = row[0]
            if resource_id in seen_resources:
                continue
            seen_resources.add(resource_id)
            
            # Calculate simple relevance score
            relevance = self._calculate_relevance(query.query, row)
            
            results.append(SearchResult(
                resource_id=resource_id,
                resource_name=row[1],
                resource_type=ResourceType(row[2]),
                collection_id=row[3],
                collection_name=row[4],
                match_type="keyword",
                relevance_score=relevance,
                matched_text=row[6][:200] if row[6] else None,
                index_type=IndexType(row[5]) if row[5] else None
            ))
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        search_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=query.query,
            total_results=len(results),
            results=results[:query.limit],
            search_time_ms=round(search_time, 2)
        )
    
    def _calculate_relevance(self, query: str, row: tuple) -> float:
        """Calculate simple relevance score"""
        score = 0.0
        query_lower = query.lower()
        
        # Name match (high weight)
        if row[1] and query_lower in row[1].lower():
            score += 0.5
        
        # Content match
        if row[6] and query_lower in row[6].lower():
            score += 0.3
            # Bonus for multiple matches
            score += min(0.2, row[6].lower().count(query_lower) * 0.02)
        
        return min(1.0, score)
    
    # ========================================================================
    # CHARACTER EXTRACTION
    # ========================================================================
    
    async def extract_characters(
        self,
        resource_id: int,
        user_id: int,
        model_id: Optional[str] = None
    ) -> List[CharacterProfile]:
        """
        Extract characters from a fiction resource.
        
        Note: LLM dialogue attribution is imperfect. 
        Results should be treated as "best effort" and may need manual review.
        """
        resource = await self.get_resource(resource_id, user_id)
        
        if resource.resource_type != ResourceType.FICTION_BOOK:
            logger.warning(f"Character extraction on non-fiction resource {resource_id}")
        
        content = await self._get_resource_content(resource)
        
        if not self.llm_router:
            raise KnowledgeBaseError("LLM router not initialized")
        
        # Use specified model or get recommendation
        if not model_id:
            model_id = self.llm_router.recommend_model_for_task("character_extraction")
        
        prompt = f"""Analyze this fiction text and extract all significant characters.

For each character, provide:
1. Name (and any aliases)
2. Role: protagonist, antagonist, supporting, minor, or narrator
3. Description: appearance, personality, key traits
4. Voice profile:
   - Vocabulary level (formal, casual, archaic, technical, etc.)
   - Speech patterns (any distinctive ways of speaking)
   - Primary concerns/motivations
   - Emotional tone
5. Key relationships with other characters
6. 2-3 representative quotes (exact quotes from the text if possible)

Return as a JSON array of character objects.

IMPORTANT: Dialogue attribution in novels can be ambiguous. Flag any quotes where 
attribution is uncertain with "attribution_uncertain": true.

Text to analyze:
{content[:100000]}"""

        response = await self.llm_router.complete(
            prompt,
            model=model_id,
            system="You are an expert literary analyst specializing in character study."
        )
        
        # Parse response
        response_text = response.get('content', '')
        
        try:
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                characters_data = json.loads(json_match.group())
            else:
                characters_data = []
        except json.JSONDecodeError:
            characters_data = []
        
        # Save to database
        characters = []
        for char_data in characters_data:
            char_id = self._save_character(resource_id, char_data, resource.name)
            
            characters.append(CharacterProfile(
                id=char_id,
                resource_id=resource_id,
                name=char_data.get('name', 'Unknown'),
                aliases=char_data.get('aliases', []),
                description=char_data.get('description'),
                role=char_data.get('role', 'supporting'),
                voice_profile=VoiceProfile(**char_data.get('voice_profile', {})) if char_data.get('voice_profile') else None,
                relationships=[],
                sample_quotes=char_data.get('quotes', [])[:10],
                source_work=resource.name,
                created_at=datetime.utcnow()
            ))
        
        # Record cost
        if self.spending_service:
            self.spending_service.record_spending(
                user_id=user_id,
                amount=response.get('cost', 0),
                operation="character_extraction",
                model_id=model_id,
                input_tokens=response.get('usage', {}).get('input_tokens', 0),
                output_tokens=response.get('usage', {}).get('output_tokens', 0),
                details={"resource_id": resource_id, "characters_found": len(characters)}
            )
        
        return characters
    
    def _save_character(self, resource_id: int, data: dict, source_work: str) -> int:
        """Save a character profile to the database"""
        cursor = self._exec(
            """INSERT INTO character_profiles
               (resource_id, name, aliases, description, role, voice_profile, 
                relationships, sample_quotes, source_work, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                resource_id,
                data.get('name', 'Unknown'),
                json.dumps(data.get('aliases', [])),
                data.get('description'),
                data.get('role', 'supporting'),
                json.dumps(data.get('voice_profile', {})),
                json.dumps(data.get('relationships', [])),
                json.dumps(data.get('quotes', [])[:10]),
                source_work,
                datetime.utcnow().isoformat()
            )
        )
        self.db.commit()
        return cursor.lastrowid
    
    # ========================================================================
    # AUTHOR VOICE
    # ========================================================================
    
    async def generate_author_voice(
        self,
        user_id: int,
        data: AuthorVoiceCreate,
        model_id: Optional[str] = None
    ) -> AuthorVoice:
        """
        Generate an author voice profile from their works.
        
        Analyzes writing style, vocabulary, themes, and distinctive techniques
        to enable style-matched content generation.
        """
        if not self.llm_router:
            raise KnowledgeBaseError("LLM router not initialized")
        
        # Gather content from specified resources
        sample_content = ""
        for res_id in data.resource_ids:
            try:
                resource = await self.get_resource(res_id, user_id)
                content = await self._get_resource_content(resource)
                sample_content += f"\n\n--- From {resource.name} ---\n{content[:20000]}"
            except ResourceNotFoundError:
                continue
        
        if not sample_content:
            raise KnowledgeBaseError("No valid resources found for voice analysis")
        
        if not model_id:
            model_id = self.llm_router.recommend_model_for_task("voice_analysis")
        
        prompt = f"""Analyze the writing style of {data.author_name} based on these samples.

Create a comprehensive voice profile including:

1. Vocabulary Range: simple, moderate, extensive, or specialized
2. Sentence Structure: simple, complex, varied, stream-of-consciousness
3. Narrative Voice: first person, third person, omniscient, etc.
4. Tone Range: list of tones used (humorous, dark, hopeful, ironic, etc.)
5. Distinctive Techniques: unique stylistic choices
6. Common Themes: recurring subjects and ideas
7. Sample Passages: 3-5 short passages that exemplify their style

Return as a JSON object.

Samples:
{sample_content[:80000]}"""

        response = await self.llm_router.complete(
            prompt,
            model=model_id,
            system="You are a literary analyst specializing in author voice and style."
        )
        
        # Parse response
        response_text = response.get('content', '')
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                voice_data = json.loads(json_match.group())
            else:
                voice_data = {}
        except json.JSONDecodeError:
            voice_data = {}
        
        # Create style profile
        style_profile = WritingStyleProfile(
            vocabulary_range=voice_data.get('vocabulary_range', 'moderate'),
            sentence_structure=voice_data.get('sentence_structure', 'varied'),
            narrative_voice=voice_data.get('narrative_voice', 'third_person'),
            tone_range=voice_data.get('tone_range', []),
            distinctive_techniques=voice_data.get('distinctive_techniques', []),
            themes=voice_data.get('common_themes', voice_data.get('themes', []))
        )
        
        # Save to database
        cursor = self._exec(
            """INSERT INTO author_voices
               (user_id, author_name, style_profile, sample_passages, source_works, resource_ids, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                data.author_name,
                json.dumps(style_profile.model_dump()),
                json.dumps(voice_data.get('sample_passages', [])[:5]),
                json.dumps(data.source_works),
                json.dumps(data.resource_ids),
                datetime.utcnow().isoformat()
            )
        )
        self.db.commit()
        
        # Record cost
        if self.spending_service:
            self.spending_service.record_spending(
                user_id=user_id,
                amount=response.get('cost', 0),
                operation="author_voice_generation",
                model_id=model_id,
                input_tokens=response.get('usage', {}).get('input_tokens', 0),
                output_tokens=response.get('usage', {}).get('output_tokens', 0),
                details={"author": data.author_name}
            )
        
        return AuthorVoice(
            id=cursor.lastrowid,
            user_id=user_id,
            author_name=data.author_name,
            style_profile=style_profile,
            sample_passages=voice_data.get('sample_passages', [])[:5],
            source_works=data.source_works,
            resource_ids=data.resource_ids,
            created_at=datetime.utcnow()
        )
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _row_to_collection(self, row) -> Collection:
        """Convert database row to Collection model"""
        # Assuming row is a tuple/list matching SELECT order
        return Collection(
            id=row[0],
            user_id=row[1],
            project_id=row[2],
            name=row[3],
            description=row[4],
            collection_type=row[5],
            visibility=row[6],
            tags=json.loads(row[7]) if isinstance(row[7], str) else (row[7] or []),
            settings=json.loads(row[8]) if isinstance(row[8], str) else (row[8] or {}),
            created_at=datetime.fromisoformat(row[9]) if isinstance(row[9], str) else row[9],
            updated_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
            resource_count=row[11] if len(row) > 11 else 0,
            total_tokens=row[12] if len(row) > 12 else 0
        )
    
    def _row_to_resource(self, row) -> Resource:
        """Convert database row to Resource model"""
        return Resource(
            id=row[0],
            collection_id=row[1],
            user_id=row[2],
            name=row[3],
            description=row[4],
            resource_type=ResourceType(row[5]),
            source_type=row[6],
            source_url=row[7],
            token_count=row[10] or 0,
            index_level=IndexLevel(row[11] or 'none'),
            index_status=IndexStatus(row[12] or 'pending'),
            index_cost_tokens=row[13] or 0,
            index_cost_dollars=row[14] or 0.0,
            visibility=row[16] or 'private',
            metadata=json.loads(row[17]) if isinstance(row[17], str) else (row[17] or {}),
            created_at=datetime.fromisoformat(row[18]) if isinstance(row[18], str) else row[18],
            updated_at=datetime.fromisoformat(row[19]) if isinstance(row[19], str) else row[19]
        )
    
    def _row_to_index(self, row) -> ResourceIndex:
        """Convert database row to ResourceIndex model"""
        return ResourceIndex(
            id=row[0],
            resource_id=row[1],
            index_type=IndexType(row[2]),
            content=json.loads(row[3]) if isinstance(row[3], str) else row[3],
            text_content=row[4],
            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7]
        )


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_knowledge_service: Optional[KnowledgeBaseService] = None


def get_knowledge_service() -> KnowledgeBaseService:
    """Get the singleton KnowledgeBaseService instance"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeBaseService()
    return _knowledge_service
