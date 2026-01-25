"""
Parsing Service

Core business logic for:
- Parsing KB resources into structured arguments
- Extracting claims, evidence, and hierarchies
- Storing parsed data for search and composition
- Cost estimation and tracking

Integrates with:
- KnowledgeBaseService for resource access
- LLMRouter for AI parsing
- SpendingService for cost tracking
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import text

from backend.models.argument_models import (
    # Core models
    ParsedResource, ParsedResourceCreate, ParsedResourceSummary,
    Claim, ClaimCreate, ClaimSummary, ClaimUpdate,
    Evidence, EvidenceCreate,
    ParsedStructure, OutlineNode, ParsedResourceOutline,
    # Enums
    ClaimType, VerificationStatus, EvidenceType,
    # Request/Response
    ParseRequest, ParseEstimate, ParseResult,
    BulkParseRequest, BulkParseResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Parsing prompt version (increment when prompt changes significantly)
PARSER_VERSION = "1.0.0"

# Token ratios for cost estimation
PARSING_INPUT_RATIO = 1.0    # Full content as input
PARSING_OUTPUT_RATIO = 0.3   # ~30% output (structured extraction)

# Default model for parsing (can be overridden)
DEFAULT_PARSING_MODEL = "claude-sonnet-4-20250514"


# ============================================================================
# PARSING PROMPT
# ============================================================================

PARSING_SYSTEM_PROMPT = """You are an expert analyst who extracts structured arguments from documents.

Your task is to identify:
1. The main thesis or central claim
2. Supporting arguments and sub-arguments
3. Individual claims within each argument
4. Evidence supporting each claim

You classify claims as:
- "factual": Verifiable facts about the world (statistics, events, data)
- "interpretive": Analysis or interpretation of facts (conclusions, assessments)
- "prescriptive": Recommendations or calls to action (should, must, need to)

You are thorough but precise. Extract the actual argument structure, not a summary.
Return valid JSON only, no markdown formatting."""

PARSING_USER_PROMPT = """Analyze this document and extract its argument structure.

Document:
---
{content}
---

Extract and return as JSON:
{{
  "main_thesis": "The central claim or position of the document (1-2 sentences)",
  "summary": "A 2-3 sentence summary of the document's overall argument",
  "arguments": [
    {{
      "title": "Brief title for this argument",
      "claim": "The main claim this argument makes",
      "claim_type": "factual|interpretive|prescriptive",
      "context": "Brief context about where/why this argument appears",
      "evidence": [
        {{
          "type": "statistic|quote|citation|example|data|testimony",
          "content": "The actual evidence",
          "source": "Source attribution if available"
        }}
      ],
      "sub_arguments": [
        // Nested arguments following the same structure
      ]
    }}
  ],
  "sources_cited": ["List of URLs or references cited in the document"]
}}

Important:
- Be thorough - capture ALL significant arguments, not just the first few
- Preserve the hierarchical structure of arguments and sub-arguments
- Include specific evidence (quotes, statistics, examples) when present
- Classify each claim accurately by type
- If no clear thesis exists, describe the document's main focus"""


# ============================================================================
# EXCEPTIONS
# ============================================================================

class ParsingError(Exception):
    """Base exception for parsing errors"""
    pass


class ResourceNotFoundError(ParsingError):
    """Resource not found in KB"""
    pass


class AlreadyParsedError(ParsingError):
    """Resource already parsed (use force_reparse)"""
    pass


class ContentTooLargeError(ParsingError):
    """Content exceeds maximum size for parsing"""
    pass


# ============================================================================
# PARSING SERVICE
# ============================================================================

