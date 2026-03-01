"""
Investigation Builder (AB) API Router

REST endpoints for:
- Investigation CRUD (list, create, get, update, delete)
- Definition CRUD within investigations
- Claim CRUD within investigations
- Evidence CRUD on claims
- Counterargument CRUD on claims

All endpoints prefixed with /ab/ (set by main.py include_router).

Follows patterns from knowledge.py and arguments.py routers.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
import logging

from backend.models.ab_schemas import (
    # Investigations
    Investigation, InvestigationSummary, InvestigationCreate, InvestigationUpdate,
    # Definitions
    Definition, DefinitionCreate, DefinitionUpdate,
    # Claims
    ABClaim, ABClaimCreate, ABClaimUpdate,
    # Evidence
    ABEvidence, ABEvidenceCreate, ABEvidenceUpdate,
    # Counterarguments
    Counterargument, CounterargumentCreate, CounterargumentUpdate,
)

from backend.services.ab_service import (
    get_ab_service,
    InvestigationNotFoundError,
    DefinitionNotFoundError,
    ClaimNotFoundError,
    EvidenceNotFoundError,
    CounterargumentNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ab", tags=["Investigation Builder"])


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_user_id() -> int:
    """Get current user ID. TODO: Replace with real auth."""
    return 1


# ============================================================================
# INVESTIGATION ENDPOINTS
# ============================================================================

@router.get("/investigations", response_model=List[InvestigationSummary])
async def list_investigations():
    """List all investigations with summary counts."""
    try:
        service = get_ab_service()
        if not service.is_initialized():
            raise HTTPException(status_code=503, detail="Investigation Builder service not initialized")
        return await service.list_investigations()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list investigations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/investigations", response_model=Investigation, status_code=201)
async def create_investigation(data: InvestigationCreate):
    """Create a new investigation."""
    try:
        service = get_ab_service()
        if not service.is_initialized():
            raise HTTPException(status_code=503, detail="Investigation Builder service not initialized")
        return await service.create_investigation(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigations/{slug}", response_model=Investigation)
async def get_investigation(slug: str):
    """Get an investigation by slug, including definitions and claims."""
    try:
        service = get_ab_service()
        if not service.is_initialized():
            raise HTTPException(status_code=503, detail="Investigation Builder service not initialized")

        result = await service.get_investigation(slug)
        if not result:
            raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/investigations/{slug}", response_model=Investigation)
async def update_investigation(slug: str, data: InvestigationUpdate):
    """Update an investigation."""
    try:
        service = get_ab_service()
        return await service.update_investigation(slug, data)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except Exception as e:
        logger.error(f"Failed to update investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/investigations/{slug}", status_code=204)
async def delete_investigation(slug: str):
    """Delete an investigation and all its contents."""
    try:
        service = get_ab_service()
        await service.delete_investigation(slug)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except Exception as e:
        logger.error(f"Failed to delete investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DEFINITION ENDPOINTS
# ============================================================================

@router.get("/investigations/{slug}/definitions", response_model=List[Definition])
async def list_definitions(slug: str):
    """List all definitions for an investigation."""
    try:
        service = get_ab_service()
        return await service.list_definitions(slug)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except Exception as e:
        logger.error(f"Failed to list definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/investigations/{slug}/definitions", response_model=Definition, status_code=201)
async def create_definition(slug: str, data: DefinitionCreate):
    """Create a definition within an investigation."""
    try:
        service = get_ab_service()
        return await service.create_definition(slug, data)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except Exception as e:
        logger.error(f"Failed to create definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigations/{slug}/definitions/{def_slug}", response_model=Definition)
async def get_definition(slug: str, def_slug: str):
    """Get a definition by slug."""
    try:
        service = get_ab_service()
        result = await service.get_definition(slug, def_slug)
        if not result:
            raise HTTPException(status_code=404, detail=f"Definition '{def_slug}' not found")
        return result
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/investigations/{slug}/definitions/{def_slug}", response_model=Definition)
async def update_definition(slug: str, def_slug: str, data: DefinitionUpdate):
    """Update a definition."""
    try:
        service = get_ab_service()
        return await service.update_definition(slug, def_slug, data)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except DefinitionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{def_slug}' not found")
    except Exception as e:
        logger.error(f"Failed to update definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/investigations/{slug}/definitions/{def_slug}", status_code=204)
async def delete_definition(slug: str, def_slug: str):
    """Delete a definition."""
    try:
        service = get_ab_service()
        await service.delete_definition(slug, def_slug)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except DefinitionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{def_slug}' not found")
    except Exception as e:
        logger.error(f"Failed to delete definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CLAIM ENDPOINTS
# ============================================================================

@router.get("/investigations/{slug}/claims", response_model=List[ABClaim])
async def list_claims(slug: str):
    """List all claims for an investigation."""
    try:
        service = get_ab_service()
        return await service.list_claims(slug)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except Exception as e:
        logger.error(f"Failed to list claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/investigations/{slug}/claims", response_model=ABClaim, status_code=201)
async def create_claim(slug: str, data: ABClaimCreate):
    """Create a claim within an investigation."""
    try:
        service = get_ab_service()
        return await service.create_claim(slug, data)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except Exception as e:
        logger.error(f"Failed to create claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigations/{slug}/claims/{claim_slug}", response_model=ABClaim)
async def get_claim(slug: str, claim_slug: str):
    """Get a claim by slug with evidence and counterarguments."""
    try:
        service = get_ab_service()
        result = await service.get_claim(slug, claim_slug)
        if not result:
            raise HTTPException(status_code=404, detail=f"Claim '{claim_slug}' not found")
        return result
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/investigations/{slug}/claims/{claim_slug}", response_model=ABClaim)
async def update_claim(slug: str, claim_slug: str, data: ABClaimUpdate):
    """Update a claim."""
    try:
        service = get_ab_service()
        return await service.update_claim(slug, claim_slug, data)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_slug}' not found")
    except Exception as e:
        logger.error(f"Failed to update claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/investigations/{slug}/claims/{claim_slug}", status_code=204)
async def delete_claim(slug: str, claim_slug: str):
    """Delete a claim and its children."""
    try:
        service = get_ab_service()
        await service.delete_claim(slug, claim_slug)
    except InvestigationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Investigation '{slug}' not found")
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_slug}' not found")
    except Exception as e:
        logger.error(f"Failed to delete claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EVIDENCE ENDPOINTS
# ============================================================================

@router.get("/claims/{claim_id}/evidence", response_model=List[ABEvidence])
async def list_evidence(claim_id: int):
    """List evidence for a claim."""
    try:
        service = get_ab_service()
        return await service._get_evidence_for_claim(claim_id)
    except Exception as e:
        logger.error(f"Failed to list evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/claims/{claim_id}/evidence", response_model=ABEvidence, status_code=201)
async def add_evidence(claim_id: int, data: ABEvidenceCreate):
    """Add evidence to a claim."""
    try:
        service = get_ab_service()
        return await service.add_evidence(claim_id, data)
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    except Exception as e:
        logger.error(f"Failed to add evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/evidence/{evidence_id}", response_model=ABEvidence)
async def update_evidence(evidence_id: int, data: ABEvidenceUpdate):
    """Update an evidence item."""
    try:
        service = get_ab_service()
        return await service.update_evidence(evidence_id, data)
    except EvidenceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")
    except Exception as e:
        logger.error(f"Failed to update evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/evidence/{evidence_id}", status_code=204)
async def delete_evidence(evidence_id: int):
    """Delete an evidence item."""
    try:
        service = get_ab_service()
        await service.delete_evidence(evidence_id)
    except EvidenceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REORDER ENDPOINTS
# ============================================================================

@router.post("/claims/{claim_id}/reorder", status_code=200)
async def reorder_claim(
    claim_id: int,
    direction: str = Query(..., pattern="^(up|down)$"),
):
    """Move a claim up or down within its investigation."""
    try:
        service = get_ab_service()
        moved = await service.reorder_claim(claim_id, direction)
        return {"moved": moved}
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    except Exception as e:
        logger.error(f"Failed to reorder claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evidence/{evidence_id}/reorder", status_code=200)
async def reorder_evidence(
    evidence_id: int,
    direction: str = Query(..., pattern="^(up|down)$"),
):
    """Move an evidence item up or down within its claim."""
    try:
        service = get_ab_service()
        moved = await service.reorder_evidence(evidence_id, direction)
        return {"moved": moved}
    except EvidenceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")
    except Exception as e:
        logger.error(f"Failed to reorder evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COUNTERARGUMENT ENDPOINTS
# ============================================================================

@router.get("/claims/{claim_id}/counterarguments", response_model=List[Counterargument])
async def list_counterarguments(claim_id: int):
    """List counterarguments for a claim."""
    try:
        service = get_ab_service()
        return await service._get_counterarguments_for_claim(claim_id)
    except Exception as e:
        logger.error(f"Failed to list counterarguments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/claims/{claim_id}/counterarguments", response_model=Counterargument, status_code=201)
async def add_counterargument(claim_id: int, data: CounterargumentCreate):
    """Add a counterargument to a claim."""
    try:
        service = get_ab_service()
        return await service.add_counterargument(claim_id, data)
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    except Exception as e:
        logger.error(f"Failed to add counterargument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/counterarguments/{ca_id}", response_model=Counterargument)
async def update_counterargument(ca_id: int, data: CounterargumentUpdate):
    """Update a counterargument (e.g., add rebuttal)."""
    try:
        service = get_ab_service()
        return await service.update_counterargument(ca_id, data)
    except CounterargumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Counterargument {ca_id} not found")
    except Exception as e:
        logger.error(f"Failed to update counterargument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/counterarguments/{ca_id}", status_code=204)
async def delete_counterargument(ca_id: int):
    """Delete a counterargument."""
    try:
        service = get_ab_service()
        await service.delete_counterargument(ca_id)
    except CounterargumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Counterargument {ca_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete counterargument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/counterarguments/{ca_id}/reorder", status_code=200)
async def reorder_counterargument(
    ca_id: int,
    direction: str = Query(..., pattern="^(up|down)$"),
):
    """Move a counterargument up or down within its claim."""
    try:
        service = get_ab_service()
        moved = await service.reorder_counterargument(ca_id, direction)
        return {"moved": moved}
    except CounterargumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Counterargument {ca_id} not found")
    except Exception as e:
        logger.error(f"Failed to reorder counterargument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def ab_health():
    """Check Investigation Builder service health."""
    try:
        service = get_ab_service()
        return {
            "status": "healthy" if service.is_initialized() else "degraded",
            "database": "connected" if service.db else "not connected",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
