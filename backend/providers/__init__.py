"""
Wisdom Agent - Fact Check Providers Package

This package contains providers for fact-checking claims:
- ClaimBuster: Check-worthiness scoring and fact-check database
- Google Fact Check: Google's fact-check aggregator
- LLM Verification: LLM-based verification with web search

Usage:
    from backend.providers import get_provider_registry, initialize_providers
    
    # At startup
    await initialize_providers()
    
    # To check a claim
    registry = get_provider_registry()
    result = await registry.check_claim("The earth is round")
"""

from backend.providers.base import (
    FactCheckProvider,
    ProviderType,
    ProviderResult,
    VerificationStatus,
    ExternalFactCheck,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderRateLimitError,
    ProviderAPIError,
)

from backend.providers.registry import (
    ProviderRegistry,
    get_provider_registry,
    initialize_providers,
)

__all__ = [
    # Base classes
    "FactCheckProvider",
    "ProviderType",
    "ProviderResult",
    "VerificationStatus",
    "ExternalFactCheck",
    # Exceptions
    "ProviderError",
    "ProviderNotConfiguredError",
    "ProviderRateLimitError",
    "ProviderAPIError",
    # Registry
    "ProviderRegistry",
    "get_provider_registry",
    "initialize_providers",
]
