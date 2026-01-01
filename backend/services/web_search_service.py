"""
Wisdom Agent - Web Search Service

Provides web search capability for fact verification.
Supports multiple backends with fallback:
- DuckDuckGo (default, no API key needed)
- Brave Search (optional, API key)
- Tavily (optional, API key)

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 7
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: Optional[str] = None  # Domain name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
        }


class SearchBackend(ABC):
    """Abstract base class for search backends."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this search backend."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this backend is configured and available."""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Perform a search.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        pass


class DuckDuckGoBackend(SearchBackend):
    """
    DuckDuckGo search backend.
    
    Uses the DuckDuckGo HTML search (no API key required).
    Note: This is rate-limited and should be used respectfully.
    """
    
    BASE_URL = "https://html.duckduckgo.com/html/"
    
    @property
    def name(self) -> str:
        return "DuckDuckGo"
    
    async def is_available(self) -> bool:
        """DuckDuckGo is always available (no API key needed)."""
        return True
    
    async def search(
        self, 
        query: str, 
        num_results: int = 10
    ) -> List[SearchResult]:
        """Search using DuckDuckGo HTML interface."""
        results = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL,
                    data={"q": query, "b": ""},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/120.0.0.0 Safari/537.36"
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                
                # Parse HTML results
                results = self._parse_html_results(response.text, num_results)
                
        except Exception as e:
            logger.exception(f"DuckDuckGo search failed: {e}")
        
        return results
    
    def _parse_html_results(
        self, 
        html: str, 
        num_results: int
    ) -> List[SearchResult]:
        """Parse DuckDuckGo HTML search results."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        results = []
        
        # Find result containers
        for result_div in soup.select(".result"):
            if len(results) >= num_results:
                break
            
            # Get title and URL
            title_elem = result_div.select_one(".result__a")
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get("href", "")
            
            # DuckDuckGo uses redirects, extract actual URL
            if "uddg=" in url:
                match = re.search(r"uddg=([^&]+)", url)
                if match:
                    from urllib.parse import unquote
                    url = unquote(match.group(1))
            
            # Get snippet
            snippet_elem = result_div.select_one(".result__snippet")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Extract domain
            source = None
            if url:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                source = parsed.netloc
            
            if title and url:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=source,
                ))
        
        return results


class BraveSearchBackend(SearchBackend):
    """
    Brave Search API backend.
    
    Requires BRAVE_SEARCH_API_KEY environment variable.
    Free tier: 2,000 queries/month
    """
    
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"
    
    def __init__(self):
        self._api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    
    @property
    def name(self) -> str:
        return "Brave Search"
    
    async def is_available(self) -> bool:
        return bool(self._api_key)
    
    async def search(
        self, 
        query: str, 
        num_results: int = 10
    ) -> List[SearchResult]:
        """Search using Brave Search API."""
        if not self._api_key:
            return []
        
        results = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "q": query,
                        "count": min(num_results, 20),  # Brave max is 20
                    },
                    headers={
                        "X-Subscription-Token": self._api_key,
                        "Accept": "application/json",
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("web", {}).get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", ""),
                        source=item.get("meta_url", {}).get("hostname"),
                    ))
                    
        except Exception as e:
            logger.exception(f"Brave Search failed: {e}")
        
        return results


class TavilyBackend(SearchBackend):
    """
    Tavily Search API backend.
    
    Requires TAVILY_API_KEY environment variable.
    Designed specifically for AI applications.
    """
    
    BASE_URL = "https://api.tavily.com/search"
    
    def __init__(self):
        self._api_key = os.getenv("TAVILY_API_KEY")
    
    @property
    def name(self) -> str:
        return "Tavily"
    
    async def is_available(self) -> bool:
        return bool(self._api_key)
    
    async def search(
        self, 
        query: str, 
        num_results: int = 10
    ) -> List[SearchResult]:
        """Search using Tavily API."""
        if not self._api_key:
            return []
        
        results = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL,
                    json={
                        "api_key": self._api_key,
                        "query": query,
                        "max_results": num_results,
                        "search_depth": "basic",
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source=item.get("source"),
                    ))
                    
        except Exception as e:
            logger.exception(f"Tavily search failed: {e}")
        
        return results


class WebSearchService:
    """
    Main web search service.
    
    Manages multiple search backends with automatic fallback.
    """
    
    def __init__(self):
        """Initialize with all available backends."""
        self._backends: List[SearchBackend] = [
            BraveSearchBackend(),   # Preferred if available
            TavilyBackend(),        # Good for AI applications
            DuckDuckGoBackend(),    # Always available fallback
        ]
    
    async def get_available_backend(self) -> Optional[SearchBackend]:
        """Get the first available search backend."""
        for backend in self._backends:
            if await backend.is_available():
                return backend
        return None
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        prefer_backend: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform a web search.
        
        Args:
            query: The search query
            num_results: Maximum number of results
            prefer_backend: Optional preferred backend name
            
        Returns:
            List of SearchResult objects
        """
        # Find backend to use
        backend = None
        
        if prefer_backend:
            for b in self._backends:
                if b.name.lower() == prefer_backend.lower():
                    if await b.is_available():
                        backend = b
                    break
        
        if not backend:
            backend = await self.get_available_backend()
        
        if not backend:
            logger.error("No search backend available")
            return []
        
        logger.info(f"Searching with {backend.name}: {query[:50]}...")
        results = await backend.search(query, num_results)
        logger.info(f"Found {len(results)} results")
        
        return results
    
    async def search_for_claim(
        self,
        claim: str,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Search for evidence related to a claim.
        
        Constructs a search query optimized for fact-checking.
        
        Args:
            claim: The claim to find evidence for
            num_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        # Construct fact-check optimized query
        query = f'"{claim}"'  # Exact phrase search
        
        results = await self.search(query, num_results)
        
        # If no results, try without quotes
        if not results:
            results = await self.search(claim, num_results)
        
        return results
    
    async def search_fact_checks(
        self,
        claim: str,
        num_results: int = 5
    ) -> List[SearchResult]:
        """
        Search specifically for existing fact checks of a claim.
        
        Args:
            claim: The claim to find fact checks for
            num_results: Maximum number of results
            
        Returns:
            List of SearchResult objects from fact-checking sites
        """
        # Add fact-check keywords to query
        query = f'fact check {claim}'
        
        results = await self.search(query, num_results * 2)
        
        # Filter to known fact-checking domains
        fact_check_domains = {
            "snopes.com", "politifact.com", "factcheck.org",
            "reuters.com/fact-check", "apnews.com/hub/ap-fact-check",
            "fullfact.org", "leadstories.com", "usatoday.com/news/factcheck",
            "washingtonpost.com/news/fact-checker",
        }
        
        fact_check_results = []
        for result in results:
            if result.source:
                source_lower = result.source.lower()
                for domain in fact_check_domains:
                    if domain in source_lower:
                        fact_check_results.append(result)
                        break
            
            if len(fact_check_results) >= num_results:
                break
        
        return fact_check_results


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create the web search service instance."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