class ParsingService:
    """
    Service for parsing KB resources into structured arguments.
    
    The parsing pipeline:
    1. Fetch resource content from KB
    2. Estimate cost and check budget
    3. Send to LLM with parsing prompt
    4. Parse JSON response
    5. Store ParsedResource, Claims, Evidence
    6. Optionally generate embeddings for search
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
        
        self.db = None
        self.llm_router = None
        self.spending_service = None
        self.knowledge_service = None
        self._initialized = True
        
        logger.info("ParsingService initialized")
    
    def initialize(
        self,
        db_connection,
        llm_router=None,
        spending_service=None,
        knowledge_service=None
    ):
        """
        Initialize with dependencies.
        
        Args:
            db_connection: Database connection
            llm_router: LLMRouter for AI operations
            spending_service: SpendingService for cost tracking
            knowledge_service: KnowledgeBaseService for resource access
        """
        self.db = db_connection
        self.llm_router = llm_router
        self.spending_service = spending_service
        self.knowledge_service = knowledge_service
        
        logger.info("ParsingService dependencies initialized")
    
    def is_initialized(self) -> bool:
        """Check if service is ready"""
        return self.db is not None and self.llm_router is not None
    
    def _exec(self, query: str, params: dict = None):
        """Execute SQL with named parameters"""
        if params:
            return self.db.execute(text(query), params)
        return self.db.execute(text(query))
    
    # ========================================================================
    # COST ESTIMATION
    # ========================================================================
    
    async def estimate_parsing(
        self,
        resource_id: int,
        user_id: int,
        model_id: Optional[str] = None
    ) -> ParseEstimate:
        """
        Estimate cost of parsing a resource.
        
        Args:
            resource_id: KB resource to parse
            user_id: User requesting the parse
            model_id: Model to use (or default)
            
        Returns:
            ParseEstimate with cost breakdown
        """
        # Get resource info
        resource = await self._get_resource(resource_id, user_id)
        if not resource:
            raise ResourceNotFoundError(f"Resource {resource_id} not found")
        
        # Check if already parsed
        already_parsed = await self._is_already_parsed(resource_id)
        
        # Get model info
        if not model_id:
            model_id = self._get_default_model()
        
        # Estimate tokens
        token_count = resource.get('token_count', 0)
        if token_count == 0:
            # Estimate from content length
            content_length = len(resource.get('original_content', '') or '')
            token_count = content_length // 4  # Rough estimate
        
        # Calculate parsing cost
        input_tokens = int(token_count * PARSING_INPUT_RATIO)
        output_tokens = int(token_count * PARSING_OUTPUT_RATIO)
        
        # Get cost from router if available
        if self.llm_router:
            try:
                cost = self.llm_router.estimate_cost(
                    model_id, input_tokens, output_tokens
                )
            except:
                # Fallback estimate (Claude Sonnet pricing)
                cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000
        else:
            cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000
        
        return ParseEstimate(
            resource_id=resource_id,
            resource_name=resource.get('name', 'Unknown'),
            token_count=token_count,
            estimated_parsing_tokens=input_tokens + output_tokens,
            estimated_cost_dollars=round(cost, 6),
            model_id=model_id,
            already_parsed=already_parsed
        )
    
    # ========================================================================
    # MAIN PARSING
    # ========================================================================
    
    async def parse_resource(
        self,
        request: ParseRequest,
        user_id: int
    ) -> ParseResult:
        """
        Parse a KB resource into structured arguments.
        
        Args:
            request: ParseRequest with resource_id and options
            user_id: User requesting the parse
            
        Returns:
            ParseResult with parsed data and cost info
        """
        start_time = time.time()
        
        try:
            # Check if already parsed
            if not request.force_reparse:
                existing = await self._get_existing_parse(request.resource_id, request.parse_level)
                if existing:
                    return ParseResult(
                        success=True,
                        parsed_resource_id=existing['id'],
                        resource_id=request.resource_id,
                        main_thesis=existing.get('main_thesis'),
                        summary=existing.get('summary'),
                        claim_count=await self._count_claims(existing['id']),
                        error_message="Already parsed (use force_reparse=True to re-parse)"
                    )
            
            # Get resource content
            resource = await self._get_resource(request.resource_id, user_id)
            if not resource:
                return ParseResult(
                    success=False,
                    resource_id=request.resource_id,
                    error_message=f"Resource {request.resource_id} not found"
                )
            
            content = await self._get_resource_content(resource)
            if not content:
                return ParseResult(
                    success=False,
                    resource_id=request.resource_id,
                    error_message="Resource has no content to parse"
                )
            
            # Get model
            model_id = request.model_id or self._get_default_model()
            
            # Call LLM
            logger.info(f"Parsing resource {request.resource_id} with {model_id}")
            
            prompt = PARSING_USER_PROMPT.format(content=content[:100000])  # Limit content size
            
            # Use complete_with_cost to get both response and cost info
            response_text, cost_info = self.llm_router.complete_with_cost(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=PARSING_SYSTEM_PROMPT,
                model=model_id,
                max_tokens=8000,
                temperature=0.1  # Low temp for structured output
            )
            
            # Create response dict for compatibility with rest of code
            response = {
                'content': response_text,
                'cost': cost_info.get('estimated_cost', 0),
                'usage': {
                    'input_tokens': cost_info.get('estimated_input_tokens', 0),
                    'output_tokens': cost_info.get('estimated_output_tokens', 0),
                    'total_tokens': cost_info.get('estimated_total_tokens', 0)
                }
            }
            
            # Parse response
            response_text = response.get('content', '')
            parsed_data = self._parse_llm_response(response_text)
            
            if not parsed_data:
                return ParseResult(
                    success=False,
                    resource_id=request.resource_id,
                    error_message="Failed to parse LLM response as JSON",
                    tokens_used=response.get('usage', {}).get('total_tokens', 0),
                    cost_dollars=response.get('cost', 0),
                    model_used=model_id
                )
            
            # Delete existing parse if force_reparse
            if request.force_reparse:
                await self._delete_existing_parse(request.resource_id, request.parse_level)
            
            # Store parsed resource
            parsed_resource_id = await self._store_parsed_resource(
                resource_id=request.resource_id,
                parsed_data=parsed_data,
                model_id=model_id,
                response=response,
                parse_level=request.parse_level
            )
            
            # Extract and store claims
            claim_count = 0
            evidence_count = 0
            
            if request.extract_claims:
                claim_count, evidence_count = await self._store_claims(
                    parsed_resource_id=parsed_resource_id,
                    arguments=parsed_data.get('arguments', []),
                    generate_embeddings=request.generate_embeddings
                )
            
            # Record spending
            if self.spending_service:
                try:
                    self.spending_service.record_spending(
                        user_id=user_id,
                        amount=response.get('cost', 0),
                        operation="resource_parsing",
                        model_id=model_id,
                        input_tokens=response.get('usage', {}).get('input_tokens', 0),
                        output_tokens=response.get('usage', {}).get('output_tokens', 0),
                        details={"resource_id": request.resource_id}
                    )
                except Exception as e:
                    logger.warning(f"Failed to record spending: {e}")
            
            self.db.commit()
            
            elapsed = time.time() - start_time
            
            return ParseResult(
                success=True,
                parsed_resource_id=parsed_resource_id,
                resource_id=request.resource_id,
                main_thesis=parsed_data.get('main_thesis'),
                summary=parsed_data.get('summary'),
                claim_count=claim_count,
                evidence_count=evidence_count,
                tokens_used=response.get('usage', {}).get('total_tokens', 0),
                cost_dollars=response.get('cost', 0),
                model_used=model_id,
                parse_time_seconds=round(elapsed, 2)
            )
            
        except Exception as e:
            logger.error(f"Parsing failed for resource {request.resource_id}: {e}")
            return ParseResult(
                success=False,
                resource_id=request.resource_id,
                error_message=str(e),
                parse_time_seconds=round(time.time() - start_time, 2)
            )
    
    async def bulk_parse(
        self,
        request: BulkParseRequest,
        user_id: int
    ) -> BulkParseResult:
        """
        Parse multiple resources.
        
        Args:
            request: BulkParseRequest with resource_ids
            user_id: User requesting the parse
            
        Returns:
            BulkParseResult with individual results
        """
        results = []
        successful = 0
        failed = 0
        skipped = 0
        total_cost = 0.0
        
        for resource_id in request.resource_ids:
            parse_request = ParseRequest(
                resource_id=resource_id,
                model_id=request.model_id,
                force_reparse=request.force_reparse
            )
            
            result = await self.parse_resource(parse_request, user_id)
            results.append(result)
            
            if result.success:
                if "Already parsed" in (result.error_message or ""):
                    skipped += 1
                else:
                    successful += 1
                    total_cost += result.cost_dollars
            else:
                failed += 1
        
        return BulkParseResult(
            total_requested=len(request.resource_ids),
            successful=successful,
            failed=failed,
            skipped=skipped,
            results=results,
            total_cost_dollars=round(total_cost, 6)
        )
    
    # ========================================================================
    # RETRIEVAL
    # ========================================================================
    
    async def get_parsed_resource(
        self,
        parsed_resource_id: int,
        include_claims: bool = True
    ) -> Optional[ParsedResource]:
        """Get a parsed resource by ID"""
        cursor = self._exec(
            """SELECT id, resource_id, main_thesis, summary, structure_json,
                      parsed_at, parser_model, parser_version,
                      parsing_cost_tokens, parsing_cost_dollars, sources_cited,
                      created_by, derived_from, license, created_at, updated_at
               FROM parsed_resources WHERE id = :id""",
            {"id": parsed_resource_id}
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        parsed = self._row_to_parsed_resource(row)
        
        if include_claims:
            parsed.claims = await self.get_claims_for_resource(parsed_resource_id)
        
        return parsed
    
    async def get_parsed_for_resource(
        self,
        resource_id: int,
        include_claims: bool = True
    ) -> Optional[ParsedResource]:
        """Get parsed data for a KB resource"""
        cursor = self._exec(
            """SELECT id, resource_id, main_thesis, summary, structure_json,
                      parsed_at, parser_model, parser_version,
                      parsing_cost_tokens, parsing_cost_dollars, sources_cited,
                      created_by, derived_from, license, created_at, updated_at
               FROM parsed_resources WHERE resource_id = :resource_id
               ORDER BY parsed_at DESC LIMIT 1""",
            {"resource_id": resource_id}
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        parsed = self._row_to_parsed_resource(row)
        
        if include_claims:
            parsed.claims = await self.get_claims_for_resource(parsed.id)
        
        return parsed
    
    async def get_claims_for_resource(
        self,
        parsed_resource_id: int,
        parent_id: Optional[int] = None
    ) -> List[Claim]:
        """Get claims for a parsed resource, optionally filtered by parent"""
        if parent_id is None:
            # Get top-level claims
            cursor = self._exec(
                """SELECT id, parsed_resource_id, claim_text, claim_type,
                          context, source_quote, position_in_doc, confidence,
                          parent_claim_id, argument_title,
                          verification_status, verification_sources, verification_notes, verified_at,
                          created_by, derived_from, license, created_at
                   FROM argument_claims
                   WHERE parsed_resource_id = :parsed_resource_id
                     AND parent_claim_id IS NULL
                   ORDER BY position_in_doc""",
                {"parsed_resource_id": parsed_resource_id}
            )
        else:
            cursor = self._exec(
                """SELECT id, parsed_resource_id, claim_text, claim_type,
                          context, source_quote, position_in_doc, confidence,
                          parent_claim_id, argument_title,
                          verification_status, verification_sources, verification_notes, verified_at,
                          created_by, derived_from, license, created_at
                   FROM argument_claims
                   WHERE parent_claim_id = :parent_id
                   ORDER BY position_in_doc""",
                {"parent_id": parent_id}
            )
        
        claims = []
        for row in cursor.fetchall():
            claim = self._row_to_claim(row)
            # Get evidence for this claim
            claim.evidence = await self._get_evidence_for_claim(claim.id)
            # Get sub-claims recursively
            claim.sub_claims = await self.get_claims_for_resource(
                parsed_resource_id, parent_id=claim.id
            )
            claims.append(claim)
        
        return claims
    
    async def get_claim(self, claim_id: int) -> Optional[Claim]:
        """Get a single claim by ID"""
        cursor = self._exec(
            """SELECT id, parsed_resource_id, claim_text, claim_type,
                      context, source_quote, position_in_doc, confidence,
                      parent_claim_id, argument_title,
                      verification_status, verification_sources, verification_notes, verified_at,
                      created_by, derived_from, license, created_at
               FROM argument_claims WHERE id = :id""",
            {"id": claim_id}
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        claim = self._row_to_claim(row)
        claim.evidence = await self._get_evidence_for_claim(claim_id)
        return claim
    
    # ========================================================================
    # OUTLINE VIEW
    # ========================================================================
    
    async def get_resource_outline(
        self,
        resource_id: int,
        user_id: int
    ) -> Optional[ParsedResourceOutline]:
        """
        Get a parsed resource as a navigable outline tree.
        
        This is optimized for frontend display with collapsible nodes.
        """
        # Get parsed resource
        parsed = await self.get_parsed_for_resource(resource_id, include_claims=True)
        if not parsed:
            return None
        
        # Get resource name
        resource = await self._get_resource(resource_id, user_id)
        resource_name = resource.get('name', 'Unknown') if resource else 'Unknown'
        
        # Build outline tree
        outline = []
        total_claims = 0
        total_evidence = 0
        verified_claims = 0
        
        for claim in parsed.claims:
            node, claims, evidence, verified = self._claim_to_outline_node(claim)
            outline.append(node)
            total_claims += claims
            total_evidence += evidence
            verified_claims += verified
        
        return ParsedResourceOutline(
            parsed_resource_id=parsed.id,
            resource_id=resource_id,
            resource_name=resource_name,
            main_thesis=parsed.main_thesis,
            summary=parsed.summary,
            outline=outline,
            total_claims=total_claims,
            total_evidence=total_evidence,
            verified_claims=verified_claims,
            parsed_at=parsed.parsed_at,
            sources_cited=parsed.sources_cited or []
        )
    
    def _claim_to_outline_node(
        self,
        claim: Claim,
        depth: int = 0
    ) -> Tuple[OutlineNode, int, int, int]:
        """Convert a claim (and its children) to outline nodes"""
        claim_count = 1
        evidence_count = len(claim.evidence)
        verified_count = 1 if claim.verification_status == VerificationStatus.VERIFIED else 0
        
        # Build children
        children = []
        
        # Add evidence as children
        for ev in claim.evidence:
            children.append(OutlineNode(
                id=f"evidence-{ev.id}",
                node_type="evidence",
                title=f"[{ev.evidence_type.value}]",
                content=ev.content,
                source_url=ev.source_url,
                metadata={
                    "source_title": ev.source_title,
                    "source_author": ev.source_author
                }
            ))
        
        # Add sub-claims as children
        for sub_claim in claim.sub_claims:
            child_node, c, e, v = self._claim_to_outline_node(sub_claim, depth + 1)
            children.append(child_node)
            claim_count += c
            evidence_count += e
            verified_count += v
        
        # Create node
        node = OutlineNode(
            id=f"claim-{claim.id}",
            node_type="argument" if claim.argument_title else "claim",
            title=claim.argument_title or claim.claim_text[:100],
            content=claim.claim_text if claim.argument_title else None,
            claim_type=claim.claim_type,
            verification_status=claim.verification_status,
            children=children,
            metadata={
                "context": claim.context,
                "source_quote": claim.source_quote,
                "confidence": claim.confidence
            }
        )
        
        return node, claim_count, evidence_count, verified_count
    
    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    def _get_default_model(self) -> str:
        """Get default model for parsing"""
        if self.llm_router:
            try:
                return self.llm_router.recommend_model_for_task("document_analysis")
            except:
                pass
        return DEFAULT_PARSING_MODEL
    
    async def _get_resource(self, resource_id: int, user_id: int) -> Optional[Dict]:
        """Get resource from KB"""
        cursor = self._exec(
            """SELECT id, collection_id, user_id, name, description,
                      resource_type, source_type, source_url, original_content,
                      content_hash, token_count
               FROM knowledge_resources
               WHERE id = :id AND user_id = :user_id""",
            {"id": resource_id, "user_id": user_id}
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'collection_id': row[1],
            'user_id': row[2],
            'name': row[3],
            'description': row[4],
            'resource_type': row[5],
            'source_type': row[6],
            'source_url': row[7],
            'original_content': row[8],
            'content_hash': row[9],
            'token_count': row[10]
        }
    
    async def _get_resource_content(self, resource: Dict) -> Optional[str]:
        """Get content for a resource"""
        # First try original_content
        content = resource.get('original_content')
        if content:
            return content
        
        # Try fetching from URL if available
        source_url = resource.get('source_url')
        if source_url and self.knowledge_service:
            try:
                from backend.services.content_extractor import get_content_extractor
                extractor = get_content_extractor()
                extracted = await extractor.extract_from_url(source_url)
                if extracted.success and extracted.content:
                    return extracted.content
            except Exception as e:
                logger.warning(f"Could not fetch content from URL: {e}")
        
        return None
    
    async def _is_already_parsed(self, resource_id: int) -> bool:
        """Check if resource has been parsed"""
        cursor = self._exec(
            "SELECT 1 FROM parsed_resources WHERE resource_id = :resource_id LIMIT 1",
            {"resource_id": resource_id}
        )
        return cursor.fetchone() is not None
    
    async def _get_existing_parse(self, resource_id: int, parse_level: str = "standard") -> Optional[Dict]:
        """Get existing parse for resource"""
        cursor = self._exec(
            """SELECT id, main_thesis, summary FROM parsed_resources
               WHERE resource_id = :resource_id AND parse_level = :parse_level ORDER BY parsed_at DESC LIMIT 1""",
            {"resource_id": resource_id,
                "parse_level": parse_level}
        )
        row = cursor.fetchone()
        if row:
            return {'id': row[0], 'main_thesis': row[1], 'summary': row[2]}
        return None
    
    async def _delete_existing_parse(self, resource_id: int, parse_level: str = "standard"):
        """Delete existing parse (cascades to claims/evidence)"""
        self._exec(
            "DELETE FROM parsed_resources WHERE resource_id = :resource_id AND parse_level = :parse_level",
            {"resource_id": resource_id,
                "parse_level": parse_level}
        )
    
    async def _count_claims(self, parsed_resource_id: int) -> int:
        """Count claims for a parsed resource"""
        cursor = self._exec(
            "SELECT COUNT(*) FROM argument_claims WHERE parsed_resource_id = :id",
            {"id": parsed_resource_id}
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def _parse_llm_response(self, response_text: str) -> Optional[Dict]:
        """Parse LLM response as JSON"""
        try:
            # Try direct parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        try:
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if json_match:
                return json.loads(json_match.group(1))
        except:
            pass
        
        # Try to find JSON object in text
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        logger.error(f"Could not parse LLM response as JSON: {response_text[:500]}")
        return None
    
    async def _store_parsed_resource(
        self,
        resource_id: int,
        parsed_data: Dict,
        model_id: str,
        response: Dict,
        parse_level: str = "standard"
    ) -> int:
        """Store parsed resource in database"""
        cursor = self._exec(
            """INSERT INTO parsed_resources
               (resource_id, main_thesis, summary, structure_json, parse_level,
                parsed_at, parser_model, parser_version,
                parsing_cost_tokens, parsing_cost_dollars, sources_cited,
                created_at, updated_at)
               VALUES (:resource_id, :main_thesis, :summary, :structure_json, :parse_level,
                       :parsed_at, :parser_model, :parser_version,
                       :parsing_cost_tokens, :parsing_cost_dollars, :sources_cited,
                       :created_at, :updated_at)
               RETURNING id""",
            {
                "resource_id": resource_id,
                "parse_level": parse_level,
                "main_thesis": parsed_data.get('main_thesis'),
                "summary": parsed_data.get('summary'),
                "structure_json": json.dumps(parsed_data),
                "parsed_at": datetime.utcnow(),
                "parser_model": model_id,
                "parser_version": PARSER_VERSION,
                "parsing_cost_tokens": response.get('usage', {}).get('total_tokens', 0),
                "parsing_cost_dollars": response.get('cost', 0),
                "sources_cited": json.dumps(parsed_data.get('sources_cited', [])),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )
        
        # Handle SQLite (no RETURNING)
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # Fallback for SQLite
        cursor = self._exec("SELECT last_insert_rowid()")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    async def _store_claims(
        self,
        parsed_resource_id: int,
        arguments: List[Dict],
        parent_claim_id: Optional[int] = None,
        position_counter: Optional[List[int]] = None,
        generate_embeddings: bool = False
    ) -> Tuple[int, int]:
        """
        Recursively store claims and evidence from parsed arguments.
        
        Returns (claim_count, evidence_count)
        """
        if position_counter is None:
            position_counter = [0]
        
        total_claims = 0
        total_evidence = 0
        
        for arg in arguments:
            position_counter[0] += 1
            
            # Insert claim
            claim_id = await self._insert_claim(
                parsed_resource_id=parsed_resource_id,
                claim_text=arg.get('claim', ''),
                claim_type=arg.get('claim_type', 'factual'),
                argument_title=arg.get('title'),
                context=arg.get('context'),
                position=position_counter[0],
                parent_claim_id=parent_claim_id
            )
            total_claims += 1
            
            # Insert evidence
            for i, ev in enumerate(arg.get('evidence', [])):
                await self._insert_evidence(
                    claim_id=claim_id,
                    evidence_type=ev.get('type', 'example'),
                    content=ev.get('content', ''),
                    source=ev.get('source'),
                    position=i
                )
                total_evidence += 1
            
            # Recurse for sub-arguments
            sub_args = arg.get('sub_arguments', [])
            if sub_args:
                sub_claims, sub_evidence = await self._store_claims(
                    parsed_resource_id=parsed_resource_id,
                    arguments=sub_args,
                    parent_claim_id=claim_id,
                    position_counter=position_counter,
                    generate_embeddings=generate_embeddings
                )
                total_claims += sub_claims
                total_evidence += sub_evidence
        
        return total_claims, total_evidence
    
    async def _insert_claim(
        self,
        parsed_resource_id: int,
        claim_text: str,
        claim_type: str,
        argument_title: Optional[str],
        context: Optional[str],
        position: int,
        parent_claim_id: Optional[int]
    ) -> int:
        """Insert a claim and return its ID"""
        # Normalize claim type
        if claim_type not in ['factual', 'interpretive', 'prescriptive']:
            claim_type = 'factual'
        
        cursor = self._exec(
            """INSERT INTO argument_claims
               (parsed_resource_id, claim_text, claim_type, argument_title,
                context, position_in_doc, parent_claim_id, confidence, created_at)
               VALUES (:parsed_resource_id, :claim_text, :claim_type, :argument_title,
                       :context, :position, :parent_claim_id, :confidence, :created_at)
               RETURNING id""",
            {
                "parsed_resource_id": parsed_resource_id,
                "claim_text": claim_text,
                "claim_type": claim_type,
                "argument_title": argument_title,
                "context": context,
                "position": position,
                "parent_claim_id": parent_claim_id,
                "confidence": 1.0,
                "created_at": datetime.utcnow()
            }
        )
        
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # Fallback for SQLite
        cursor = self._exec("SELECT last_insert_rowid()")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    async def _insert_evidence(
        self,
        claim_id: int,
        evidence_type: str,
        content: str,
        source: Optional[str],
        position: int
    ) -> int:
        """Insert evidence and return its ID"""
        # Normalize evidence type
        valid_types = ['statistic', 'quote', 'citation', 'example', 'data', 'testimony']
        if evidence_type not in valid_types:
            evidence_type = 'example'
        
        cursor = self._exec(
            """INSERT INTO argument_evidence
               (claim_id, evidence_type, content, source_title, position, created_at)
               VALUES (:claim_id, :evidence_type, :content, :source_title, :position, :created_at)
               RETURNING id""",
            {
                "claim_id": claim_id,
                "evidence_type": evidence_type,
                "content": content,
                "source_title": source,
                "position": position,
                "created_at": datetime.utcnow()
            }
        )
        
        result = cursor.fetchone()
        if result:
            return result[0]
        
        cursor = self._exec("SELECT last_insert_rowid()")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    async def _get_evidence_for_claim(self, claim_id: int) -> List[Evidence]:
        """Get evidence for a claim"""
        cursor = self._exec(
            """SELECT id, claim_id, evidence_type, content,
                      source_url, source_title, source_author, source_date,
                      position, created_by, derived_from, license, created_at
               FROM argument_evidence
               WHERE claim_id = :claim_id
               ORDER BY position""",
            {"claim_id": claim_id}
        )
        
        evidence = []
        for row in cursor.fetchall():
            evidence.append(Evidence(
                id=row[0],
                claim_id=row[1],
                evidence_type=EvidenceType(row[2]) if row[2] in [e.value for e in EvidenceType] else EvidenceType.EXAMPLE,
                content=row[3],
                source_url=row[4],
                source_title=row[5],
                source_author=row[6],
                source_date=row[7],
                position=row[8] or 0,
                created_by=row[9],
                derived_from=json.loads(row[10]) if isinstance(row[10], str) else row[10],
                license=row[11] or "private",
                created_at=datetime.fromisoformat(row[12]) if isinstance(row[12], str) else row[12]
            ))
        
        return evidence
    
    def _row_to_parsed_resource(self, row) -> ParsedResource:
        """Convert database row to ParsedResource model"""
        return ParsedResource(
            id=row[0],
            resource_id=row[1],
            main_thesis=row[2],
            summary=row[3],
            structure_json=json.loads(row[4]) if isinstance(row[4], str) else row[4],
            parsed_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
            parser_model=row[6],
            parser_version=row[7],
            parsing_cost_tokens=row[8] or 0,
            parsing_cost_dollars=row[9] or 0.0,
            sources_cited=json.loads(row[10]) if isinstance(row[10], str) else (row[10] or []),
            created_by=row[11],
            derived_from=json.loads(row[12]) if isinstance(row[12], str) else row[12],
            license=row[13] or "private",
            created_at=datetime.fromisoformat(row[14]) if isinstance(row[14], str) else row[14],
            updated_at=datetime.fromisoformat(row[15]) if isinstance(row[15], str) else row[15],
            claims=[]
        )
    
    def _row_to_claim(self, row) -> Claim:
        """Convert database row to Claim model"""
        return Claim(
            id=row[0],
            parsed_resource_id=row[1],
            claim_text=row[2],
            claim_type=ClaimType(row[3]) if row[3] in [c.value for c in ClaimType] else ClaimType.FACTUAL,
            context=row[4],
            source_quote=row[5],
            position_in_doc=row[6],
            confidence=row[7] or 1.0,
            parent_claim_id=row[8],
            argument_title=row[9],
            verification_status=VerificationStatus(row[10]) if row[10] else None,
            verification_sources=json.loads(row[11]) if isinstance(row[11], str) else row[11],
            verification_notes=row[12],
            verified_at=datetime.fromisoformat(row[13]) if isinstance(row[13], str) and row[13] else None,
            created_by=row[14],
            derived_from=json.loads(row[15]) if isinstance(row[15], str) else row[15],
            license=row[16] or "private",
            created_at=datetime.fromisoformat(row[17]) if isinstance(row[17], str) else row[17],
            evidence=[],
            sub_claims=[]
        )


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_parsing_service: Optional[ParsingService] = None


def get_parsing_service() -> ParsingService:
    """Get the singleton ParsingService instance"""
    global _parsing_service
    if _parsing_service is None:
        _parsing_service = ParsingService()
    return _parsing_service
