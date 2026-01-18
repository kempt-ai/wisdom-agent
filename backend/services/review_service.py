"""
Wisdom Agent - Fact Checker Review Service (Updated for Phase 2)

Main orchestrator for the fact checking feature.
Coordinates content extraction, claim analysis, fact checking,
logic analysis, and wisdom evaluation.

Author: Wisdom Agent Team  
Date: 2025-12-18 (Phase 1)
Updated: 2025-12-20 (Phase 2 - Full Integration)
Updated: 2025-12-30 (Fixed session_number NULL constraint bug)
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
    ReviewStatus, SourceType, FactualVerdict
)
from backend.models.review_models import (
    ReviewCreateRequest, ReviewListResponse, ReviewDetailResponse,
    ReviewSummaryResponse, ReviewStatusResponse
)

# Phase 2 service imports
from backend.services.content_extraction_service import (
    get_content_extraction_service, ContentExtractionError, PaywallDetectedError
)
from backend.services.claim_extraction_service import (
    get_claim_extraction_service, ClaimExtractionError
)
from backend.services.fact_check_service import get_fact_check_service
from backend.services.logic_analysis_service import (
    get_logic_analysis_service, LogicAnalysisError
)
from backend.services.wisdom_evaluation_service import (
    get_wisdom_evaluation_service, WisdomEvaluationError
)

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Main orchestrator for fact checking functionality.
    
    This service:
    - Creates and manages reviews
    - Coordinates the analysis pipeline
    - Integrates with session management
    
    Phase 2 Update: Now fully integrated with all analysis services.
    """
    
    def __init__(self):
        """Initialize the review service."""
        # Services are initialized lazily to avoid circular imports
        self._content_extraction_service = None
        self._claim_extraction_service = None
        self._fact_check_service = None
        self._logic_analysis_service = None
        self._wisdom_evaluation_service = None
    
    # ========================================================================
    # SERVICE GETTERS (Lazy initialization)
    # ========================================================================
    
    def _get_content_extraction(self):
        if self._content_extraction_service is None:
            self._content_extraction_service = get_content_extraction_service()
        return self._content_extraction_service
    
    def _get_claim_extraction(self):
        if self._claim_extraction_service is None:
            self._claim_extraction_service = get_claim_extraction_service()
        return self._claim_extraction_service
    
    def _get_fact_check(self):
        if self._fact_check_service is None:
            self._fact_check_service = get_fact_check_service()
        return self._fact_check_service
    
    def _get_logic_analysis(self):
        if self._logic_analysis_service is None:
            self._logic_analysis_service = get_logic_analysis_service()
        return self._logic_analysis_service
    
    def _get_wisdom_evaluation(self):
        if self._wisdom_evaluation_service is None:
            self._wisdom_evaluation_service = get_wisdom_evaluation_service()
        return self._wisdom_evaluation_service
    # ========================================================================
    # COST ESTIMATION
    # ========================================================================
    
    async def estimate_fact_check_cost(
        self,
        source_type: SourceType,
        source_content: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate the cost of a fact-check operation before running it.
        
        For URLs, fetches the content first to get accurate token count.
        
        Returns dict with:
        - input_tokens: estimated input tokens
        - estimates_by_model: list of {model, provider, cost, tier}
        - recommended_model: best value recommendation
        """
        from backend.services.llm_router import get_llm_router, PROVIDER_MODELS
        
        # Get content length
        if source_type == SourceType.URL and source_url:
            # Fetch URL to estimate content size
            try:
                service = self._get_content_extraction()
                client = await service.get_http_client()
                response = await client.get(source_url)
                response.raise_for_status()
                
                # Quick extraction for size estimate
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                # Remove script/style
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)
                content = text[:50000]  # Cap for estimation
            except Exception as e:
                # If fetch fails, estimate based on typical article
                content = "x" * 8000  # ~2000 tokens typical article
        elif source_type == SourceType.TEXT and source_content:
            content = source_content
        else:
            content = "x" * 4000  # Default estimate
        
        # Estimate tokens (rough: 4 chars per token)
        input_tokens = len(content) // 4
        
        # Fact-check pipeline uses multiple LLM calls:
        # 1. Claim extraction: input + ~2000 output
        # 2. Fact verification: ~500 input per claim × ~10 claims, ~300 output each
        # 3. Logic analysis: input + ~1500 output  
        # 4. Wisdom evaluation: input + summaries (~2000) + ~2000 output
        
        # Total estimated tokens for full pipeline
        estimated_claims = min(20, max(3, input_tokens // 500))  # Rough claim count
        
        total_input = (
            input_tokens +                          # Claim extraction
            (500 * estimated_claims) +              # Fact check per claim
            input_tokens +                          # Logic analysis
            (input_tokens + 2000)                   # Wisdom (content + summaries)
        )
        total_output = (
            2000 +                                  # Claim extraction
            (300 * estimated_claims) +              # Fact check per claim
            1500 +                                  # Logic analysis
            2000                                    # Wisdom evaluation
        )
        
        # Calculate costs for each available model
        estimates = []
        for provider, provider_data in PROVIDER_MODELS.items():
            for model in provider_data['models']:
                input_cost = (total_input / 1_000_000) * model['input_cost_per_1m']
                output_cost = (total_output / 1_000_000) * model['output_cost_per_1m']
                total_cost = input_cost + output_cost
                
                estimates.append({
                    'provider': provider,
                    'model_id': model['id'],
                    'model_name': model['name'],
                    'tier': model['tier'],
                    'estimated_cost': round(total_cost, 4),
                    'input_cost_per_1m': model['input_cost_per_1m'],
                    'output_cost_per_1m': model['output_cost_per_1m'],
                    'description': model['description'],
                })
        
        # Sort by cost
        estimates.sort(key=lambda x: x['estimated_cost'])
        
        # Find recommended model (best value = standard tier, reasonable cost)
        recommended = None
        for est in estimates:
            if est['tier'] == 'standard' and est['provider'] in ['anthropic', 'openai', 'gemini']:
                recommended = est
                break
        if not recommended:
            recommended = estimates[0] if estimates else None
        
        return {
            'content_tokens': input_tokens,
            'estimated_total_input': total_input,
            'estimated_total_output': total_output,
            'estimated_claims': estimated_claims,
            'estimates_by_model': estimates,
            'recommended': recommended,
        }
    
    # ========================================================================
    # CRUD OPERATIONS (unchanged from Phase 1)
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
    # ANALYSIS PIPELINE (Phase 2 - Fully Implemented)
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
        6. Generate summary
        """
        print(f"DEBUG: run_analysis called for review {review_id}")  # Add this line
        logger.info(f"Starting analysis for review {review_id}")
        
        try:
            # Step 1: Extract content
            await self._update_status(review_id, ReviewStatus.EXTRACTING)
            content = await self._extract_content(review_id)
            
            if not content:
                raise Exception("Content extraction returned empty content")
            
            # Step 2: Extract claims
            await self._update_status(review_id, ReviewStatus.ANALYZING_CLAIMS)
            claims = await self._extract_claims(review_id, content)
            print(f"DEBUG: Claims extracted: {len(claims)}, starting fact check...")
            
            # Step 3: Fact check claims
            await self._update_status(review_id, ReviewStatus.FACT_CHECKING)
            fact_results = await self._fact_check_claims(review_id, claims)
            print(f"DEBUG: Fact check complete, got {len(fact_results)} results")
            
            # Step 4: Logic analysis (now receives fact-check results for soundness assessment)
            await self._update_status(review_id, ReviewStatus.LOGIC_ANALYSIS)
            logic_results = await self._analyze_logic(review_id, content, fact_results)
            print(f"DEBUG: Logic analysis complete")
            
            # Step 5: Wisdom evaluation
            await self._update_status(review_id, ReviewStatus.WISDOM_EVALUATION)
            await self._evaluate_wisdom(
                review_id, content,
                fact_summary=self._summarize_fact_results(fact_results),
                logic_summary=self._summarize_logic_results(logic_results)
            )

            print(f"DEBUG: Wisdom evaluation complete")
            
            # Step 6: Generate summary and complete
            await self._generate_summary(review_id)
            await self._update_status(review_id, ReviewStatus.COMPLETED)
            print(f"DEBUG: ALL STEPS COMPLETE for review {review_id}")
            
            logger.info(f"Completed analysis for review {review_id}")
            
        except PaywallDetectedError as e:
            logger.warning(f"Paywall detected for review {review_id}: {e}")
            await self._update_status(review_id, ReviewStatus.FAILED, str(e))
        except Exception as e:
            logger.exception(f"Analysis failed for review {review_id}: {e}")
            await self._update_status(review_id, ReviewStatus.FAILED, str(e))
    
    # ========================================================================
    # PIPELINE STEPS (Phase 2 - Fully Implemented)
    # ========================================================================
    
    async def _extract_content(self, review_id: int) -> str:
        """Extract and clean content from the source."""
        service = self._get_content_extraction()
        result = await service.extract_content(review_id)
        return result.get("content", "")
    
    async def _extract_claims(self, review_id: int, content: str) -> List[Dict[str, Any]]:
        """Identify claims in the content."""
        service = self._get_claim_extraction()
        claims = await service.extract_claims(review_id, content)
        return claims
    
    async def _fact_check_claims(
        self, 
        review_id: int, 
        claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Verify extracted claims."""
        service = self._get_fact_check()
        results = await service.fact_check_claims(review_id, claims)
        return results
    
    async def _analyze_logic(
        self, 
        review_id: int, 
        content: str,
        fact_check_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze logical structure and fallacies.
        
        Args:
            review_id: The review ID
            content: The content to analyze
            fact_check_results: Optional list of fact-check results to integrate
                               into soundness assessment
        """
        service = self._get_logic_analysis()
        results = await service.analyze_logic(review_id, content, fact_check_results)
        return results
    
    async def _evaluate_wisdom(
        self, 
        review_id: int, 
        content: str,
        fact_summary: Optional[str] = None,
        logic_summary: Optional[str] = None
    ):
        """Evaluate against 7 Universal Values and Something Deeperism."""
        service = self._get_wisdom_evaluation()
        await service.evaluate_wisdom(
            review_id, content,
            fact_check_summary=fact_summary,
            logic_summary=logic_summary
        )
    
    async def _generate_summary(self, review_id: int):
        """Generate quick summary from all analysis results."""
        with get_db_session() as db:
            review = db.get(ContentReview, review_id)
            if not review:
                return
            
            # Build summary from available data
            summary_parts = []
            
            # Factual summary
            true_count = 0
            false_count = 0
            mixed_count = 0
            for claim in review.claims:
                if claim.fact_check_result:
                    verdict = claim.fact_check_result.verdict.value
                    if verdict in ["true", "mostly_true"]:
                        true_count += 1
                    elif verdict in ["false", "mostly_false"]:
                        false_count += 1
                    else:
                        mixed_count += 1
            
            total_claims = len(review.claims)
            if total_claims > 0:
                summary_parts.append(
                    f"Analyzed {total_claims} claims: {true_count} verified, "
                    f"{false_count} false/misleading, {mixed_count} mixed/unverifiable."
                )
                
                # Determine overall factual verdict
                if false_count == 0 and true_count > 0:
                    review.overall_factual_verdict = FactualVerdict.ACCURATE
                elif true_count == 0 and false_count > 0:
                    review.overall_factual_verdict = FactualVerdict.INACCURATE
                elif true_count > false_count:
                    review.overall_factual_verdict = FactualVerdict.MOSTLY_ACCURATE
                elif false_count > true_count:
                    review.overall_factual_verdict = FactualVerdict.MOSTLY_INACCURATE
                else:
                    review.overall_factual_verdict = FactualVerdict.MIXED
            
            # Logic summary
            if review.logic_analysis:
                fallacy_count = len(review.logic_analysis.fallacies_found or [])
                if fallacy_count > 0:
                    summary_parts.append(
                        f"Found {fallacy_count} logical fallacy(s)."
                    )
                else:
                    summary_parts.append("No significant logical fallacies detected.")
            
            # Wisdom summary
            if review.wisdom_evaluation:
                wisdom_verdict = review.wisdom_evaluation.serves_wisdom_or_folly
                if wisdom_verdict:
                    verdict_text = wisdom_verdict.value.replace("_", " ").title()
                    summary_parts.append(f"Wisdom assessment: {verdict_text}.")
            
            review.quick_summary = " ".join(summary_parts)
            
            # Calculate confidence score (average of available confidences)
            confidences = []
            for claim in review.claims:
                if claim.fact_check_result and claim.fact_check_result.confidence:
                    confidences.append(claim.fact_check_result.confidence)
            if review.logic_analysis and review.logic_analysis.confidence:
                confidences.append(review.logic_analysis.confidence)
            
            if confidences:
                review.confidence_score = sum(confidences) / len(confidences)
            
            review.completed_at = datetime.utcnow()
            db.commit()
    
    def _summarize_fact_results(self, results: List[Dict[str, Any]]) -> str:
        """Create a summary of fact-check results for wisdom evaluation."""
        if not results:
            return "No fact-check results available."
        
        summaries = []
        for r in results[:5]:  # Limit to first 5
            claim = r.get("claim_text", "Unknown claim")[:100]
            verdict = r.get("verdict", "unknown")
            summaries.append(f"- {claim}: {verdict}")
        
        return "Fact-check summary:\n" + "\n".join(summaries)
    
    def _summarize_logic_results(self, results: Dict[str, Any]) -> str:
        """Create a summary of logic analysis for wisdom evaluation."""
        if not results or "error" in results:
            return "No logic analysis available."
        
        parts = []
        
        if results.get("main_conclusion"):
            parts.append(f"Main conclusion: {results['main_conclusion'][:200]}")
        
        fallacies = results.get("fallacies_found", [])
        if fallacies:
            fallacy_names = [f.get("name", "Unknown") for f in fallacies[:3]]
            parts.append(f"Fallacies found: {', '.join(fallacy_names)}")
        
        score = results.get("logic_quality_score")
        if score:
            parts.append(f"Logic quality score: {score:.2f}")
        
        return "\n".join(parts) if parts else "Logic analysis completed."
    
    # ========================================================================
    # HELPER METHODS (FIXED - 2025-12-30)
    # ========================================================================
    
    async def _create_fact_check_session(self, db, request: ReviewCreateRequest) -> int:
        """
        Create a new session for a standalone fact check.
        
        FIXED 2025-12-30: Now properly sets session_number and handles missing project_id.
        Previously this function did not set session_number, causing NULL constraint violations.
        """
        # Import here to avoid circular imports
        from backend.database.models import Session, Project, SessionType
        
        # Handle case where project_id is not provided
        project_id = request.project_id
        
        if project_id is None:
            # Try to find or create a default "Fact Checks" project
            default_project = db.query(Project).filter(
                Project.name == "Fact Checks",
                Project.user_id == 1  # TODO: Get from auth context
            ).first()
            
            if default_project:
                project_id = default_project.id
            else:
                # Create the default Fact Checks project
                default_project = Project(
                    name="Fact Checks",
                    slug="fact-checks",
                    description="Default project for standalone fact-checking sessions",
                    session_type=SessionType.GENERAL,
                    user_id=1,  # TODO: Get from auth context
                )
                db.add(default_project)
                db.flush()  # Get the ID
                project_id = default_project.id
                logger.info(f"Created default 'Fact Checks' project with id {project_id}")
        
        # Calculate the next session_number for this project
        max_session_num = db.query(func.max(Session.session_number)).filter(
            Session.project_id == project_id
        ).scalar()
        
        next_session_number = (max_session_num or 0) + 1
        
        # Create session with fact-check type
        session = Session(
            user_id=1,  # TODO: Get from auth context
            project_id=project_id,
            session_number=next_session_number,  # FIX: This was missing before!
            title=f"Fact Check: {request.title or request.source_url or 'New Analysis'}",
        )
        
        db.add(session)
        db.flush()  # Get the ID without committing
        
        logger.info(f"Created fact-check session {session.id} (session #{next_session_number} in project {project_id})")
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


# ========================================================================
# MODULE-LEVEL SINGLETON
# ========================================================================

_review_service: Optional[ReviewService] = None


def get_review_service() -> ReviewService:
    """Get or create the review service singleton."""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
