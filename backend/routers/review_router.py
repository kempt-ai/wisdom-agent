"""
Wisdom Agent - Fact Checker API Router

FastAPI router providing endpoints for fact checking functionality.
Integrates with the existing Wisdom Agent API structure.

Author: Wisdom Agent Team
Date: 2025-12-18
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks

from backend.models.review_models import (
    ReviewCreateRequest, ReviewListRequest, ReviewListResponse,
    ReviewDetailResponse, ReviewSummaryResponse, ReviewStatusResponse,
    SourceType, ReviewStatus
)
from backend.services.review_service import ReviewService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/reviews",
    tags=["Fact Checker"],
    responses={404: {"description": "Not found"}},
)

# Service instance (will be properly injected via dependency injection)
# For now, we instantiate directly - you can update this to use FastAPI's Depends
_review_service: Optional[ReviewService] = None


def get_review_service() -> ReviewService:
    """Get or create the review service instance."""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service


# ============================================================================
# CREATE & LIST ENDPOINTS
# ============================================================================

@router.post("", response_model=ReviewSummaryResponse, status_code=201)
async def create_review(
    request: ReviewCreateRequest,
    background_tasks: BackgroundTasks,
    service: ReviewService = Depends(get_review_service)
):
    """
    Create a new fact check review.
    
    The analysis runs in the background. Poll the status endpoint to check progress.
    
    - **source_type**: "url", "text", or "file"
    - **source_url**: Required if source_type is "url"
    - **source_content**: Required if source_type is "text"
    - **file_id**: Required if source_type is "file"
    - **session_id**: Optional - link to existing session (for mid-session fact checks)
    - **project_id**: Optional - associate with a project
    """
    try:
        # Validate input based on source type
        if request.source_type == SourceType.URL and not request.source_url:
            raise HTTPException(status_code=400, detail="source_url is required when source_type is 'url'")
        if request.source_type == SourceType.TEXT and not request.source_content:
            raise HTTPException(status_code=400, detail="source_content is required when source_type is 'text'")
        if request.source_type == SourceType.FILE and not request.file_id:
            raise HTTPException(status_code=400, detail="file_id is required when source_type is 'file'")
        
        # Create the review
        review = await service.create_review(request)
        
        # Start analysis in background
        background_tasks.add_task(service.run_analysis, review.id)
        
        return review
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    project_id: Optional[int] = Query(None, description="Filter by project"),
    session_id: Optional[int] = Query(None, description="Filter by session"),
    status: Optional[ReviewStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title and URL"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: ReviewService = Depends(get_review_service)
):
    """
    List fact check reviews.
    
    Supports filtering by project, session, status, and search.
    Results are paginated and sorted by creation date (newest first).
    """
    try:
        result = await service.list_reviews(
            project_id=project_id,
            session_id=session_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset
        )
        return result
        
    except Exception as e:
        logger.exception(f"Error listing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SINGLE REVIEW ENDPOINTS
# ============================================================================

@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(
    review_id: int,
    service: ReviewService = Depends(get_review_service)
):
    """
    Get a fact check review with full details.
    
    Includes:
    - Source metadata
    - All extracted claims with fact check results
    - Logic analysis
    - Wisdom evaluation (7 Universal Values + Something Deeperism)
    """
    try:
        review = await service.get_review(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting review {review_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    service: ReviewService = Depends(get_review_service)
):
    """
    Delete a fact check review.
    
    This also deletes all associated claims, results, and evaluations.
    """
    try:
        success = await service.delete_review(review_id)
        if not success:
            raise HTTPException(status_code=404, detail="Review not found")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting review {review_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{review_id}/status", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: int,
    service: ReviewService = Depends(get_review_service)
):
    """
    Get the current status of a review.
    
    Use this endpoint to poll for progress during analysis.
    """
    try:
        status = await service.get_review_status(review_id)
        if not status:
            raise HTTPException(status_code=404, detail="Review not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting review status {review_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYSIS ENDPOINTS (for manual re-runs if needed)
# ============================================================================

@router.post("/{review_id}/analyze", response_model=ReviewStatusResponse)
async def run_analysis(
    review_id: int,
    background_tasks: BackgroundTasks,
    service: ReviewService = Depends(get_review_service)
):
    """
    Manually trigger analysis for a review.
    
    Useful for re-running failed analyses.
    """
    try:
        review = await service.get_review(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Reset status and run analysis
        await service.reset_review_status(review_id)
        background_tasks.add_task(service.run_analysis, review_id)
        
        return await service.get_review_status(review_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting analysis for review {review_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SESSION LINK ENDPOINTS
# ============================================================================

@router.get("/session/{session_id}", response_model=List[ReviewSummaryResponse])
async def get_reviews_for_session(
    session_id: int,
    service: ReviewService = Depends(get_review_service)
):
    """
    Get all fact check reviews linked to a session.
    """
    try:
        reviews = await service.get_reviews_for_session(session_id)
        return reviews
        
    except Exception as e:
        logger.exception(f"Error getting reviews for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REPOSITORY BROWSER ENDPOINT (for dedicated fact-check browsing)
# ============================================================================

@router.get("/repository/all", response_model=ReviewListResponse)
async def browse_all_reviews(
    search: Optional[str] = Query(None, description="Search in title and URL"),
    factual_verdict: Optional[str] = Query(None, description="Filter by factual verdict"),
    wisdom_verdict: Optional[str] = Query(None, description="Filter by wisdom verdict"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ReviewService = Depends(get_review_service)
):
    """
    Browse all fact check reviews across all sessions.
    
    This is the dedicated fact-check repository view.
    Returns reviews regardless of which session they belong to.
    """
    try:
        result = await service.list_reviews(
            project_id=None,
            session_id=None,  # All sessions
            status=ReviewStatus.COMPLETED,  # Only show completed reviews
            search=search,
            limit=limit,
            offset=offset
        )
        return result
        
    except Exception as e:
        logger.exception(f"Error browsing review repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))
