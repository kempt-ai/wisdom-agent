"""
Wisdom Agent - Fact Check Service

Orchestrates fact-checking across multiple providers.
Coordinates Google Fact Check API and LLM verification
to produce comprehensive verification results.

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 8 (supporting service)

FIXED: 2024-12-31 - Auto-initialize providers when service is first used
FIXED: 2025-01-01 - Properly load claims relationship with joinedload
FIXED: 2026-01-15 - Added semantic relevance check for external fact-checks
                    to prevent mismatches (e.g., fact-checks about what someone
                    SAID being used to verify claims about WHO someone IS)
FIXED: 2026-01-17 - Made relevance checking properly async to fix event loop bug
FIXED: 2026-01-17 - Removed ClaimBuster provider (site has been down for months)
FIXED: 2026-01-17 - Parallelized claim checking for ~70-80% speedup
"""

import logging
import asyncio
import re
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import joinedload

from backend.database.connection import get_db_session
from backend.database.fact_check_models import (
    ContentReview, ExtractedClaim, FactCheckResult, ClaimVerdict
)
from backend.providers import (
    get_provider_registry, ProviderType, VerificationStatus
)

logger = logging.getLogger(__name__)


class FactCheckService:
    """
    Service for fact-checking claims using multiple providers.
    
    Coordinates:
    - Google Fact Check API for fact-check database search
    - LLM verification with web search for novel claims
    
    Note: ClaimBuster was removed 2026-01-17 as the service has been
    unavailable for an extended period. Snopes FactBot could be added
    as an alternative in the future: https://www.snopes.com/factbot/
    """
    
    def __init__(self):
        """Initialize the fact check service."""
        self._registry = None
        self._providers_initialized = False
    
    async def _ensure_providers_initialized(self):
        """Make sure providers are registered before using the registry."""
        if not self._providers_initialized:
            logger.info("Initializing fact-check providers...")
            registry = get_provider_registry()
            
            # Try to register Google Fact Check provider
            try:
                from backend.providers.google_factcheck import GoogleFactCheckProvider
                provider = GoogleFactCheckProvider()
                if await provider.is_available():
                    registry.register(provider)
                    logger.info("Registered Google Fact Check provider")
                else:
                    logger.warning("Google Fact Check provider not available (check API key)")
            except ImportError as e:
                logger.debug(f"Google Fact Check provider not available: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Fact Check: {e}")
            
            # Try to register LLM verification provider
            try:
                from backend.providers.llm_verification import LLMVerificationProvider
                provider = LLMVerificationProvider()
                if await provider.is_available():
                    registry.register(provider)
                    logger.info("Registered LLM verification provider")
                else:
                    logger.warning("LLM verification provider not available")
            except ImportError as e:
                logger.debug(f"LLM verification provider not available: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM verification: {e}")
            
            self._providers_initialized = True
            
            # Log summary
            available = await registry.get_available_providers()
            logger.info(f"Initialized {len(available)} fact-check providers")
    
    async def get_registry(self):
        """Get the provider registry, ensuring providers are initialized."""
        await self._ensure_providers_initialized()
        if self._registry is None:
            self._registry = get_provider_registry()
        return self._registry
    
    # ========================================================================
    # MAIN FACT-CHECKING METHOD
    # ========================================================================
    
    async def fact_check_claims(
        self,
        review_id: int,
        claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fact-check a list of claims for a review.
        
        Args:
            review_id: The review ID these claims belong to
            claims: List of claim data with at least 'claim_text'
            
        Returns:
            List of fact-check results
        """
        logger.info(f"Fact-checking {len(claims)} claims for review {review_id}")
        
        results = []
        registry = await self.get_registry()  # Now awaits to ensure providers initialized
        
        with get_db_session() as db:
            # FIXED: Use query with joinedload to ensure claims are loaded
            from sqlalchemy import select
            
            query = (
                select(ContentReview)
                .options(joinedload(ContentReview.claims))
                .where(ContentReview.id == review_id)
            )
            review = db.execute(query).unique().scalar_one_or_none()
            
            if not review:
                logger.error(f"Review {review_id} not found")
                return []
            
            # FIXED: Check if claims exist
            claim_list = list(review.claims)  # Force evaluation of relationship
            if not claim_list:
                logger.warning(f"No claims found in database for review {review_id}")
                # If no claims in DB but claims were passed, something went wrong
                if claims:
                    logger.warning(f"Claims were passed ({len(claims)}) but not found in DB - possible timing issue")
                return []
            
            logger.info(f"Processing {len(claim_list)} claims for review {review_id} (parallel)")
            
            # ================================================================
            # PARALLELIZED: Check all claims concurrently for major speedup
            # Previously: ~40s per claim × 5 claims = ~200s sequential
            # Now: ~40-50s total (limited by slowest claim)
            # ================================================================
            
            async def check_claim_wrapper(claim_record):
                """Wrapper to handle individual claim checking with error handling."""
                try:
                    logger.debug(f"Fact-checking claim {claim_record.id}: {claim_record.claim_text[:50]}...")
                    result = await self._check_single_claim(
                        registry,
                        claim_record.claim_text,
                        claim_record.check_worthiness_score or 0.5
                    )
                    logger.debug(f"Claim {claim_record.id} verdict: {result.get('verdict')}")
                    return {
                        "claim_record": claim_record,
                        "result": result,
                        "error": None
                    }
                except Exception as e:
                    logger.exception(f"Failed to fact-check claim {claim_record.id}: {e}")
                    return {
                        "claim_record": claim_record,
                        "result": None,
                        "error": str(e)
                    }
            
            # Run all claim checks in parallel
            check_tasks = [check_claim_wrapper(claim) for claim in claim_list]
            check_results = await asyncio.gather(*check_tasks)
            
            # Save results to database sequentially (DB operations are fast)
            for check_data in check_results:
                claim_record = check_data["claim_record"]
                result = check_data["result"]
                error = check_data["error"]
                
                if error:
                    results.append({
                        "claim_id": claim_record.id,
                        "claim_text": claim_record.claim_text,
                        "error": error
                    })
                else:
                    try:
                        # Save result to database
                        await self._save_fact_check_result(
                            db, claim_record.id, result
                        )
                        results.append({
                            "claim_id": claim_record.id,
                            "claim_text": claim_record.claim_text,
                            **result
                        })
                    except Exception as e:
                        logger.exception(f"Failed to save fact-check result for claim {claim_record.id}: {e}")
                        results.append({
                            "claim_id": claim_record.id,
                            "claim_text": claim_record.claim_text,
                            "error": f"Save failed: {str(e)}"
                        })
            
            # FIXED: Explicit commit after all claims processed
            try:
                db.commit()
                logger.info(f"Committed fact-check results for review {review_id}")
            except Exception as e:
                logger.exception(f"Failed to commit fact-check results: {e}")
                db.rollback()
                raise
        
        logger.info(f"Completed fact-checking {len(results)} claims for review {review_id}")
        return results
    
    async def _check_single_claim(
        self,
        registry,
        claim_text: str,
        check_worthiness: float
    ) -> Dict[str, Any]:
        """
        Check a single claim using available providers.
        
        Strategy:
        1. If check-worthiness is low (<0.3), skip detailed checking
        2. First check Google Fact Check for existing fact checks
        3. If no results, use LLM verification with web search
        4. If no providers available, use direct LLM fallback
        """
        # Skip low check-worthiness claims
        if check_worthiness < 0.3:
            return {
                "verdict": "not_a_claim",
                "confidence": 0.8,
                "explanation": "Claim was assessed as not check-worthy (opinion or not verifiable)",
                "providers_used": [],
            }
        
        # Check if we have any providers at all
        available_providers = await registry.get_available_providers()
        
        if not available_providers:
            # No providers registered - use direct LLM fallback
            logger.info("No fact-check providers available, using LLM fallback")
            return await self._llm_fallback_check(claim_text)
        
        # Try Google Fact Check first
        google_provider = registry.get_provider(ProviderType.GOOGLE_FACT_CHECK)
        if google_provider and await google_provider.is_available():
            result = await registry.check_claim(
                claim_text,
                providers=[ProviderType.GOOGLE_FACT_CHECK]
            )
            
            # Only return if Google found actual fact-checks
            if result.get("results"):
                # FIXED: Pass our_claim for semantic relevance checking
                # This filters out fact-checks that are about the same person but different claims
                external_matches = await self._extract_external_matches(result, our_claim=claim_text)
                
                # FIXED: Only use Google's verdict if we have RELEVANT matches after filtering
                # If all matches were filtered out as irrelevant, fall through to LLM verification
                if external_matches:
                    verdict = result.get("consensus_verdict", "unverifiable")
                    return {
                        "verdict": verdict,
                        "confidence": result.get("confidence", 0.5),
                        "explanation": self._extract_explanation(result),
                        "providers_used": result.get("providers_used", []),
                        "external_matches": external_matches,
                    }
                # No relevant matches found after filtering, fall through to LLM verification
                logger.info(f"Google Fact Check matches were filtered as irrelevant, trying LLM verification")
        
        print(f"DEBUG: About to try LLM verification provider")
        # Try LLM verification provider
        llm_provider = registry.get_provider(ProviderType.LLM_VERIFICATION)
        print(f"DEBUG: LLM provider = {llm_provider}")
        
        is_avail = await llm_provider.is_available() if llm_provider else False
        print(f"DEBUG: LLM provider is_available = {is_avail}")
        if llm_provider and is_avail:
            print(f"DEBUG: Calling LLM verification for claim: {claim_text[:50]}...")
            try:
                result = await registry.check_claim(
                    claim_text,
                    providers=[ProviderType.LLM_VERIFICATION]
                )
                print(f"DEBUG: LLM result = {result}")
            except Exception as e:
                print(f"DEBUG: LLM verification EXCEPTION: {e}")
                result = None
            
            return {
                "verdict": result.get("consensus_verdict", "unverifiable"),
                "confidence": result.get("confidence", 0.5),
                "explanation": self._extract_explanation(result),
                "providers_used": result.get("providers_used", []),
                "web_sources": self._extract_web_sources(result),
            }
        
        # Final fallback: direct LLM check
        return await self._llm_fallback_check(claim_text)
    
    async def _llm_fallback_check(self, claim_text: str) -> Dict[str, Any]:
        """
        Direct LLM-based fact checking when no providers are available.
        Uses the LLM router directly.
        """
        try:
            from backend.services.llm_router import get_llm_router
            llm = get_llm_router()
            
            prompt = f"""Evaluate the following claim for factual accuracy.

Claim: "{claim_text}"

Analyze this claim and provide:
1. Your verdict: one of [true, mostly_true, half_true, mostly_false, false, unverifiable]
2. Your confidence: a number from 0.0 to 1.0
3. A brief explanation of your reasoning

Respond in this exact format:
VERDICT: [your verdict]
CONFIDENCE: [your confidence]
EXPLANATION: [your explanation]"""

            # FIXED: Run synchronous LLM call in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(
                llm.complete,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            # Parse the response
            lines = response.strip().split('\n')
            verdict = "unverifiable"
            confidence = 0.5
            explanation = "LLM-based verification"
            
            for line in lines:
                line_lower = line.lower().strip()
                if line_lower.startswith('verdict:'):
                    verdict_text = line.split(':', 1)[1].strip().lower()
                    # Clean up the verdict
                    verdict_text = verdict_text.replace('-', '_').replace(' ', '_')
                    if verdict_text in ['true', 'mostly_true', 'half_true', 'mostly_false', 'false', 'unverifiable']:
                        verdict = verdict_text
                elif line_lower.startswith('confidence:'):
                    try:
                        conf_text = line.split(':', 1)[1].strip()
                        confidence = float(conf_text)
                        confidence = max(0.0, min(1.0, confidence))
                    except ValueError:
                        pass
                elif line_lower.startswith('explanation:'):
                    explanation = line.split(':', 1)[1].strip()
            
            return {
                "verdict": verdict,
                "confidence": confidence,
                "explanation": f"LLM Analysis: {explanation}",
                "providers_used": ["llm_fallback"],
            }
            
        except Exception as e:
            logger.exception(f"LLM fallback check failed: {e}")
            return {
                "verdict": "unverifiable",
                "confidence": 0.0,
                "explanation": f"Verification failed: {str(e)}",
                "providers_used": [],
            }
    
    # ========================================================================
    # EXTERNAL MATCH EXTRACTION WITH SEMANTIC RELEVANCE CHECK
    # ========================================================================
    
    async def _extract_external_matches(
        self, 
        result: Dict[str, Any], 
        our_claim: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Extract external fact check matches from provider results.
        
        IMPORTANT: When our_claim is provided, verifies semantic relevance 
        before including matches. A fact-check about the same PERSON is not 
        necessarily about the same CLAIM (e.g., a fact-check about what 
        RFK Jr. SAID about vaccines tells us nothing about whether he IS 
        the Health Secretary).
        
        Args:
            result: The provider result containing potential matches
            our_claim: The original claim we're trying to verify (optional)
            
        Returns:
            List of relevant external fact-check matches
        """
        matches = []
        for provider_result in result.get("results", []):
            sources = provider_result.get("sources", [])
            for source in sources:
                if isinstance(source, dict):
                    # Get the fact-check claim - different providers use different keys
                    # Google Fact Check uses "claim_reviewed", others might use "claim_text"
                    factcheck_claim = (
                        source.get("claim_reviewed") or 
                        source.get("claim_text") or 
                        ""
                    )
                    # Get the rating/verdict - providers use different keys
                    factcheck_rating = (
                        source.get("verdict") or 
                        source.get("rating") or 
                        ""
                    )
                    
                    # If we have our original claim and a fact-check claim, verify relevance
                    if our_claim and factcheck_claim:
                        is_relevant = await self._verify_factcheck_relevance(
                            our_claim=our_claim,
                            factcheck_claim=factcheck_claim,
                            factcheck_rating=factcheck_rating
                        )
                        if not is_relevant:
                            logger.info(
                                f"Rejected irrelevant fact-check: '{factcheck_claim[:60]}...' "
                                f"does not match our claim: '{our_claim[:60]}...'"
                            )
                            continue
                    matches.append(source)
        return matches
    
    async def _verify_factcheck_relevance(
        self, 
        our_claim: str, 
        factcheck_claim: str, 
        factcheck_rating: str
    ) -> bool:
        """
        Verify that an external fact-check is actually about our claim,
        not just about the same person or topic.
        
        Uses heuristic checks first (free), then LLM if needed (cheap).
        
        Args:
            our_claim: The claim we're trying to verify
            factcheck_claim: The claim that was checked in the external fact-check
            factcheck_rating: The rating/verdict from the external fact-check
            
        Returns:
            True if the fact-check is relevant to our claim, False otherwise
        """
        # Quick heuristic checks first (no LLM cost)
        
        # Normalize for comparison
        our_lower = our_claim.lower().strip()
        fc_lower = factcheck_claim.lower().strip()
        
        # If claims are very similar (>60% word overlap), probably relevant
        our_words = set(our_lower.split())
        fc_words = set(fc_lower.split())
        
        if len(our_words) > 0 and len(fc_words) > 0:
            overlap = len(our_words & fc_words) / max(len(our_words), len(fc_words))
            if overlap > 0.6:
                logger.debug(f"Heuristic acceptance: high word overlap ({overlap:.2f})")
                return True
        
        # Check for obvious mismatches:
        # If our claim is about a position/role and the fact-check is about something they SAID
        position_indicators = [
            "is", "was", "became", "appointed", "elected", "serves as", 
            "secretary", "president", "ceo", "director", "minister", 
            "governor", "mayor", "chairman", "chief"
        ]
        statement_indicators = [
            "said", "claimed", "stated", "tweeted", "posted", "according to",
            "argues", "believes", "asserts", "suggests", "wrote"
        ]
        
        our_is_about_position = any(ind in our_lower for ind in position_indicators)
        fc_is_about_statement = any(ind in fc_lower for ind in statement_indicators)
        
        if our_is_about_position and fc_is_about_statement:
            # Our claim is about WHO someone IS, fact-check is about what they SAID
            # These are different types of claims
            logger.debug(f"Heuristic rejection: position claim vs statement claim")
            return False
        
        # Check if fact-check is about a SPECIFIC DATE but our claim is general
        # e.g., "confirmed on Feb. 4" vs "is the Health Secretary"
        date_patterns = [
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}',
            r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\b\d{4}\b',  # Year
            r'\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        ]
        fc_has_specific_date = any(re.search(pattern, fc_lower) for pattern in date_patterns)
        our_has_specific_date = any(re.search(pattern, our_lower) for pattern in date_patterns)
        
        if fc_has_specific_date and not our_has_specific_date:
            # Fact-check is about a specific date/time, but our claim is general
            # The fact-check verdict might be about the DATE being wrong, not the claim itself
            logger.debug(f"Heuristic rejection: fact-check has specific date, our claim is general")
            return False
        
        # Check if the fact-check claim contains completely different subject matter
        our_topics = self._extract_key_topics(our_claim)
        fc_topics = self._extract_key_topics(factcheck_claim)
        
        if our_topics and fc_topics:
            topic_overlap = len(our_topics & fc_topics) / max(len(our_topics), len(fc_topics))
            if topic_overlap < 0.15:
                # Very little topic overlap - probably unrelated
                logger.debug(f"Heuristic rejection: low topic overlap ({topic_overlap:.2f})")
                return False
        
        # If heuristics are inconclusive, use LLM verification
        # (This is the expensive path, but more accurate)
        return await self._verify_relevance_with_llm(our_claim, factcheck_claim, factcheck_rating)
    
    def _extract_key_topics(self, text: str) -> set:
        """
        Extract key topic words from text (nouns, proper nouns).
        Simple extraction without NLP dependencies.
        """
        # Common stopwords to filter out
        stopwords = {
            'the', 'a', 'an', 'is', 'was', 'are', 'were', 'been', 'be', 
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
            'could', 'should', 'may', 'might', 'must', 'shall', 'can',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'that', 'which', 'who', 'whom', 'this', 'these', 'those',
            'and', 'or', 'but', 'if', 'then', 'than', 'so', 'as', 'not',
            'no', 'yes', 'all', 'any', 'some', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'into', 'over', 'such', 'only'
        }
        
        # Extract words (3+ chars), filter stopwords
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        topics = {w for w in words if w not in stopwords}
        
        return topics
    
    async def _verify_relevance_with_llm(
        self, 
        our_claim: str, 
        factcheck_claim: str, 
        factcheck_rating: str
    ) -> bool:
        """
        Use LLM to verify if a fact-check is semantically relevant to our claim.
        This is more expensive but more accurate than heuristics alone.
        
        Args:
            our_claim: The claim we're trying to verify
            factcheck_claim: The claim from the external fact-check
            factcheck_rating: The rating from the external fact-check
            
        Returns:
            True if the fact-check is relevant, False otherwise
        """
        prompt = f"""I need to verify if an external fact-check is relevant to the claim I'm checking.

MY CLAIM TO VERIFY: "{our_claim}"

EXTERNAL FACT-CHECK FOUND:
- Claim that was checked: "{factcheck_claim}"
- Verdict given: "{factcheck_rating}"

QUESTION: Is this fact-check about THE SAME CLAIM as mine?

Important considerations:
- Same person mentioned ≠ same claim (e.g., "RFK Jr. claimed vaccines cause autism is FALSE" tells us nothing about "RFK Jr. is Health Secretary")
- Same topic mentioned ≠ same claim (e.g., a fact-check about one specific donation doesn't verify general campaign finance rules)
- A fact-check about a SPECIFIC DATE or DETAIL (e.g., "confirmed on Feb 4") doesn't verify the GENERAL claim (e.g., "is Health Secretary")
- The fact-check must DIRECTLY address the truth of my specific claim

Answer with just YES or NO, then a brief reason."""

        try:
            from backend.services.llm_router import get_llm_router
            llm = get_llm_router()
            
            # Run synchronous LLM call in thread pool to avoid blocking
            response = await asyncio.to_thread(
                llm.complete,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic for consistency
                max_tokens=100  # Short response needed
            )
            
            # Parse response - look for YES or NO at the start
            response_lower = response.lower().strip()
            is_relevant = response_lower.startswith("yes")
            
            logger.debug(f"LLM relevance check: {is_relevant} - {response[:100]}")
            return is_relevant
            
        except Exception as e:
            logger.warning(f"LLM relevance check failed: {e}, defaulting to include")
            # On error, include the fact-check (conservative approach - don't lose potentially relevant info)
            return True
    
    # ========================================================================
    # WEB SOURCE EXTRACTION
    # ========================================================================
    
    def _extract_web_sources(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract web sources from LLM verification results."""
        sources = []
        for provider_result in result.get("results", []):
            # First check direct sources (from LLM verification provider)
            direct_sources = provider_result.get("sources", [])
            if direct_sources:
                sources.extend(direct_sources[:10])  # Limit to 10 sources
            else:
                # Fallback to raw_response.search_results for backwards compatibility
                raw = provider_result.get("raw_response", {})
                if isinstance(raw, dict):
                    search_results = raw.get("search_results", [])
                    sources.extend(search_results[:10])
        return sources
    
    def _extract_explanation(self, result: Dict[str, Any]) -> str:
        """Extract explanation from provider results."""
        for provider_result in result.get("results", []):
            explanation = provider_result.get("explanation")
            if explanation:
                return explanation
        return "Verification completed but no detailed explanation available."
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    async def _save_fact_check_result(
        self,
        db,
        claim_id: int,
        result: Dict[str, Any]
    ):
        """Save fact check result to database."""
        # Delete existing result if any
        claim = db.get(ExtractedClaim, claim_id)
        if not claim:
            logger.warning(f"Claim {claim_id} not found when saving result")
            return
            
        if claim.fact_check_result:
            db.delete(claim.fact_check_result)
            db.flush()  # Ensure delete is processed before insert
        
        # Map verdict string to enum (handle None values)
        verdict_str = result.get("verdict") or "unverifiable"
        verdict_map = {
            "true": ClaimVerdict.TRUE,
            "mostly_true": ClaimVerdict.MOSTLY_TRUE,
            "half_true": ClaimVerdict.HALF_TRUE,
            "mostly_false": ClaimVerdict.MOSTLY_FALSE,
            "false": ClaimVerdict.FALSE,
            "unverifiable": ClaimVerdict.UNVERIFIABLE,
            "not_a_claim": ClaimVerdict.NOT_A_CLAIM,
        }
        verdict = verdict_map.get(verdict_str.lower(), ClaimVerdict.UNVERIFIABLE)
        
        # Create result record
        fact_check_result = FactCheckResult(
            claim_id=claim_id,
            verdict=verdict,
            confidence=result.get("confidence", 0.5),
            explanation=result.get("explanation"),
            providers_used=result.get("providers_used"),
            external_matches=result.get("external_matches"),
            web_sources=result.get("web_sources"),
        )
        
        db.add(fact_check_result)
        logger.debug(f"Saved fact check result for claim {claim_id}: {verdict}")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def check_single_claim_standalone(
        self,
        claim_text: str,
        use_all_providers: bool = False
    ) -> Dict[str, Any]:
        """
        Check a single claim without associating with a review.
        
        Useful for quick checks or API access.
        
        Args:
            claim_text: The claim to verify
            use_all_providers: If True, use all providers and aggregate
            
        Returns:
            Verification result
        """
        registry = await self.get_registry()
        
        if use_all_providers:
            result = await registry.check_claim(
                claim_text,
                require_consensus=True
            )
        else:
            result = await registry.check_claim(claim_text)
        
        return {
            "claim": claim_text,
            "verdict": result.get("consensus_verdict"),
            "confidence": result.get("confidence"),
            "providers_used": result.get("providers_used", []),
            "results": result.get("results", []),
        }
    
    async def get_provider_status(self) -> Dict[str, bool]:
        """Get availability status of all providers."""
        registry = await self.get_registry()
        status = {}
        
        for provider_type in ProviderType:
            provider = registry.get_provider(provider_type)
            if provider:
                status[provider_type.value] = await provider.is_available()
            else:
                status[provider_type.value] = False
        
        return status


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_fact_check_service: Optional[FactCheckService] = None


def get_fact_check_service() -> FactCheckService:
    """Get or create the fact check service instance."""
    global _fact_check_service
    if _fact_check_service is None:
        _fact_check_service = FactCheckService()
    return _fact_check_service
