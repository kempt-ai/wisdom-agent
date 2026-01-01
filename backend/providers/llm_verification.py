"""
Wisdom Agent - LLM Verification Provider

Uses LLM with web search to verify claims when external
fact-check databases don't have results.

This is the fallback provider that can check any claim
by searching the web and having the LLM analyze the evidence.

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 8
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any

from backend.providers.base import (
    FactCheckProvider, ProviderType, ProviderResult,
    VerificationStatus
)
from backend.services.web_search_service import (
    get_web_search_service, SearchResult
)

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPTS
# ============================================================================

VERIFICATION_SYSTEM_PROMPT = """You are an expert fact-checker. Your task is to evaluate claims based on evidence from web search results.

For each claim:
1. Analyze the provided search results carefully
2. Assess whether the evidence supports, refutes, or is inconclusive about the claim
3. Consider source credibility (prefer official sources, academic papers, reputable news)
4. Note any conflicting evidence
5. Provide a clear verdict with confidence level

Be objective and evidence-based. If evidence is insufficient, say so rather than guessing.

Verdicts should be one of:
- true: Strong evidence supports the claim
- mostly_true: Evidence largely supports with minor caveats
- half_true: Mixed evidence or claim is partially accurate
- mostly_false: Evidence largely contradicts with minor accurate elements
- false: Strong evidence contradicts the claim
- unverifiable: Insufficient evidence to make a determination

Respond in JSON format only."""

VERIFICATION_USER_PROMPT = """Evaluate this claim based on the search evidence:

CLAIM: {claim}

SEARCH RESULTS:
{search_results}

Respond with a JSON object:
{{
  "verdict": "true|mostly_true|half_true|mostly_false|false|unverifiable",
  "confidence": 0.0-1.0,
  "explanation": "Detailed explanation of your reasoning",
  "key_evidence": [
    {{"source": "source name", "supports_or_refutes": "supports|refutes|neutral", "quote_or_summary": "relevant info"}}
  ],
  "caveats": ["Any important caveats or limitations"],
  "sources_used": ["URLs of most relevant sources"]
}}"""


class LLMVerificationProvider(FactCheckProvider):
    """
    LLM-based verification provider.
    
    Uses web search to gather evidence, then has an LLM
    analyze the evidence to verify the claim.
    
    This is the most flexible provider - it can check any claim
    but requires more computation and may be less reliable than
    established fact-checkers.
    """
    
    def __init__(self, llm_service=None, web_search_service=None):
        """
        Initialize the LLM verification provider.
        
        Args:
            llm_service: Optional LLM service instance
            web_search_service: Optional web search service instance
        """
        self._llm_service = llm_service
        self._web_search_service = web_search_service
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.LLM_VERIFICATION
    
    @property
    def name(self) -> str:
        return "LLM Verification"
    
    def _get_llm_service(self):
        """Get or create the LLM service."""
        if self._llm_service is None:
            from backend.services.llm_router import get_llm_router
            self._llm_service = get_llm_router()
        return self._llm_service
    
    async def _get_web_search_service(self):
        """Get or create the web search service."""
        if self._web_search_service is None:
            self._web_search_service = get_web_search_service()
        return self._web_search_service
    
    async def is_available(self) -> bool:
        """
        Check if LLM verification is available.
        
        Always returns True since we use the default LLM router
        and DuckDuckGo (no API key needed).
        """
        try:
            llm = self._get_llm_service()
            return llm is not None
        except Exception:
            return False
    
    async def check_claim(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> ProviderResult:
        """
        Verify a claim using LLM with web search.
        
        Steps:
        1. Search the web for evidence related to the claim
        2. Have the LLM analyze the search results
        3. Return the verdict with explanation
        """
        try:
            # Step 1: Search for evidence
            web_search = await self._get_web_search_service()
            search_results = await web_search.search_for_claim(claim, num_results=10)
            
            if not search_results:
                return ProviderResult(
                    provider=self.provider_type,
                    status=VerificationStatus.NO_RESULTS,
                    explanation="Could not find relevant search results for this claim."
                )
            
            # Step 2: Format search results for LLM
            formatted_results = self._format_search_results(search_results)
            
            # Step 3: Get LLM analysis
            llm = self._get_llm_service()
            
            response = llm.complete(
                messages=[{"role": "user", "content": VERIFICATION_USER_PROMPT.format(
                    claim=claim,
                    search_results=formatted_results
                )}],
                system_prompt=VERIFICATION_SYSTEM_PROMPT,
                temperature=0.3,
            )
            
            # Step 4: Parse response
            analysis = self._parse_llm_response(response)
            
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.SUCCESS,
                verdict=analysis.get("verdict", "unverifiable"),
                confidence=self._parse_confidence(analysis.get("confidence", 0.5)),
                explanation=analysis.get("explanation", ""),
                sources=[
                    {"url": url, "type": "web_search"} 
                    for url in analysis.get("sources_used", [])
                ],
                raw_response={
                    "analysis": analysis,
                    "search_results": [r.to_dict() for r in search_results]
                }
            )
            
        except Exception as e:
            logger.exception(f"LLM verification failed: {e}")
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.ERROR,
                error_message=str(e)
            )
    
    def _format_search_results(
        self, 
        results: List[SearchResult]
    ) -> str:
        """Format search results for the LLM prompt."""
        formatted = []
        
        for i, result in enumerate(results, 1):
            formatted.append(f"""
