"""
Wisdom Agent - Fact Check Provider Base

Defines the interface for all fact-checking providers.
Providers can be external APIs (ClaimBuster, Google Fact Check)
or internal services (LLM verification).

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 7
"""

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class ProviderType(enum.Enum):
    """Types of fact-checking providers."""
    CLAIM_BUSTER = "claimbuster"       # ClaimBuster API
    GOOGLE_FACT_CHECK = "google"       # Google Fact Check API
    LLM_VERIFICATION = "llm"           # LLM with web search
    WEB_SEARCH = "web_search"          # Direct web search
    FACTICITY = "facticity"            # Premium provider (future)


class VerificationStatus(enum.Enum):
    """Status of a verification attempt."""
    SUCCESS = "success"
    NO_RESULTS = "no_results"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ProviderResult:
    """Result from a fact-check provider."""
    provider: ProviderType
    status: VerificationStatus
    
    # Verdict (if available)
    verdict: Optional[str] = None  # true, false, mixed, etc.
    confidence: float = 0.0        # 0.0 to 1.0
    
    # Evidence and explanation
    explanation: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    
    # Raw data from provider
    raw_response: Optional[Dict[str, Any]] = None
    
    # Error information
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "provider": self.provider.value,
            "status": self.status.value,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "sources": self.sources,
            "error_message": self.error_message,
        }


@dataclass
class ExternalFactCheck:
    """A fact check found from an external source."""
    source: str           # e.g., "Snopes", "PolitiFact"
    claim_reviewed: str   # The claim that was checked
    verdict: str          # Their verdict
    url: str              # Link to the fact check
    review_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "claim_reviewed": self.claim_reviewed,
            "verdict": self.verdict,
            "url": self.url,
            "review_date": self.review_date,
        }


class FactCheckProvider(ABC):
    """
    Abstract base class for fact-checking providers.
    
    All providers must implement:
    - check_claim(): Verify a single claim
    - is_available(): Check if provider is configured and working
    
    Optional methods:
    - triage_claim(): Score how check-worthy a claim is
    - batch_check(): Check multiple claims at once
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the type of this provider."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this provider."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if this provider is configured and available.
        
        Returns:
            True if the provider can be used, False otherwise
        """
        pass
    
    @abstractmethod
    async def check_claim(
        self, 
        claim: str,
        context: Optional[str] = None
    ) -> ProviderResult:
        """
        Verify a claim using this provider.
        
        Args:
            claim: The claim text to verify
            context: Optional surrounding context
            
        Returns:
            ProviderResult with verdict and evidence
        """
        pass
    
    async def triage_claim(self, claim: str) -> float:
        """
        Score how check-worthy a claim is (0.0 to 1.0).
        
        Higher scores indicate claims that are more important to verify.
        Default implementation returns 0.5 for all claims.
        
        Args:
            claim: The claim text to evaluate
            
        Returns:
            Check-worthiness score between 0.0 and 1.0
        """
        return 0.5
    
    async def batch_check(
        self, 
        claims: List[str],
        context: Optional[str] = None
    ) -> List[ProviderResult]:
        """
        Check multiple claims at once.
        
        Default implementation calls check_claim for each claim.
        Override for providers that support batch operations.
        
        Args:
            claims: List of claim texts to verify
            context: Optional shared context
            
        Returns:
            List of ProviderResults, one per claim
        """
        results = []
        for claim in claims:
            result = await self.check_claim(claim, context)
            results.append(result)
        return results
    
    async def find_existing_fact_checks(
        self, 
        claim: str
    ) -> List[ExternalFactCheck]:
        """
        Find existing fact checks for a claim.
        
        Default implementation returns empty list.
        Override for providers that can search fact-check databases.
        
        Args:
            claim: The claim to search for
            
        Returns:
            List of existing fact checks found
        """
        return []


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class ProviderNotConfiguredError(ProviderError):
    """Raised when a provider is not properly configured."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when a provider rate limit is hit."""
    pass


class ProviderAPIError(ProviderError):
    """Raised when a provider API call fails."""
    pass
