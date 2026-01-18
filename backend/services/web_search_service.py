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
Updated: 2025-01-17 - Improved search_for_claim with key term extraction
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Set

import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# STOPWORDS FOR QUERY OPTIMIZATION
# ============================================================================

# Common words to filter out when extracting search terms
STOPWORDS: Set[str] = {
    # Articles
    "a", "an", "the",
    # Conjunctions
    "and", "or", "but", "nor", "so", "yet", "for",
    # Prepositions
    "in", "on", "at", "to", "from", "by", "with", "about", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "under", "over", "of", "as", "into", "onto", "upon",
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "who", "whom", "which", "what",
    # Common verbs (when used as auxiliaries)
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "could", "should", "may", "might", "must", "shall",
    "can", "need", "dare", "ought", "used",
    # Other common words
    "each", "every", "both", "all", "any", "some", "no", "not",
    "only", "own", "same", "than", "too", "very", "just", "also",
    "now", "here", "there", "when", "where", "why", "how",
    "if", "then", "else", "because", "although", "though", "while",
    # Claim-specific filler words
    "said", "says", "according", "claimed", "claims", "stated", "states",
    "reported", "reports", "allegedly", "supposedly", "apparently",
    "actually", "really", "basically", "essentially", "generally",
}


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
                print(f"DEBUG DuckDuckGo: POSTing query='{query}'")
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
                print(f"DEBUG DuckDuckGo: response status={response.status_code}, len={len(response.text)}")
                
                # Parse HTML results
                results = self._parse_html_results(response.text, num_results)
                print(f"DEBUG DuckDuckGo: parsed {len(results)} results")
                
        except Exception as e:
            print(f"DEBUG DuckDuckGo: EXCEPTION: {e}")
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
        print(f"DEBUG WebSearchService.search: backend={backend.name}, query='{query}'")
        results = await backend.search(query, num_results)
        print(f"DEBUG WebSearchService.search: got {len(results)} results")
        logger.info(f"Found {len(results)} results")
        
        return results
    
    def _extract_search_terms(
        self, 
        claim: str, 
        max_terms: int = 8
    ) -> str:
        """
        Extract key search terms from a claim.
        
        Prioritizes:
        1. Proper nouns (capitalized words)
        2. Numbers and monetary amounts
        3. Quoted phrases
        4. Other significant words (not stopwords)
        
        Args:
            claim: The claim text to extract terms from
            max_terms: Maximum number of terms to include
            
        Returns:
            A concise search query string
        """
        # Extract quoted phrases first (preserve these intact)
        quoted_phrases = re.findall(r'"([^"]+)"', claim)
        
        # Remove quoted phrases from claim for further processing
        remaining = re.sub(r'"[^"]+"', ' ', claim)
        
        # Extract monetary amounts (e.g., "$50 million", "tens of millions")
        money_patterns = re.findall(
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand))?|'
            r'(?:tens|hundreds|thousands|millions|billions)\s+of\s+(?:dollars|millions|billions)',
            remaining, 
            re.IGNORECASE
        )
        
        # Extract years (4-digit numbers that look like years)
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', remaining)
        
        # Extract percentages
        percentages = re.findall(r'\d+(?:\.\d+)?%', remaining)
        
        # Tokenize remaining text
        words = re.findall(r'\b[A-Za-z0-9]+\b', remaining)
        
        # Separate proper nouns (capitalized) and regular words
        proper_nouns = []
        regular_words = []
        
        for word in words:
            # Skip very short words
            if len(word) < 2:
                continue
            
            word_lower = word.lower()
            
            # Skip stopwords
            if word_lower in STOPWORDS:
                continue
            
            # Check if it's a proper noun (capitalized and not at sentence start)
            # We'll be generous and include any capitalized word
            if word[0].isupper() and not word.isupper():
                proper_nouns.append(word)
            elif word.isupper() and len(word) > 1:
                # Acronyms like "ABC", "FBI", "CEO"
                proper_nouns.append(word)
            else:
                regular_words.append(word_lower)
        
        # Build the query, prioritizing in order:
        # 1. Quoted phrases
        # 2. Proper nouns (names, organizations, places)
        # 3. Numbers (money, years, percentages)
        # 4. Other significant words
        
        terms = []
        
        # Add quoted phrases (limit to first 2)
        for phrase in quoted_phrases[:2]:
            if len(phrase.split()) <= 4:  # Only short phrases
                terms.append(f'"{phrase}"')
        
        # Add proper nouns (deduplicated)
        seen_proper = set()
        for noun in proper_nouns:
            noun_lower = noun.lower()
            if noun_lower not in seen_proper:
                seen_proper.add(noun_lower)
                terms.append(noun)
        
        # Add monetary amounts
        terms.extend(money_patterns[:2])
        
        # Add years and percentages
        terms.extend(years[:2])
        terms.extend(percentages[:2])
        
        # Add regular words if we need more terms
        seen_regular = set()
        for word in regular_words:
            if word not in seen_regular and word not in seen_proper:
                seen_regular.add(word)
                terms.append(word)
        
        # Limit total terms
        terms = terms[:max_terms]
        
        # Join into query string
        query = ' '.join(terms)
        
        logger.debug(f"Extracted search terms: '{query}' from claim: '{claim[:50]}...'")
        
        return query
    
    async def search_for_claim(
        self,
        claim: str,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Search for evidence related to a claim.
        
        Uses intelligent term extraction to construct effective search queries.
        Tries multiple search strategies with fallback.
        
        Args:
            claim: The claim to find evidence for
            num_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        all_results = []
        
        # Strategy 1: Extract key terms (most likely to succeed)
        key_terms = self._extract_search_terms(claim)
        print(f"DEBUG search_for_claim: claim='{claim[:60]}...'")
        print(f"DEBUG search_for_claim: extracted key_terms='{key_terms}'")
        
        if key_terms:
            logger.info(f"Search strategy 1 - Key terms: {key_terms}")
            results = await self.search(key_terms, num_results)
            print(f"DEBUG search_for_claim: strategy 1 got {len(results)} results")
            if results:
                return results
        
        # Strategy 2: Try with fewer terms if first attempt failed
        if key_terms and len(key_terms.split()) > 4:
            shorter_terms = ' '.join(key_terms.split()[:4])
            print(f"DEBUG search_for_claim: strategy 2 shorter_terms='{shorter_terms}'")
            logger.info(f"Search strategy 2 - Shorter terms: {shorter_terms}")
            results = await self.search(shorter_terms, num_results)
            print(f"DEBUG search_for_claim: strategy 2 got {len(results)} results")
            if results:
                return results
        
        # Strategy 3: If claim is short enough, try it directly (no quotes)
        if len(claim.split()) <= 10:
            print(f"DEBUG search_for_claim: strategy 3 direct claim")
            logger.info(f"Search strategy 3 - Direct claim (short)")
            results = await self.search(claim, num_results)
            print(f"DEBUG search_for_claim: strategy 3 got {len(results)} results")
            if results:
                return results
        
        # Strategy 4: Last resort - try first part of claim
        first_part = ' '.join(claim.split()[:8])
        print(f"DEBUG search_for_claim: strategy 4 first_part='{first_part}'")
        logger.info(f"Search strategy 4 - First part: {first_part}")
        results = await self.search(first_part, num_results)
        print(f"DEBUG search_for_claim: strategy 4 got {len(results)} results")
        
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
        # Extract key terms instead of using full claim
        key_terms = self._extract_search_terms(claim, max_terms=5)
        
        # Add fact-check keywords to query
        query = f'fact check {key_terms}'
        
        logger.info(f"Searching for fact checks: {query}")
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