Result {i}:
- Source: {result.source or 'Unknown'}
- Title: {result.title}
- URL: {result.url}
- Snippet: {result.snippet}
""")
        
        return "\n".join(formatted)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        # Try to extract JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find bare JSON
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If parsing fails, return basic structure with the response as explanation
        logger.warning("Could not parse LLM response as JSON")
        return {
            "verdict": "unverifiable",
            "confidence": 0.3,
            "explanation": response,
        }
    
    def _parse_confidence(self, confidence: Any) -> float:
        """Parse and validate confidence value."""
        try:
            conf = float(confidence)
            return max(0.0, min(1.0, conf))
        except (TypeError, ValueError):
            return 0.5
    
    async def verify_with_context(
        self,
        claim: str,
        context: str,
        additional_search_terms: Optional[List[str]] = None
    ) -> ProviderResult:
        """
        Verify a claim with additional context and search terms.
        
        Args:
            claim: The claim to verify
            context: Surrounding context that might help verification
            additional_search_terms: Extra terms to include in search
            
        Returns:
            ProviderResult with verdict
        """
        # Build enhanced search query
        search_query = claim
        if additional_search_terms:
            search_query = f"{claim} {' '.join(additional_search_terms)}"
        
        # Get search results
        web_search = await self._get_web_search_service()
        search_results = await web_search.search(search_query, num_results=15)
        
        if not search_results:
            return ProviderResult(
                provider=self.provider_type,
                status=VerificationStatus.NO_RESULTS,
                explanation="Could not find relevant search results."
            )
        
        # Enhanced prompt with context
        formatted_results = self._format_search_results(search_results)
        
        llm = self._get_llm_service()
        
        prompt = f"""Evaluate this claim based on the search evidence:

CLAIM: {claim}

CONTEXT (from the original content):
{context[:1000]}

SEARCH RESULTS:
{formatted_results}

Respond with a JSON object:
{{
  "verdict": "true|mostly_true|half_true|mostly_false|false|unverifiable",
  "confidence": 0.0-1.0,
  "explanation": "Detailed explanation",
  "key_evidence": [...],
  "sources_used": [...]
}}"""
        
        response = llm.complete(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=VERIFICATION_SYSTEM_PROMPT,
            temperature=0.3,
        )
        
        analysis = self._parse_llm_response(response)
        
        return ProviderResult(
            provider=self.provider_type,
            status=VerificationStatus.SUCCESS,
            verdict=analysis.get("verdict", "unverifiable"),
            confidence=self._parse_confidence(analysis.get("confidence", 0.5)),
            explanation=analysis.get("explanation", ""),
            sources=[
                {"url": url, "type": "web_search"} 
                for url in analysis.get("sources_used", [])
            ],
            raw_response={"analysis": analysis}
        )
