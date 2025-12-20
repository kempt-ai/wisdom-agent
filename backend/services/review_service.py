"""
Wisdom Agent - Fact Checker Review Service

Main orchestrator for the fact checking feature.
Coordinates content extraction, claim analysis, fact checking,
logic analysis, and wisdom evaluation.

Author: Wisdom Agent Team  
Date: 2025-12-18
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import joinedload

from backend.database.connection import get_db_session
from backend.database.fact_check_models import (
    ContentReview, SourceMetadata, ExtractedClaim,
    FactCheckResult, LogicAnalysis, WisdomEvaluation,
    ReviewStatus, SourceType
)
from backend.models.review_models import (
    ReviewCreateRequest, ReviewListResponse, ReviewDetailResponse,
    ReviewSummaryResponse, ReviewStatusResponse
)

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Main orchestrator for fact checking functionality.
    
    This service:
    - Creates and manages reviews
    - Coordinates the analysis pipeline
    - Integrates with session management
    """
    
    def __init__(self):
        """Initialize the review service."""
        # These will be initialized on first use
        self._content_extraction_service = None
        self._claim_extraction_service = None
        self._fact_check_service = None
        self._logic_analysis_service = None
        self._wisdom_evaluation_service = None
    
    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    async def create_review(self, request: ReviewCreateRequest) -> ReviewSummaryResponse:
        """
        Create a new fact check review.
        
        If no session_id is provided, creates a new session for this fact check.
        """
        with get_db_session() as db:
            try:
                # Get or create session
                session_id = request.session_id
                if session_id is None:
                    # Create a new session for this standalone fact check
                    session_id = await self._create_fact_check_session(db, request)
                
                # Get content based on source type
                source_content = ""
                if request.source_type == SourceType.URL:
                    source_content = request.source_url  # Will be fetched during analysis
                elif request.source_type == SourceType.TEXT:
                    source_content = request.source_content
                elif request.source_type == SourceType.FILE:
                    source_content = f"file:{request.file_id}"  # Will be loaded during analysis
                
                # Create the review record
                review = ContentReview(
                    session_id=session_id,
                    project_id=request.project_id,
                    user_id=1,  # TODO: Get from auth context
                    title=request.title,
                    source_type=request.source_type,
                    source_url=request.source_url,
                    source_content=source_content,
                    status=ReviewStatus.PENDING,
                )
                
                db.add(review)
                db.commit()
                db.refresh(review)
                
                logger.info(f"Created review {review.id} for session {session_id}")
                
                return self._to_summary_response(review)
                
            except Exception as e:
                db.rollback()
                logger.exception(f"Error creating review: {e}")
                raise
    
    async def list_reviews(
        self,
        project_id: Optional[int] = None,
        session_id: Optional[int] = None,
        status: Optional[ReviewStatus] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> ReviewListResponse:
        """List reviews with filtering and pagination."""
        with get_db_session() as db:
            # Build query
            query = select(ContentReview)
            
            # Apply filters
            conditions = []
            if project_id is not None:
                conditions.append(ContentReview.project_id == project_id)
            if session_id is not None:
                conditions.append(ContentReview.session_id == session_id)
            if status is not None:
                conditions.append(ContentReview.status == status)
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        ContentReview.title.ilike(search_term),
                        ContentReview.source_url.ilike(search_term)
                    )
                )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total = db.execute(count_query).scalar()
            
            # Apply pagination and ordering
            query = query.order_by(desc(ContentReview.created_at))
            query = query.limit(limit).offset(offset)
            
            # Execute
            reviews = db.execute(query).scalars().all()
            
            return ReviewListResponse(
                items=[self._to_summary_response(r) for r in reviews],
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(reviews)) < total
            )
    
    async def get_review(self, review_id: int) -> Optional[ReviewDetailResponse]:
        """Get a review with all details."""
        with get_db_session() as db:
            query = (
                select(ContentReview)
                .options(
                    joinedload(ContentReview.source_metadata),
                    joinedload(ContentReview.claims).joinedload(ExtractedClaim.fact_check_result),
                    joinedload(ContentReview.logic_analysis),
                    joinedload(ContentReview.wisdom_evaluation),
                )
                .where(ContentReview.id == review_id)
            )
            
            review = db.execute(query).unique().scalar_one_or_none()
            
            if not review:
                return None
            
            return self._to_detail_response(review)
    
    async def delete_review(self, review_id: int) -> bool:
        """Delete a review and all associated data."""
        with get_db_session() as db:
            review = db.get(ContentReview, review_id)
            if not review:
                return False
            
            db.delete(review)  # Cascades to related records
            db.commit()
            
            logger.info(f"Deleted review {review_id}")
            return True
    
    async def get_review_status(self, review_id: int) -> Optional[ReviewStatusResponse]:
        """Get current status of a review."""
        with get_db_session() as db:
            review = db.get(ContentReview, review_id)
            if not review:
                return None
            
            # Generate progress message based on status
            progress_messages = {
                ReviewStatus.PENDING: "Waiting to start...",
                ReviewStatus.EXTRACTING: "Extracting content from source...",
                ReviewStatus.ANALYZING_CLAIMS: "Identifying claims in content...",
                ReviewStatus.FACT_CHECKING: "Verifying claims against sources...",
                ReviewStatus.LOGIC_ANALYSIS: "Analyzing logical structure...",
                ReviewStatus.WISDOM_EVALUATION: "Evaluating against 7 Universal Values...",
                ReviewStatus.COMPLETED: "Analysis complete!",
                ReviewStatus.FAILED: "Analysis failed.",
            }
            
            return ReviewStatusResponse(
                id=review.id,
                status=review.status,
                error_message=review.error_message,
                progress_message=progress_messages.get(review.status, "Processing..."),
                completed_at=review.completed_at
            )
    
    async def reset_review_status(self, review_id: int):
        """Reset a review to pending status for re-analysis."""
        with get_db_session() as db:
            review = db.get(ContentReview, review_id)
            if review:
                review.status = ReviewStatus.PENDING
                review.error_message = None
                review.completed_at = None
                db.commit()
    
    async def get_reviews_for_session(self, session_id: int) -> List[ReviewSummaryResponse]:
        """Get all reviews linked to a session."""
        with get_db_session() as db:
            query = (
                select(ContentReview)
                .where(ContentReview.session_id == session_id)
                .order_by(desc(ContentReview.created_at))
            )
            reviews = db.execute(query).scalars().all()
            return [self._to_summary_response(r) for r in reviews]
    
    # ========================================================================
    # ANALYSIS PIPELINE
    # ========================================================================
    
    async def run_analysis(self, review_id: int):
        """
        Run the full analysis pipeline for a review.
        
        Pipeline steps:
        1. Content extraction (fetch URL, parse file, etc.)
        2. Claim extraction (identify claims in content)
        3. Fact checking (verify claims)
        4. Logic analysis (check argument structure)
        5. Wisdom evaluation (7 Values + Something Deeperism)
        """
        logger.info(f"Starting analysis for review {review_id}")
        
        try:
            # Step 1: Extract content
            await self._update_status(review_id, ReviewStatus.EXTRACTING)
            content = await self._extract_content(review_id)
            
            # Step 2: Extract claims
            await self._update_status(review_id, ReviewStatus.ANALYZING_CLAIMS)
            claims = await self._extract_claims(review_id, content)
            
            # Step 3: Fact check claims
            await self._update_status(review_id, ReviewStatus.FACT_CHECKING)
            await self._fact_check_claims(review_id, claims)
            
            # Step 4: Logic analysis
            await self._update_status(review_id, ReviewStatus.LOGIC_ANALYSIS)
            await self._analyze_logic(review_id, content)
            
            # Step 5: Wisdom evaluation
            await self._update_status(review_id, ReviewStatus.WISDOM_EVALUATION)
            await self._evaluate_wisdom(review_id, content)
            
            # Step 6: Generate summary and complete
            await self._generate_summary(review_id)
            await self._update_status(review_id, ReviewStatus.COMPLETED)
            
            logger.info(f"Completed analysis for review {review_id}")
            
        except Exception as e:
            logger.exception(f"Analysis failed for review {review_id}: {e}")
            await self._update_status(review_id, ReviewStatus.FAILED, str(e))
    
    # ========================================================================
    # PIPELINE STEPS (to be implemented with actual services)
    # ========================================================================
    
    async def _extract_content(self, review_id: int) -> str:
        """Extract and clean content from the source."""
        # TODO: Implement with ContentExtractionService
        # For now, return placeholder
        with get_db_session() as db:
            review = db.get(ContentReview, review_id)
            if review.source_type == SourceType.URL:
                # Fetch URL content
                logger.info(f"Would fetch URL: {review.source_url}")
                return f"[Content from {review.source_url}]"
            elif review.source_type == SourceType.TEXT:
                return review.source_content
            else:
                return review.source_content
    
    async def _extract_claims(self, review_id: int, content: str) -> List[Dict[str, Any]]:
        """Identify claims in the content."""
        # TODO: Implement with ClaimExtractionService
        # For now, create placeholder claims
        logger.info(f"Would extract claims from content for review {review_id}")
        return []
    
    async def _fact_check_claims(self, review_id: int, claims: List[Dict[str, Any]]):
        """Verify extracted claims."""
        # TODO: Implement with FactCheckService
        logger.info(f"Would fact check {len(claims)} claims for review {review_id}")
    
    async def _analyze_logic(self, review_id: int, content: str):
        """Analyze logical structure and fallacies."""
        # TODO: Implement with LogicAnalysisService
        logger.info(f"Would analyze logic for review {review_id}")
    
    async def _evaluate_wisdom(self, review_id: int, content: str):
        """Evaluate against 7 Universal Values and Something Deeperism."""
        # TODO: Implement with WisdomEvaluationService
        logger.info(f"Would evaluate wisdom for review {review_id}")
    
    async def _generate_summary(self, review_id: int):
        """Generate quick summary from all analysis results."""
        # TODO: Combine results into summary
        logger.info(f"Would generate summary for review {review_id}")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _create_fact_check_session(self, db, request: ReviewCreateRequest) -> int:
        """Create a new session for a standalone fact check."""
        # Import here to avoid circular imports
        from backend.database.models import Session
        
        # Create session with fact-check type
        session = Session(
            user_id=1,  # TODO: Get from auth context
            project_id=request.project_id,
            title=f"Fact Check: {request.title or request.source_url or 'New Analysis'}",
            # session_type="fact_check",  # If your Session model has this field
        )
        
        db.add(session)
        db.flush()  # Get the ID without committing
        
        logger.info(f"Created fact-check session {session.id}")
        return session.id
    
    async def _update_status(
        self, 
        review_id: int, 
        status: ReviewStatus, 
        error_message: Optional[str] = None
    ):
        """Update the status of a review."""
        with get_db_session() as db:
            review = db.get(ContentReview, review_id)
            if review:
                review.status = status
                review.error_message = error_message
                if status == ReviewStatus.COMPLETED:
                    review.completed_at = datetime.utcnow()
                db.commit()
    
    def _to_summary_response(self, review: ContentReview) -> ReviewSummaryResponse:
        """Convert database model to summary response."""
        return ReviewSummaryResponse(
            id=review.id,
            title=review.title,
            source_type=review.source_type,
            source_url=review.source_url,
            status=review.status,
            quick_summary=review.quick_summary,
            overall_factual_verdict=review.overall_factual_verdict,
            overall_wisdom_verdict=review.overall_wisdom_verdict,
            confidence_score=review.confidence_score,
            session_id=review.session_id,
            project_id=review.project_id,
            created_at=review.created_at,
            completed_at=review.completed_at,
        )
    
    def _to_detail_response(self, review: ContentReview) -> ReviewDetailResponse:
        """Convert database model to detail response."""
        # Build nested responses
        source_metadata = None
        if review.source_metadata:
            from backend.models.review_models import SourceMetadataResponse
            source_metadata = SourceMetadataResponse(
                author=review.source_metadata.author,
                publication=review.source_metadata.publication,
                publish_date=review.source_metadata.publish_date,
                domain=review.source_metadata.domain,
                credibility_score=review.source_metadata.credibility_score,
                credibility_notes=review.source_metadata.credibility_notes,
            )
        
        claims = []
        for claim in review.claims:
            from backend.models.review_models import (
                ExtractedClaimResponse, FactCheckResultResponse
            )
            fact_check = None
            if claim.fact_check_result:
                fact_check = FactCheckResultResponse(
                    verdict=claim.fact_check_result.verdict,
                    confidence=claim.fact_check_result.confidence,
                    explanation=claim.fact_check_result.explanation,
                    providers_used=claim.fact_check_result.providers_used,
                    external_matches=claim.fact_check_result.external_matches,
                    web_sources=claim.fact_check_result.web_sources,
                )
            
            claims.append(ExtractedClaimResponse(
                id=claim.id,
                claim_text=claim.claim_text,
                claim_type=claim.claim_type,
                source_location=claim.source_location,
                source_quote=claim.source_quote,
                check_worthiness_score=claim.check_worthiness_score,
                fact_check_result=fact_check,
            ))
        
        logic_analysis = None
        if review.logic_analysis:
            from backend.models.review_models import LogicAnalysisResponse, FallacyFinding
            logic_analysis = LogicAnalysisResponse(
                main_conclusion=review.logic_analysis.main_conclusion,
                premises=review.logic_analysis.premises,
                unstated_assumptions=review.logic_analysis.unstated_assumptions,
                fallacies_found=[
                    FallacyFinding(**f) for f in (review.logic_analysis.fallacies_found or [])
                ],
                validity_assessment=review.logic_analysis.validity_assessment,
                soundness_assessment=review.logic_analysis.soundness_assessment,
                alternative_interpretations=review.logic_analysis.alternative_interpretations,
                logic_quality_score=review.logic_analysis.logic_quality_score,
                confidence=review.logic_analysis.confidence,
            )
        
        wisdom_evaluation = None
        if review.wisdom_evaluation:
            from backend.models.review_models import WisdomEvaluationResponse, ValueAssessment
            we = review.wisdom_evaluation
            
            def make_value(score, notes):
                if score is not None:
                    return ValueAssessment(score=score, notes=notes or "")
                return None
            
            wisdom_evaluation = WisdomEvaluationResponse(
                awareness=make_value(we.awareness_score, we.awareness_notes),
                honesty=make_value(we.honesty_score, we.honesty_notes),
                accuracy=make_value(we.accuracy_score, we.accuracy_notes),
                competence=make_value(we.competence_score, we.competence_notes),
                compassion=make_value(we.compassion_score, we.compassion_notes),
                loving_kindness=make_value(we.loving_kindness_score, we.loving_kindness_notes),
                joyful_sharing=make_value(we.joyful_sharing_score, we.joyful_sharing_notes),
                something_deeperism_assessment=we.something_deeperism_assessment,
                claims_unwarranted_certainty=we.claims_unwarranted_certainty,
                treats_complex_truths_dogmatically=we.treats_complex_truths_dogmatically,
                acknowledges_limits_of_understanding=we.acknowledges_limits_of_understanding,
                serves_pure_love=we.serves_pure_love,
                fosters_or_squelches_sd=we.fosters_or_squelches_sd,
                overall_wisdom_score=we.overall_wisdom_score,
                serves_wisdom_or_folly=we.serves_wisdom_or_folly,
                final_reflection=we.final_reflection,
                is_it_true=we.is_it_true_assessment,
                is_it_reasonable=we.is_it_reasonable_assessment,
                does_it_serve_wisdom=we.does_it_serve_wisdom_assessment,
                three_questions_interaction=we.three_questions_interaction,
            )
        
        return ReviewDetailResponse(
            id=review.id,
            title=review.title,
            source_type=review.source_type,
            source_url=review.source_url,
            source_content=review.source_content,
            status=review.status,
            error_message=review.error_message,
            quick_summary=review.quick_summary,
            overall_factual_verdict=review.overall_factual_verdict,
            overall_wisdom_verdict=review.overall_wisdom_verdict,
            confidence_score=review.confidence_score,
            session_id=review.session_id,
            project_id=review.project_id,
            user_id=review.user_id,
            source_metadata=source_metadata,
            claims=claims,
            logic_analysis=logic_analysis,
            wisdom_evaluation=wisdom_evaluation,
            created_at=review.created_at,
            updated_at=review.updated_at,
            completed_at=review.completed_at,
        )
