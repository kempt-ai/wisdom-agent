"""
Argument Builder API Router

REST endpoints for:
- Parsing KB resources into structured arguments
- Retrieving parsed resources, claims, evidence
- Outline view for frontend tree display
- Claim verification (future: integrates with fact-checker)
- Argument module CRUD (Phase 5)

Follows patterns from knowledge.py router
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import logging

from backend.models.argument_models import (
    # Parsed resources
    ParsedResource, ParsedResourceSummary, ParsedResourceOutline,
    # Claims
    Claim, ClaimSummary, ClaimUpdate,
    # Evidence
    Evidence,
    # Enums
    ClaimType, VerificationStatus,
    # Request/Response
    ParseRequest, ParseEstimate, ParseResult,
    BulkParseRequest, BulkParseResult,
    # Search
    ClaimSearchQuery, ClaimSearchResponse,
)

from backend.services.parsing_service import (
    get_parsing_service,
    ParsingError,
    ResourceNotFoundError,
    AlreadyParsedError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arguments", tags=["Argument Builder"])


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
# PARSING ENDPOINTS
# ============================================================================

@router.post("/parse", response_model=ParseResult)
async def parse_resource(
    request: ParseRequest,
    user_id: int = Depends(get_user_id)
):
    """
    Parse a KB resource into structured arguments.
    
    This extracts:
    - Main thesis
    - Supporting arguments and sub-arguments
    - Individual claims (classified as factual/interpretive/prescriptive)
    - Evidence (statistics, quotes, citations, examples)
    
    The parsed structure is stored for search and composition.
    
    **Options:**
    - `force_reparse`: Re-parse even if already parsed
    - `extract_claims`: Store individual claims in DB (default: true)
    - `generate_embeddings`: Generate vectors for semantic search
    """
    try:
        service = get_parsing_service()
        if not service.is_initialized():
            raise HTTPException(
                status_code=503,
                detail="Parsing service not initialized. Check LLM router configuration."
            )
        
        result = await service.parse_resource(request, user_id)
        return result
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse/estimate", response_model=ParseEstimate)
async def estimate_parsing(
    resource_id: int,
    model_id: Optional[str] = Query(None, description="Model to use for parsing"),
    parse_level: str = Query("standard", description="Parse level: light, standard, or full"),
    user_id: int = Depends(get_user_id)
):
    """
    Estimate the cost of parsing a resource.
    
    Use this before parsing to:
    - Check if resource is already parsed
    - See estimated token usage and cost
    - Choose appropriate model
    """
    try:
        service = get_parsing_service()
        return await service.estimate_parsing(resource_id, user_id, model_id, parse_level)
        
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        logger.error(f"Estimate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse/bulk", response_model=BulkParseResult)
async def bulk_parse_resources(
    request: BulkParseRequest,
    user_id: int = Depends(get_user_id)
):
    """
    Parse multiple KB resources.
    
    Returns individual results for each resource.
    Already-parsed resources are skipped unless `force_reparse=True`.
    """
    try:
        service = get_parsing_service()
        if not service.is_initialized():
            raise HTTPException(
                status_code=503,
                detail="Parsing service not initialized"
            )
        
        return await service.bulk_parse(request, user_id)
        
    except Exception as e:
        logger.error(f"Bulk parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PARSED RESOURCE ENDPOINTS
# ============================================================================

@router.get("/parsed/{parsed_resource_id}", response_model=ParsedResource)
async def get_parsed_resource(
    parsed_resource_id: int,
    include_claims: bool = Query(True, description="Include claims in response"),
    user_id: int = Depends(get_user_id)
):
    """
    Get a parsed resource by its ID.
    
    Includes the full structure, claims, and evidence.
    """
    try:
        service = get_parsing_service()
        result = await service.get_parsed_resource(parsed_resource_id, include_claims)
        
        if not result:
            raise HTTPException(status_code=404, detail="Parsed resource not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parsed resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resource/{resource_id}/parsed", response_model=ParsedResource)
async def get_parsed_for_resource(
    resource_id: int,
    include_claims: bool = Query(True, description="Include claims in response"),
    user_id: int = Depends(get_user_id)
):
    """
    Get parsed data for a KB resource.
    
    Returns the most recent parse for the specified resource.
    Returns 404 if the resource hasn't been parsed yet.
    """
    try:
        service = get_parsing_service()
        result = await service.get_parsed_for_resource(resource_id, include_claims)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Resource {resource_id} has not been parsed. Use POST /arguments/parse first."
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parsed resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resource/{resource_id}/outline", response_model=ParsedResourceOutline)
async def get_resource_outline(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    Get a parsed resource as a navigable outline tree.
    
    This endpoint is optimized for frontend display with:
    - Collapsible tree structure
    - Claims organized by argument hierarchy
    - Evidence nested under claims
    - Verification status badges
    - Stats (total claims, evidence, verified count)
    
    Use this for the "Parsed View" UI component.
    """
    try:
        service = get_parsing_service()
        result = await service.get_resource_outline(resource_id, user_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Resource {resource_id} has not been parsed. Use POST /arguments/parse first."
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resource/{resource_id}/parses")
async def list_resource_parses(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    List all parses for a KB resource.
    
    Returns all parse versions (light/standard/full) with their metadata.
    Useful for showing available parses and letting user choose which to view.
    """
    try:
        service = get_parsing_service()
        parses = await service.list_parses_for_resource(resource_id, user_id)
        return {"resource_id": resource_id, "parses": parses}
        
    except Exception as e:
        logger.error(f"Failed to list parses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsed/{parsed_resource_id}/outline", response_model=ParsedResourceOutline)
async def get_outline_by_parsed_id(
    parsed_resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    Get outline for a specific parsed resource by its ID.
    
    Unlike /resource/{id}/outline which returns the most recent parse,
    this returns the outline for the exact parse specified.
    Use this when viewing a specific parse from the parses list.
    """
    try:
        service = get_parsing_service()
        result = await service.get_outline_by_parsed_id(parsed_resource_id, user_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Parsed resource {parsed_resource_id} not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resource/{resource_id}/status")
async def get_resource_parse_status(
    resource_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    Check if a resource has been parsed.
    
    Quick check without fetching full data.
    """
    try:
        service = get_parsing_service()
        parsed = await service.get_parsed_for_resource(resource_id, include_claims=False)
        
        if parsed:
            return {
                "resource_id": resource_id,
                "is_parsed": True,
                "parsed_resource_id": parsed.id,
                "parsed_at": parsed.parsed_at,
                "main_thesis": parsed.main_thesis,
                "parser_model": parsed.parser_model
            }
        else:
            return {
                "resource_id": resource_id,
                "is_parsed": False
            }
        
    except Exception as e:
        logger.error(f"Failed to check parse status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CLAIM ENDPOINTS
# ============================================================================

@router.get("/claims/{claim_id}", response_model=Claim)
async def get_claim(
    claim_id: int,
    user_id: int = Depends(get_user_id)
):
    """
    Get a single claim by ID.
    
    Includes evidence and sub-claims.
    """
    try:
        service = get_parsing_service()
        result = await service.get_claim(claim_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsed/{parsed_resource_id}/claims", response_model=List[Claim])
async def get_claims_for_parsed_resource(
    parsed_resource_id: int,
    claim_type: Optional[ClaimType] = Query(None, description="Filter by claim type"),
    verified_only: bool = Query(False, description="Only return verified claims"),
    user_id: int = Depends(get_user_id)
):
    """
    Get all claims for a parsed resource.
    
    Returns hierarchical structure with sub-claims nested.
    Optionally filter by claim type or verification status.
    """
    try:
        service = get_parsing_service()
        claims = await service.get_claims_for_resource(parsed_resource_id)
        
        # Apply filters
        if claim_type:
            claims = [c for c in claims if c.claim_type == claim_type]
        
        if verified_only:
            claims = [c for c in claims if c.verification_status == VerificationStatus.VERIFIED]
        
        return claims
        
    except Exception as e:
        logger.error(f"Failed to get claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/claims/{claim_id}", response_model=Claim)
async def update_claim(
    claim_id: int,
    update: ClaimUpdate,
    user_id: int = Depends(get_user_id)
):
    """
    Update a claim (e.g., after verification).
    
    Can update:
    - claim_text (if correction needed)
    - claim_type (if misclassified)
    - verification_status
    - verification_sources
    - verification_notes
    """
    try:
        service = get_parsing_service()
        
        # Get existing claim
        existing = await service.get_claim(claim_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Build update query dynamically
        updates = []
        params = {"id": claim_id}
        
        if update.claim_text is not None:
            updates.append("claim_text = :claim_text")
            params["claim_text"] = update.claim_text
        
        if update.claim_type is not None:
            updates.append("claim_type = :claim_type")
            params["claim_type"] = update.claim_type.value
        
        if update.verification_status is not None:
            updates.append("verification_status = :verification_status")
            params["verification_status"] = update.verification_status.value
            updates.append("verified_at = :verified_at")
            params["verified_at"] = __import__('datetime').datetime.utcnow()
        
        if update.verification_sources is not None:
            updates.append("verification_sources = :verification_sources")
            params["verification_sources"] = __import__('json').dumps(update.verification_sources)
        
        if update.verification_notes is not None:
            updates.append("verification_notes = :verification_notes")
            params["verification_notes"] = update.verification_notes
        
        if updates:
            from sqlalchemy import text
            query = f"UPDATE argument_claims SET {', '.join(updates)} WHERE id = :id"
            service.db.execute(text(query), params)
            service.db.commit()
        
        # Return updated claim
        return await service.get_claim(claim_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEARCH ENDPOINTS (placeholder for Phase 2)
# ============================================================================

@router.post("/claims/search", response_model=ClaimSearchResponse)
async def search_claims(
    query: ClaimSearchQuery,
    user_id: int = Depends(get_user_id)
):
    """
    Search for claims across parsed resources.
    
    **Coming in Phase 2:**
    - Keyword search
    - Semantic (vector) search
    - Filter by claim type, verification status
    - Filter by resource or collection
    """
    # TODO: Implement in Phase 2
    return ClaimSearchResponse(
        query=query.query,
        total_results=0,
        results=[],
        search_time_ms=0
    )


# ============================================================================
# VERIFICATION ENDPOINTS (placeholder for Phase 4)
# ============================================================================

@router.post("/claims/verify")
async def verify_claims(
    parsed_resource_id: int,
    claim_ids: Optional[List[int]] = Query(None, description="Specific claims to verify"),
    user_id: int = Depends(get_user_id)
):
    """
    Run fact-checking on extracted claims.
    
    **Coming in Phase 4:**
    - Integrates with existing F/L/W fact-checker (Factual only)
    - Updates claims with verification status
    - Attaches verification sources
    """
    # TODO: Implement in Phase 4
    return {
        "message": "Claim verification coming in Phase 4",
        "parsed_resource_id": parsed_resource_id,
        "claim_ids": claim_ids
    }


# ============================================================================
# STATS ENDPOINTS
# ============================================================================

@router.get("/stats")
async def get_argument_stats(
    user_id: int = Depends(get_user_id)
):
    """
    Get statistics about parsed resources and extracted claims.
    """
    try:
        service = get_parsing_service()
        from sqlalchemy import text
        
        # Count parsed resources
        parsed_cursor = service.db.execute(text(
            """SELECT COUNT(*) FROM parsed_resources pr
               JOIN knowledge_resources kr ON kr.id = pr.resource_id
               WHERE kr.user_id = :user_id"""
        ), {"user_id": user_id})
        parsed_result = parsed_cursor.fetchone()
        parsed_count = parsed_result[0] if parsed_result else 0
        
        # Count claims
        claims_cursor = service.db.execute(text(
            """SELECT COUNT(*), 
                      SUM(CASE WHEN claim_type = 'factual' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN claim_type = 'interpretive' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN claim_type = 'prescriptive' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN verification_status = 'verified' THEN 1 ELSE 0 END)
               FROM argument_claims ec
               JOIN parsed_resources pr ON pr.id = ec.parsed_resource_id
               JOIN knowledge_resources kr ON kr.id = pr.resource_id
               WHERE kr.user_id = :user_id"""
        ), {"user_id": user_id})
        claims_result = claims_cursor.fetchone()
        
        # Count evidence
        evidence_cursor = service.db.execute(text(
            """SELECT COUNT(*) FROM argument_evidence ee
               JOIN argument_claims ec ON ec.id = ee.claim_id
               JOIN parsed_resources pr ON pr.id = ec.parsed_resource_id
               JOIN knowledge_resources kr ON kr.id = pr.resource_id
               WHERE kr.user_id = :user_id"""
        ), {"user_id": user_id})
        evidence_result = evidence_cursor.fetchone()
        evidence_count = evidence_result[0] if evidence_result else 0
        
        return {
            "parsed_resources": parsed_count,
            "total_claims": claims_result[0] if claims_result else 0,
            "claims_by_type": {
                "factual": claims_result[1] or 0 if claims_result else 0,
                "interpretive": claims_result[2] or 0 if claims_result else 0,
                "prescriptive": claims_result[3] or 0 if claims_result else 0
            },
            "verified_claims": claims_result[4] or 0 if claims_result else 0,
            "total_evidence": evidence_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def arguments_health():
    """Check Argument Builder service health."""
    try:
        service = get_parsing_service()
        
        return {
            "status": "healthy" if service.is_initialized() else "degraded",
            "parsing_service": "initialized" if service.is_initialized() else "not initialized",
            "llm_router": "available" if service.llm_router else "not configured",
            "database": "connected" if service.db else "not connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================================================
# MODEL SELECTION
# ============================================================================

@router.get("/models")
async def get_available_models():
    """
    Get available LLM providers and models for parsing.
    
    Returns providers with their models, costs, and capabilities.
    Use this to populate model selection dropdowns.
    """
    try:
        service = get_parsing_service()
        
        if not service.llm_router:
            return {
                "providers": [],
                "error": "LLM router not configured"
            }
        
        router = service.llm_router
        available_providers = router.get_available_providers()
        
        providers = []
        for provider_name in available_providers:
            models = router.get_models(provider_name)
            current = router.get_current_model(provider_name)
            
            providers.append({
                "name": provider_name,
                "default_model": current.get('model_id'),
                "models": models
            })
        
        return {
            "active_provider": router.active_provider,
            "providers": providers
        }
        
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        return {
            "providers": [],
            "error": str(e)
        }
