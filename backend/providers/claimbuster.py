"""
Wisdom Agent - ClaimBuster Provider

Integrates with the ClaimBuster API for:
- Claim check-worthiness scoring (triage)
- Claim matching against their database

ClaimBuster is a research project from UT Arlington.
API documentation: https://idir.uta.edu/claimbuster/

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


class ClaimBusterProvider(FactCheckProvider):
    """
    ClaimBuster API provider.
    
    Features:
    - Check-worthiness scoring: Rates claims 0-1 on how important they are to check
    - Claim matching: Finds similar claims that have been fact-checked
    
    Requires CLAIMBUSTER_API_KEY environment variable.
    Get a free key at: https://idir.uta.edu/claimbuster/api/
    """
    
    BASE_URL = "https://idir.uta.edu/claimbuster/api/v2"
    
    def __init__(self):
        self._api_key = os.getenv("CLAIMBUSTER_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CLAIM_BUSTER
    
    @property
    def name(self) -> str:
        return "ClaimBuster"
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def is_available(self) -> bool:
        """Check if ClaimBuster API is configured."""
        return bool(self._api_key)
    
    async def check_claim(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> ProviderResult:
        """
        Check a claim using ClaimBuster.
        
        ClaimBuster primarily provides check-worthiness scores,
        but can also match against their fact-check database.
        """
        if not self._api_key:
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.NOT_CONFIGURED,
                error_message="ClaimBuster API key not configured"
            )
        
        try:
            # Get check-worthiness score
            score = await self.triage_claim(claim)
            
            # Try to find matching fact checks
            matches = await self.find_existing_fact_checks(claim)
            
            if matches:
                # We found existing fact checks
                return ProviderResult(
                    provider=self.provider_type,
                    status=VerificationStatus.SUCCESS,
                    verdict=matches[0].verdict.lower() if matches else None,
                    confidence=score,
                    explanation=f"Found {len(matches)} existing fact check(s) for similar claims.",
                    sources=[m.to_dict() for m in matches],
                    raw_response={
                        "check_worthiness_score": score,
                        "matches": [m.to_dict() for m in matches]
                    }
                )
            else:
                # No matches found, return check-worthiness info
                return ProviderResult(
                    provider=self.provider_type,
                    status=VerificationStatus.NO_RESULTS,
                    confidence=score,
                    explanation=f"No existing fact checks found. Check-worthiness score: {score:.2f}",
                    raw_response={"check_worthiness_score": score}
                )
                
        except Exception as e:
            logger.exception(f"ClaimBuster check failed: {e}")
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.ERROR,
                error_message=str(e)
            )
    
    async def triage_claim(self, claim: str) -> float:
        """
        Get check-worthiness score from ClaimBuster.
        
        This is ClaimBuster's primary feature - scoring how
        important/checkable a claim is.
        
        Args:
            claim: The claim text to evaluate
            
        Returns:
            Score from 0.0 (not check-worthy) to 1.0 (highly check-worthy)
        """
        if not self._api_key:
            return 0.5
        
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"{self.BASE_URL}/score/text/{claim}",
                headers={"x-api-key": self._api_key}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # ClaimBuster returns results per sentence
            results = data.get("results", [])
            if results:
                # Return highest score among sentences
                scores = [r.get("score", 0) for r in results]
                return max(scores)
            
            return 0.5
            
        except Exception as e:
            logger.warning(f"ClaimBuster triage failed: {e}")
            return 0.5
    
    async def find_existing_fact_checks(
        self, 
        claim: str
    ) -> List[ExternalFactCheck]:
        """
        Search ClaimBuster's fact-check database for similar claims.
        
        Args:
            claim: The claim to search for
            
        Returns:
            List of matching fact checks
        """
        if not self._api_key:
            return []
        
        matches = []
        
        try:
            client = await self._get_client()
            
            # Use the claim matching endpoint
            response = await client.get(
                f"{self.BASE_URL}/query/fact_matcher/{claim}",
                headers={"x-api-key": self._api_key}
            )
            response.raise_for_status()
            
            data = response.json()
            
            for result in data.get("results", []):
                # ClaimBuster returns matches from various fact-checkers
                matches.append(ExternalFactCheck(
                    source=result.get("source", "Unknown"),
                    claim_reviewed=result.get("claim", claim),
                    verdict=result.get("verdict", "Unknown"),
                    url=result.get("url", ""),
                    review_date=result.get("date"),
                ))
            
        except Exception as e:
            logger.warning(f"ClaimBuster fact check search failed: {e}")
        
        return matches
    
    async def batch_triage(self, claims: List[str]) -> List[float]:
        """
        Get check-worthiness scores for multiple claims.
        
        Args:
            claims: List of claim texts
            
        Returns:
            List of scores (same order as input)
        """
        scores = []
        for claim in claims:
            score = await self.triage_claim(claim)
            scores.append(score)
        return scores
