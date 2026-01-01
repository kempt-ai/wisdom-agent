"""
Wisdom Agent - Fact Check Provider Registry

Manages all available fact-checking providers and coordinates
verification across multiple sources.

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 7
"""

import logging
from typing import Optional, List, Dict, Any, Type

from backend.providers.base import (
    FactCheckProvider, ProviderType, ProviderResult,
    VerificationStatus, ExternalFactCheck
)

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for fact-checking providers.
    
    Responsibilities:
    - Manage provider instances
    - Route requests to appropriate providers
    - Aggregate results from multiple providers
    - Handle provider availability and fallbacks
    """
    
    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[ProviderType, FactCheckProvider] = {}
        self._priority_order: List[ProviderType] = [
            # Order providers by preference
            ProviderType.GOOGLE_FACT_CHECK,  # Check existing fact checks first
            ProviderType.CLAIM_BUSTER,       # Then use ClaimBuster
            ProviderType.LLM_VERIFICATION,   # Then LLM with web search
            ProviderType.WEB_SEARCH,         # Finally, direct web search
        ]
    
    # ========================================================================
    # PROVIDER MANAGEMENT
    # ========================================================================
    
    def register(self, provider: FactCheckProvider):
        """
        Register a provider with the registry.
        
        Args:
            provider: The provider instance to register
        """
        self._providers[provider.provider_type] = provider
        logger.info(f"Registered provider: {provider.name}")
    
    def unregister(self, provider_type: ProviderType):
        """
        Remove a provider from the registry.
        
        Args:
            provider_type: The type of provider to remove
        """
        if provider_type in self._providers:
            del self._providers[provider_type]
            logger.info(f"Unregistered provider: {provider_type.value}")
    
    def get_provider(
        self, 
        provider_type: ProviderType
    ) -> Optional[FactCheckProvider]:
        """
        Get a specific provider by type.
        
        Args:
            provider_type: The type of provider to get
            
        Returns:
            The provider instance, or None if not registered
        """
        return self._providers.get(provider_type)
    
    async def get_available_providers(self) -> List[FactCheckProvider]:
        """
        Get all providers that are currently available.
        
        Returns:
            List of available provider instances
        """
        available = []
        for provider_type in self._priority_order:
            provider = self._providers.get(provider_type)
            if provider and await provider.is_available():
                available.append(provider)
        return available
    
    def set_priority_order(self, order: List[ProviderType]):
        """
        Set the priority order for providers.
        
        Args:
            order: List of provider types in priority order
        """
        self._priority_order = order
    
    # ========================================================================
    # CLAIM VERIFICATION
    # ========================================================================
    
    async def check_claim(
        self,
        claim: str,
        context: Optional[str] = None,
        providers: Optional[List[ProviderType]] = None,
        require_consensus: bool = False
    ) -> Dict[str, Any]:
        """
        Check a claim using available providers.
        
        Args:
            claim: The claim text to verify
            context: Optional surrounding context
            providers: Specific providers to use (or None for all available)
            require_consensus: If True, use multiple providers and aggregate
            
        Returns:
            Dict containing:
            - results: List of ProviderResults
            - consensus_verdict: Aggregated verdict (if multiple providers)
            - confidence: Overall confidence score
            - providers_used: List of provider names used
        """
        results = []
        providers_used = []
        
        # Determine which providers to use
        if providers:
            target_providers = [
                self._providers[pt] for pt in providers 
                if pt in self._providers
            ]
        else:
            target_providers = await self.get_available_providers()
        
        if not target_providers:
            return {
                "results": [],
                "consensus_verdict": None,
                "confidence": 0.0,
                "providers_used": [],
                "error": "No providers available"
            }
        
        # Run verification with each provider
        for provider in target_providers:
            try:
                result = await provider.check_claim(claim, context)
                results.append(result)
                providers_used.append(provider.name)
                
                # If not requiring consensus, stop after first successful result
                if not require_consensus and result.status == VerificationStatus.SUCCESS:
                    break
                    
            except Exception as e:
                logger.exception(f"Provider {provider.name} failed: {e}")
                results.append(ProviderResult(
                    provider=provider.provider_type,
                    status=VerificationStatus.ERROR,
                    error_message=str(e)
                ))
        
        # Aggregate results
        consensus = self._aggregate_results(results) if require_consensus else None
        
        return {
            "results": [r.to_dict() for r in results],
            "consensus_verdict": consensus.get("verdict") if consensus else (
                results[0].verdict if results and results[0].status == VerificationStatus.SUCCESS else None
            ),
            "confidence": consensus.get("confidence") if consensus else (
                results[0].confidence if results else 0.0
            ),
            "providers_used": providers_used,
        }
    
    async def find_existing_fact_checks(
        self, 
        claim: str
    ) -> List[ExternalFactCheck]:
        """
        Search for existing fact checks across all providers.
        
        Args:
            claim: The claim to search for
            
        Returns:
            List of existing fact checks found
        """
        all_fact_checks = []
        
        for provider in self._providers.values():
            try:
                fact_checks = await provider.find_existing_fact_checks(claim)
                all_fact_checks.extend(fact_checks)
            except Exception as e:
                logger.warning(f"Provider {provider.name} fact check search failed: {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_fact_checks = []
        for fc in all_fact_checks:
            if fc.url not in seen_urls:
                seen_urls.add(fc.url)
                unique_fact_checks.append(fc)
        
        return unique_fact_checks
    
    async def triage_claim(self, claim: str) -> float:
        """
        Get a check-worthiness score for a claim.
        
        Uses the first available provider that supports triage.
        
        Args:
            claim: The claim to evaluate
            
        Returns:
            Check-worthiness score (0.0 to 1.0)
        """
        # Prefer ClaimBuster for triage
        if ProviderType.CLAIM_BUSTER in self._providers:
            provider = self._providers[ProviderType.CLAIM_BUSTER]
            if await provider.is_available():
                try:
                    return await provider.triage_claim(claim)
                except Exception as e:
                    logger.warning(f"ClaimBuster triage failed: {e}")
        
        # Fall back to default
        return 0.5
    
    # ========================================================================
    # RESULT AGGREGATION
    # ========================================================================
    
    def _aggregate_results(
        self, 
        results: List[ProviderResult]
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple providers into a consensus.
        
        Uses weighted voting based on confidence scores.
        """
        if not results:
            return {"verdict": None, "confidence": 0.0}
        
        # Filter to successful results with verdicts
        valid_results = [
            r for r in results 
            if r.status == VerificationStatus.SUCCESS and r.verdict
        ]
        
        if not valid_results:
            return {"verdict": None, "confidence": 0.0}
        
        # Map verdicts to normalized scale
        verdict_scores = {
            "true": 1.0,
            "mostly_true": 0.75,
            "half_true": 0.5,
            "mixed": 0.5,
            "mostly_false": 0.25,
            "false": 0.0,
            "unverifiable": None,
        }
        
        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0
        
        for result in valid_results:
            verdict_lower = result.verdict.lower().replace("-", "_").replace(" ", "_")
            score = verdict_scores.get(verdict_lower)
            
            if score is not None:
                weight = result.confidence
                weighted_sum += score * weight
                total_weight += weight
        
        if total_weight == 0:
            return {"verdict": "unverifiable", "confidence": 0.0}
        
        avg_score = weighted_sum / total_weight
        avg_confidence = total_weight / len(valid_results)
        
        # Convert back to verdict
        if avg_score >= 0.8:
            consensus_verdict = "true"
        elif avg_score >= 0.6:
            consensus_verdict = "mostly_true"
        elif avg_score >= 0.4:
            consensus_verdict = "mixed"
        elif avg_score >= 0.2:
            consensus_verdict = "mostly_false"
        else:
            consensus_verdict = "false"
        
        return {
            "verdict": consensus_verdict,
            "confidence": avg_confidence,
            "score": avg_score,
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_provider_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get or create the provider registry instance."""
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = ProviderRegistry()
    return _provider_registry


async def initialize_providers():
    """
    Initialize and register all available providers.
    
    Call this at application startup.
    """
    registry = get_provider_registry()
    
    # Import providers (they're created in Day 8)
    try:
        from backend.providers.google_factcheck import GoogleFactCheckProvider
        provider = GoogleFactCheckProvider()
        if await provider.is_available():
            registry.register(provider)
    except ImportError:
        logger.debug("Google Fact Check provider not available")
    
    try:
        from backend.providers.claimbuster import ClaimBusterProvider
        provider = ClaimBusterProvider()
        if await provider.is_available():
            registry.register(provider)
    except ImportError:
        logger.debug("ClaimBuster provider not available")
    
    try:
        from backend.providers.llm_verification import LLMVerificationProvider
        provider = LLMVerificationProvider()
        if await provider.is_available():
            registry.register(provider)
    except ImportError:
        logger.debug("LLM verification provider not available")
    
    available = await registry.get_available_providers()
    logger.info(f"Initialized {len(available)} fact-check providers")
