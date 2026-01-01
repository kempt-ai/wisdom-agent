"""
Content Extraction Service

Fetches and extracts clean content from various sources:
- Web pages (HTML → clean text)
- PDFs (local or remote)
- Articles (with metadata extraction)
- Documents (DOCX, TXT, MD)

Uses trafilatura for high-quality article extraction,
with BeautifulSoup as fallback.
"""

import re
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
import asyncio

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ExtractedContent:
    """Result of content extraction"""
    success: bool
    content: str
    title: Optional[str] = None
    author: Optional[str] = None
    publish_date: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    content_type: str = "text/html"
    word_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.content:
            self.word_count = len(self.content.split())


@dataclass 
class FetchResult:
    """Result of URL fetch operation"""
    success: bool
    content: bytes = b""
    content_type: str = ""
    status_code: int = 0
    final_url: str = ""
    error_message: Optional[str] = None
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


# ============================================================================
# CONTENT EXTRACTION SERVICE
# ============================================================================

class ContentExtractor:
    """
    Service for extracting clean content from URLs and files.
    
    Supports:
    - Web pages (HTML articles, blogs, news)
    - PDF documents
    - Plain text files
    - Markdown files
    
    Uses trafilatura for best article extraction quality,
    with BeautifulSoup fallback for edge cases.
    """
    
    # User agent for requests (be a good citizen)
    USER_AGENT = "WisdomAgent/1.0 (Knowledge Base; +https://github.com/kempt-ai/wisdom-agent)"
    
    # Timeout for requests (seconds)
    REQUEST_TIMEOUT = 30
    
    # Maximum content size (10MB)
    MAX_CONTENT_SIZE = 10 * 1024 * 1024
    
    # Domains that need special handling
    SPECIAL_DOMAINS = {
        "twitter.com": "_extract_twitter",
        "x.com": "_extract_twitter", 
        "youtube.com": "_extract_youtube",
        "youtu.be": "_extract_youtube",
        "github.com": "_extract_github",
        "arxiv.org": "_extract_arxiv",
        "medium.com": "_extract_medium",
    }
    
    def __init__(self):
        self._http_client = None
    
    async def _get_client(self):
        """Get or create async HTTP client"""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(
                    timeout=self.REQUEST_TIMEOUT,
                    follow_redirects=True,
                    headers={"User-Agent": self.USER_AGENT}
                )
            except ImportError:
                logger.warning("httpx not installed, using synchronous requests")
                self._http_client = "sync"
        return self._http_client
    
    async def extract_from_url(self, url: str) -> ExtractedContent:
        """
        Extract content from a URL.
        
        Automatically detects content type and uses appropriate extractor.
        """
        # Validate URL
        if not self._is_valid_url(url):
            return ExtractedContent(
                success=False,
                content="",
                error_message=f"Invalid URL: {url}"
            )
        
        # Fetch the content
        fetch_result = await self._fetch_url(url)
        
        if not fetch_result.success:
            return ExtractedContent(
                success=False,
                content="",
                source_url=url,
                error_message=fetch_result.error_message
            )
        
        # Route to appropriate extractor based on content type
        content_type = fetch_result.content_type.lower()
        
        if "pdf" in content_type:
            return await self._extract_pdf(fetch_result.content, url)
        elif "html" in content_type or "text/html" in content_type:
            return await self._extract_html(fetch_result.content, fetch_result.final_url)
        elif "text/plain" in content_type:
            return self._extract_text(fetch_result.content, url)
        elif "text/markdown" in content_type or url.endswith(".md"):
            return self._extract_markdown(fetch_result.content, url)
        elif "json" in content_type:
            return self._extract_json(fetch_result.content, url)
        else:
            # Try HTML extraction as fallback
            return await self._extract_html(fetch_result.content, fetch_result.final_url)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and safe to fetch"""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only allow http/https
            if parsed.scheme not in ("http", "https"):
                return False
            
            # Block local/private IPs
            netloc = parsed.netloc.lower()
            blocked = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
            if any(b in netloc for b in blocked):
                return False
            
            # Block private IP ranges
            if re.match(r"^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)", netloc):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _fetch_url(self, url: str) -> FetchResult:
        """Fetch content from URL"""
        try:
            client = await self._get_client()
            
            if client == "sync":
                # Fallback to synchronous requests
                return await self._fetch_sync(url)
            
            response = await client.get(url)
            
            # Check size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_CONTENT_SIZE:
                return FetchResult(
                    success=False,
                    error_message=f"Content too large: {content_length} bytes"
                )
            
            return FetchResult(
                success=True,
                content=response.content,
                content_type=response.headers.get("content-type", "text/html"),
                status_code=response.status_code,
                final_url=str(response.url),
                headers=dict(response.headers)
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return FetchResult(
                success=False,
                error_message=str(e)
            )
    
    async def _fetch_sync(self, url: str) -> FetchResult:
        """Synchronous fetch fallback using requests"""
        try:
            import requests
            
            response = requests.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                headers={"User-Agent": self.USER_AGENT},
                allow_redirects=True
            )
            
            return FetchResult(
                success=True,
                content=response.content,
                content_type=response.headers.get("content-type", "text/html"),
                status_code=response.status_code,
                final_url=response.url,
                headers=dict(response.headers)
            )
            
        except ImportError:
            return FetchResult(
                success=False,
                error_message="Neither httpx nor requests is installed"
            )
        except Exception as e:
            return FetchResult(
                success=False,
                error_message=str(e)
            )
    
    async def _extract_html(self, content: bytes, url: str) -> ExtractedContent:
        """Extract article content from HTML"""
        
        # Decode content
        text_content = self._decode_content(content)
        
        # Check for special domain handling
        domain = urlparse(url).netloc.lower()
        for special_domain, handler_name in self.SPECIAL_DOMAINS.items():
            if special_domain in domain:
                handler = getattr(self, handler_name, None)
                if handler:
                    return handler(text_content, url)
        
        # Try trafilatura first (best quality)
        try:
            import trafilatura
            
            # Extract with trafilatura
            extracted = trafilatura.extract(
                text_content,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
                url=url
            )
            
            if extracted and len(extracted) > 100:
                # Get metadata
                metadata = trafilatura.extract_metadata(text_content)
                
                return ExtractedContent(
                    success=True,
                    content=extracted,
                    title=metadata.title if metadata else self._extract_title_fallback(text_content),
                    author=metadata.author if metadata else None,
                    publish_date=str(metadata.date) if metadata and metadata.date else None,
                    description=metadata.description if metadata else None,
                    source_url=url,
                    content_type="text/html",
                    metadata={
                        "extractor": "trafilatura",
                        "sitename": metadata.sitename if metadata else None,
                        "categories": metadata.categories if metadata else None,
                    }
                )
        except ImportError:
            logger.info("trafilatura not installed, using BeautifulSoup fallback")
        except Exception as e:
            logger.warning(f"trafilatura extraction failed: {e}")
        
        # Fallback to BeautifulSoup
        return self._extract_with_beautifulsoup(text_content, url)
    
    def _extract_with_beautifulsoup(self, html: str, url: str) -> ExtractedContent:
        """BeautifulSoup fallback for HTML extraction"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove unwanted elements
            for element in soup.find_all(["script", "style", "nav", "header", 
                                          "footer", "aside", "iframe", "noscript"]):
                element.decompose()
            
            # Try to find main content
            main_content = None
            
            # Look for article tag
            article = soup.find("article")
            if article:
                main_content = article
            
            # Look for main tag
            if not main_content:
                main = soup.find("main")
                if main:
                    main_content = main
            
            # Look for common content divs
            if not main_content:
                for class_name in ["content", "post-content", "article-content", 
                                   "entry-content", "post-body", "article-body"]:
                    content_div = soup.find(class_=re.compile(class_name, re.I))
                    if content_div:
                        main_content = content_div
                        break
            
            # Fallback to body
            if not main_content:
                main_content = soup.find("body") or soup
            
            # Extract text
            text = main_content.get_text(separator="\n", strip=True)
            
            # Clean up excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" {2,}", " ", text)
            
            # Extract metadata
            title = None
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Try og:title or h1
            if not title:
                og_title = soup.find("meta", property="og:title")
                if og_title:
                    title = og_title.get("content")
            
            if not title:
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)
            
            # Get description
            description = None
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content")
            
            # Get author
            author = None
            author_meta = soup.find("meta", attrs={"name": "author"})
            if author_meta:
                author = author_meta.get("content")
            
            return ExtractedContent(
                success=True,
                content=text,
                title=title,
                author=author,
                description=description,
                source_url=url,
                content_type="text/html",
                metadata={"extractor": "beautifulsoup"}
            )
            
        except ImportError:
            return ExtractedContent(
                success=False,
                content="",
                source_url=url,
                error_message="BeautifulSoup not installed. Install with: pip install beautifulsoup4"
            )
        except Exception as e:
            return ExtractedContent(
                success=False,
                content="",
                source_url=url,
                error_message=f"HTML extraction failed: {e}"
            )
    
    async def _extract_pdf(self, content: bytes, url: str) -> ExtractedContent:
        """Extract text from PDF"""
        try:
            # Try pypdf first
            try:
                from pypdf import PdfReader
                import io
                
                reader = PdfReader(io.BytesIO(content))
                text_parts = []
                
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                full_text = "\n\n".join(text_parts)
                
                # Get metadata
                metadata = reader.metadata or {}
                
                return ExtractedContent(
                    success=True,
                    content=full_text,
                    title=metadata.get("/Title"),
                    author=metadata.get("/Author"),
                    source_url=url,
                    content_type="application/pdf",
                    metadata={
                        "extractor": "pypdf",
                        "pages": len(reader.pages),
                        "creator": metadata.get("/Creator"),
                    }
                )
                
            except ImportError:
                pass
            
            # Try pdfplumber as fallback
            try:
                import pdfplumber
                import io
                
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    
                    full_text = "\n\n".join(text_parts)
                    
                    return ExtractedContent(
                        success=True,
                        content=full_text,
                        source_url=url,
                        content_type="application/pdf",
                        metadata={
                            "extractor": "pdfplumber",
                            "pages": len(pdf.pages)
                        }
                    )
                    
            except ImportError:
                pass
            
            return ExtractedContent(
                success=False,
                content="",
                source_url=url,
                error_message="No PDF library installed. Install with: pip install pypdf or pip install pdfplumber"
            )
            
        except Exception as e:
            return ExtractedContent(
                success=False,
                content="",
                source_url=url,
                error_message=f"PDF extraction failed: {e}"
            )
    
    def _extract_text(self, content: bytes, url: str) -> ExtractedContent:
        """Extract plain text content"""
        text = self._decode_content(content)
        
        # Try to extract title from first line
        lines = text.strip().split("\n")
        title = lines[0][:100] if lines else None
        
        return ExtractedContent(
            success=True,
            content=text,
            title=title,
            source_url=url,
            content_type="text/plain",
            metadata={"extractor": "plain_text"}
        )
    
    def _extract_markdown(self, content: bytes, url: str) -> ExtractedContent:
        """Extract markdown content"""
        text = self._decode_content(content)
        
        # Extract title from first H1
        title = None
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
        
        return ExtractedContent(
            success=True,
            content=text,
            title=title,
            source_url=url,
            content_type="text/markdown",
            metadata={"extractor": "markdown"}
        )
    
    def _extract_json(self, content: bytes, url: str) -> ExtractedContent:
        """Extract and format JSON content"""
        import json
        
        text = self._decode_content(content)
        
        try:
            data = json.loads(text)
            formatted = json.dumps(data, indent=2)
            
            return ExtractedContent(
                success=True,
                content=formatted,
                source_url=url,
                content_type="application/json",
                metadata={"extractor": "json"}
            )
        except json.JSONDecodeError as e:
            return ExtractedContent(
                success=False,
                content="",
                source_url=url,
                error_message=f"Invalid JSON: {e}"
            )
    
    # ========================================================================
    # SPECIAL DOMAIN HANDLERS
    # ========================================================================
    
    def _extract_twitter(self, html: str, url: str) -> ExtractedContent:
        """Handle Twitter/X URLs"""
        # Twitter requires JavaScript, so we can't extract much
        # Return a placeholder with the URL for manual handling
        return ExtractedContent(
            success=True,
            content=f"Twitter/X post: {url}\n\n[Twitter content requires JavaScript and cannot be directly extracted. Consider using the Twitter API or copying the tweet text manually.]",
            title="Twitter Post",
            source_url=url,
            content_type="text/html",
            metadata={"extractor": "twitter_placeholder", "requires_js": True}
        )
    
    def _extract_youtube(self, html: str, url: str) -> ExtractedContent:
        """Handle YouTube URLs"""
        # Extract video ID
        video_id = None
        patterns = [
            r"youtube\.com/watch\?v=([^&]+)",
            r"youtu\.be/([^?]+)",
            r"youtube\.com/embed/([^?]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        # Try to get title from HTML
        title = self._extract_title_fallback(html)
        
        content = f"YouTube Video: {url}\n\n"
        if video_id:
            content += f"Video ID: {video_id}\n\n"
        content += "[YouTube video content. Consider using YouTube's API or transcript feature for full content.]"
        
        return ExtractedContent(
            success=True,
            content=content,
            title=title or "YouTube Video",
            source_url=url,
            content_type="text/html",
            metadata={"extractor": "youtube", "video_id": video_id}
        )
    
    def _extract_github(self, html: str, url: str) -> ExtractedContent:
        """Handle GitHub URLs - especially README files"""
        # Use standard extraction but note it's from GitHub
        result = self._extract_with_beautifulsoup(html, url)
        result.metadata["extractor"] = "github"
        result.metadata["source"] = "github"
        return result
    
    def _extract_arxiv(self, html: str, url: str) -> ExtractedContent:
        """Handle arXiv URLs"""
        # Check if this is a PDF link
        if "/pdf/" in url:
            # Redirect to abstract page for metadata
            abstract_url = url.replace("/pdf/", "/abs/").replace(".pdf", "")
            return ExtractedContent(
                success=True,
                content=f"arXiv paper: {url}\n\nThis is a PDF link. For full text extraction, the PDF will be downloaded separately.\n\nAbstract page: {abstract_url}",
                source_url=url,
                content_type="text/html",
                metadata={"extractor": "arxiv", "is_pdf": True, "abstract_url": abstract_url}
            )
        
        # Extract abstract page
        result = self._extract_with_beautifulsoup(html, url)
        result.metadata["extractor"] = "arxiv"
        return result
    
    def _extract_medium(self, html: str, url: str) -> ExtractedContent:
        """Handle Medium articles"""
        # Medium works well with trafilatura/beautifulsoup
        # Just add metadata noting the source
        result = self._extract_with_beautifulsoup(html, url)
        result.metadata["source"] = "medium"
        return result
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _decode_content(self, content: bytes) -> str:
        """Decode bytes to string with encoding detection"""
        # Try UTF-8 first
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            pass
        
        # Try to detect encoding
        try:
            import chardet
            detected = chardet.detect(content)
            if detected and detected.get("encoding"):
                return content.decode(detected["encoding"])
        except ImportError:
            pass
        
        # Fallback encodings
        for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # Last resort: decode with replacement
        return content.decode("utf-8", errors="replace")
    
    def _extract_title_fallback(self, html: str) -> Optional[str]:
        """Quick title extraction without full parsing"""
        # Try <title> tag
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try og:title
        match = re.search(r'property="og:title"\s+content="([^"]+)"', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try first h1
        match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client and self._http_client != "sync":
            await self._http_client.aclose()
            self._http_client = None


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_extractor: Optional[ContentExtractor] = None


def get_content_extractor() -> ContentExtractor:
    """Get singleton ContentExtractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = ContentExtractor()
    return _extractor


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def extract_url(url: str) -> ExtractedContent:
    """Convenience function to extract content from a URL"""
    extractor = get_content_extractor()
    return await extractor.extract_from_url(url)


async def extract_urls(urls: list[str]) -> list[ExtractedContent]:
    """Extract content from multiple URLs concurrently"""
    extractor = get_content_extractor()
    tasks = [extractor.extract_from_url(url) for url in urls]
    return await asyncio.gather(*tasks)
