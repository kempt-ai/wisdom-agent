"""
Wisdom Agent - Fact Check Service

Orchestrates fact-checking across multiple providers.
Coordinates ClaimBuster, Google Fact Check API, and LLM verification
to produce comprehensive verification results.

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 8 (supporting service)

FIXED: 2024-12-31 - Auto-initialize providers when service is first used
FIXED: 2025-01-01 - Properly load claims relationship with joinedload
"""

import logging
import asyncio
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
    - ClaimBuster for check-worthiness and existing fact checks
    - Google Fact Check API for fact-check database search
    - LLM verification with web search for novel claims
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
            
            # Try to register ClaimBuster provider
            try:
                from backend.providers.claimbuster import ClaimBusterProvider
                provider = ClaimBusterProvider()
                if await provider.is_available():
                    registry.register(provider)
                    logger.info("Registered ClaimBuster provider")
                else:
                    logger.warning("ClaimBuster provider not available (check API key)")
            except ImportError as e:
                logger.debug(f"ClaimBuster provider not available: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize ClaimBuster: {e}")
            
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
            
            logger.info(f"Processing {len(claim_list)} claims for review {review_id}")
            
            for claim_record in claim_list:
                try:
                    logger.debug(f"Fact-checking claim {claim_record.id}: {claim_record.claim_text[:50]}...")
                    
                    # Check this claim
                    result = await self._check_single_claim(
                        registry,
                        claim_record.claim_text,
                        claim_record.check_worthiness_score or 0.5
                    )
                    
                    logger.debug(f"Claim {claim_record.id} verdict: {result.get('verdict')}")
                    
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
                    logger.exception(f"Failed to fact-check claim {claim_record.id}: {e}")
                    results.append({
                        "claim_id": claim_record.id,
                        "claim_text": claim_record.claim_text,
                        "error": str(e)
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
        3. If no results, try ClaimBuster database
        4. If still no results, use LLM verification
        5. If no providers available, use direct LLM fallback
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
                external_matches = self._extract_external_matches(result)
                verdict = result.get("consensus_verdict", "unverifiable")
                
                if external_matches or verdict not in ["unverifiable", None]:
                    return {
                        "verdict": verdict,
                        "confidence": result.get("confidence", 0.5),
                        "explanation": self._extract_explanation(result),
                        "providers_used": result.get("providers_used", []),
                        "external_matches": external_matches,
                    }
                # No matches found, fall through to other providers
                logger.info(f"Google Fact Check found no matches, trying other providers")
        
        # Try ClaimBuster
        claimbuster_provider = registry.get_provider(ProviderType.CLAIM_BUSTER)
        if claimbuster_provider and await claimbuster_provider.is_available():
            result = await registry.check_claim(
                claim_text,
                providers=[ProviderType.CLAIM_BUSTER]
            )
            
            # Only return ClaimBuster result if it found actual matches
            # Otherwise fall through to LLM verification
            if result.get("results"):
                external_matches = self._extract_external_matches(result)
                verdict = result.get("consensus_verdict", "unverifiable")
                
                # If ClaimBuster found actual fact-checks, use them
                if external_matches or verdict not in ["unverifiable", None]:
                    return {
                        "verdict": verdict,
                        "confidence": result.get("confidence", 0.5),
                        "explanation": self._extract_explanation(result),
                        "providers_used": result.get("providers_used", []),
                        "external_matches": external_matches,
                    }
                # Otherwise, ClaimBuster just gave check-worthiness score
                # Fall through to LLM verification
                logger.info(f"ClaimBuster found no matches for claim, using LLM fallback")
        
        # Try LLM verification provider
        llm_provider = registry.get_provider(ProviderType.LLM_VERIFICATION)
        if llm_provider and await llm_provider.is_available():
            result = await registry.check_claim(
                claim_text,
                providers=[ProviderType.LLM_VERIFICATION]
            )
            
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

            response = llm.complete(
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
    
    def _extract_external_matches(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract external fact check matches from provider results."""
        matches = []
        for provider_result in result.get("results", []):
            sources = provider_result.get("sources", [])
            for source in sources:
                if isinstance(source, dict):
                    matches.append(source)
        return matches
    
    def _extract_web_sources(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract web sources from LLM verification results."""
        sources = []
        for provider_result in result.get("results", []):
            raw = provider_result.get("raw_response", {})
            if isinstance(raw, dict):
                search_results = raw.get("search_results", [])
                sources.extend(search_results[:5])  # Limit to 5 sources
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
