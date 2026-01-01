"""
Wisdom Agent - Google Fact Check API Provider

Integrates with Google's Fact Check Tools API to find
existing fact checks from reputable organizations.

API documentation: https://developers.google.com/fact-check/tools/api

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 8
"""

import logging
import os
from typing import Optional, List

import httpx

from backend.providers.base import (
    FactCheckProvider, ProviderType, ProviderResult,
    VerificationStatus, ExternalFactCheck
)

logger = logging.getLogger(__name__)


class GoogleFactCheckProvider(FactCheckProvider):
    """
    Google Fact Check Tools API provider.
    
    Searches Google's database of fact checks from:
    - PolitiFact
    - Snopes
    - FactCheck.org
    - AFP Fact Check
    - Reuters Fact Check
    - And many more...
    
    Requires GOOGLE_FACT_CHECK_API_KEY environment variable.
    Get a key at: https://console.cloud.google.com/apis/credentials
    Enable the "Fact Check Tools API" in your project.
    """
    
    BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    
    def __init__(self):
        self._api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GOOGLE_FACT_CHECK
    
    @property
    def name(self) -> str:
        return "Google Fact Check"
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def is_available(self) -> bool:
        """Check if Google Fact Check API is configured."""
        return bool(self._api_key)
    
    async def check_claim(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> ProviderResult:
        """
        Check a claim using Google Fact Check API.
        
        Searches for existing fact checks that match the claim.
        """
        if not self._api_key:
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.NOT_CONFIGURED,
                error_message="Google Fact Check API key not configured"
            )
        
        try:
            # Search for fact checks
            fact_checks = await self.find_existing_fact_checks(claim)
            
            if not fact_checks:
                return ProviderResult(
                    provider=self.provider_type,
                    status=VerificationStatus.NO_RESULTS,
                    explanation="No existing fact checks found for this claim."
                )
            
            # Aggregate verdicts
            verdict, confidence = self._aggregate_verdicts(fact_checks)
            
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.SUCCESS,
                verdict=verdict,
                confidence=confidence,
                explanation=f"Found {len(fact_checks)} existing fact check(s).",
                sources=[fc.to_dict() for fc in fact_checks],
                raw_response={"fact_checks": [fc.to_dict() for fc in fact_checks]}
            )
            
        except Exception as e:
            logger.exception(f"Google Fact Check API failed: {e}")
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.ERROR,
                error_message=str(e)
            )
    
    async def find_existing_fact_checks(
        self, 
        claim: str,
        language: str = "en",
        max_results: int = 10
    ) -> List[ExternalFactCheck]:
        """
        Search for existing fact checks using Google's API.
        
        Args:
            claim: The claim to search for
            language: Language code (default: "en")
            max_results: Maximum results to return
            
        Returns:
            List of existing fact checks found
        """
        if not self._api_key:
            return []
        
        fact_checks = []
        
        try:
            client = await self._get_client()
            
            response = await client.get(
                self.BASE_URL,
                params={
                    "key": self._api_key,
                    "query": claim,
                    "languageCode": language,
                    "pageSize": max_results,
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get("claims", []):
                # Each claim can have multiple reviews
                for review in item.get("claimReview", []):
                    fact_checks.append(ExternalFactCheck(
                        source=review.get("publisher", {}).get("name", "Unknown"),
                        claim_reviewed=item.get("text", claim),
                        verdict=review.get("textualRating", "Unknown"),
                        url=review.get("url", ""),
                        review_date=review.get("reviewDate"),
                    ))
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Google Fact Check API rate limited")
            else:
                logger.exception(f"Google Fact Check API error: {e}")
        except Exception as e:
            logger.exception(f"Google Fact Check search failed: {e}")
        
        return fact_checks
    
    def _aggregate_verdicts(
        self, 
        fact_checks: List[ExternalFactCheck]
    ) -> tuple:
        """
        Aggregate verdicts from multiple fact checks.
        
        Returns:
            (verdict, confidence) tuple
        """
        if not fact_checks:
            return (None, 0.0)
        
        # Map common verdict strings to normalized values
        verdict_map = {
            # True variants
            "true": "true",
            "correct": "true",
            "accurate": "true",
            "verified": "true",
            # Mostly true variants
            "mostly true": "mostly_true",
            "mostly correct": "mostly_true",
            "mostly accurate": "mostly_true",
            "largely true": "mostly_true",
            # Half true variants  
            "half true": "half_true",
            "mixture": "half_true",
            "mixed": "half_true",
            "half-true": "half_true",
            "partially true": "half_true",
            # Mostly false variants
            "mostly false": "mostly_false",
            "mostly incorrect": "mostly_false",
            "mostly inaccurate": "mostly_false",
            "largely false": "mostly_false",
            # False variants
            "false": "false",
            "incorrect": "false",
            "inaccurate": "false",
            "wrong": "false",
            "pants on fire": "false",
            "four pinocchios": "false",
        }
        
        # Score each verdict
        verdict_scores = {
            "true": 1.0,
            "mostly_true": 0.75,
            "half_true": 0.5,
            "mostly_false": 0.25,
            "false": 0.0,
        }
        
        scores = []
        for fc in fact_checks:
            verdict_lower = fc.verdict.lower().strip()
            normalized = verdict_map.get(verdict_lower)
            if normalized:
                scores.append(verdict_scores[normalized])
        
        if not scores:
            # Couldn't normalize any verdicts
            return ("unverifiable", 0.3)
        
        # Average the scores
        avg_score = sum(scores) / len(scores)
        
        # Convert back to verdict
        if avg_score >= 0.875:
            verdict = "true"
        elif avg_score >= 0.625:
            verdict = "mostly_true"
        elif avg_score >= 0.375:
            verdict = "half_true"
        elif avg_score >= 0.125:
            verdict = "mostly_false"
        else:
            verdict = "false"
        
        # Confidence based on agreement
        if len(scores) == 1:
            confidence = 0.6  # Single source
        elif len(scores) >= 3:
            # Check agreement
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            confidence = min(0.95, 0.7 + (1 - min(variance, 1)) * 0.25)
        else:
            confidence = 0.7
        
        return (verdict, confidence)
    
    async def search_by_publisher(
        self,
        claim: str,
        publisher: str
    ) -> List[ExternalFactCheck]:
        """
        Search for fact checks from a specific publisher.
        
        Args:
            claim: The claim to search for
            publisher: Publisher name (e.g., "politifact.com")
            
        Returns:
            List of fact checks from that publisher
        """
        all_results = await self.find_existing_fact_checks(claim, max_results=20)
        
        return [
            fc for fc in all_results 
            if publisher.lower() in fc.source.lower()
        ]
