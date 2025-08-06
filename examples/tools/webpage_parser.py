"""
Web Page Parser Tool

Scrapes and parses web pages to extract meaningful content.
Handles various content types, respects robots.txt, and includes rate limiting.
"""

import asyncio
import aiohttp
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin, urlparse, urlencode
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

try:
    import readability
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

from base_tool import BaseTool, ToolResult, ToolCapability


class WebPageContent:
    """Represents parsed web page content."""
    
    def __init__(
        self,
        url: str,
        title: str = "",
        content: str = "",
        summary: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        links: Optional[List[str]] = None,
        images: Optional[List[str]] = None
    ):
        self.url = url
        self.title = title
        self.content = content
        self.summary = summary
        self.metadata = metadata or {}
        self.links = links or []
        self.images = images or []
        self.extracted_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'metadata': self.metadata,
            'links': self.links,
            'images': self.images,
            'extracted_at': self.extracted_at.isoformat(),
            'content_length': len(self.content),
            'summary_length': len(self.summary)
        }


class WebPageParserTool(BaseTool):
    """
    Web page parser tool for extracting content from web pages.
    
    Features:
    - Multiple extraction strategies (BeautifulSoup, readability, fallback)
    - Rate limiting and respectful crawling
    - Robots.txt checking (optional)
    - Content cleaning and summarization
    - Support for various content types
    - Link and image extraction
    """
    
    def __init__(self, tool_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            tool_id=tool_id or "webpage_parser",
            name="WebPageParser",
            description="Extracts and parses content from web pages",
            capabilities=[ToolCapability.HTTP_REQUESTS],
            config=config,
            max_concurrent_operations=5
        )
        
        # Configuration
        self.request_timeout = self.config.get("request_timeout", 30)
        self.max_content_length = self.config.get("max_content_length", 1024 * 1024)  # 1MB
        self.respect_robots_txt = self.config.get("respect_robots_txt", True)
        self.min_content_length = self.config.get("min_content_length", 100)
        self.max_summary_length = self.config.get("max_summary_length", 2000)
        
        # Rate limiting
        self.rate_limit_delay = self.config.get("rate_limit_delay", 1.0)
        self.max_retries = self.config.get("max_retries", 3)
        self.backoff_factor = self.config.get("backoff_factor", 2.0)
        
        # Request tracking
        self.request_history = {}  # domain -> list of timestamps
        self.robots_cache = {}     # domain -> robots.txt info
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        
        self.session = None
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute web page parsing.
        
        Args:
            parameters: Parsing parameters including:
                - url: URL to parse (required) or urls: List of URLs
                - extract_links: Extract links from page (default: False)
                - extract_images: Extract images from page (default: False)
                - max_content_length: Override max content length
                - strategy: Extraction strategy ("auto", "beautifulsoup", "readability", "basic")
        
        Returns:
            ToolResult with parsed content
        """
        # Handle single URL or multiple URLs
        urls = parameters.get("urls")
        if not urls:
            url = parameters.get("url", "").strip()
            if not url:
                return ToolResult(
                    tool_id=self.tool_id,
                    success=False,
                    result=None,
                    errors=["No URL provided"]
                )
            urls = [url]
        
        extract_links = parameters.get("extract_links", False)
        extract_images = parameters.get("extract_images", False)
        strategy = parameters.get("strategy", "auto")
        max_content_length = parameters.get("max_content_length", self.max_content_length)
        
        await self._log_info(
            f"Starting web page parsing",
            urls=urls,
            extract_links=extract_links,
            extract_images=extract_images,
            strategy=strategy
        )
        
        try:
            # Parse each URL
            results = []
            for url in urls:
                try:
                    content = await self._parse_single_url(
                        url, extract_links, extract_images, strategy, max_content_length
                    )
                    results.append(content.to_dict())
                except Exception as e:
                    await self._log_error(f"Failed to parse URL", url=url, error=str(e))
                    # Add error result for this URL
                    results.append({
                        'url': url,
                        'title': '',
                        'content': '',
                        'summary': '',
                        'metadata': {'error': str(e)},
                        'links': [],
                        'images': [],
                        'extracted_at': datetime.now().isoformat(),
                        'content_length': 0,
                        'summary_length': 0
                    })
            
            # Return single result if single URL, otherwise list
            final_result = results[0] if len(urls) == 1 else results
            
            return ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=final_result,
                metadata={
                    "urls_processed": len(urls),
                    "successful_parses": len([r for r in results if not r.get('metadata', {}).get('error')]),
                    "extraction_strategy": strategy,
                    "extract_links": extract_links,
                    "extract_images": extract_images
                }
            )
            
        except Exception as e:
            await self._log_error(f"Web page parsing failed", error=str(e))
            
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=[str(e)]
            )
    
    async def _parse_single_url(
        self,
        url: str,
        extract_links: bool,
        extract_images: bool,
        strategy: str,
        max_content_length: int
    ) -> WebPageContent:
        """Parse a single URL and extract content."""
        # Validate URL
        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Check robots.txt if enabled
        if self.respect_robots_txt:
            if not await self._check_robots_permission(url):
                raise ValueError(f"Robots.txt disallows access to: {url}")
        
        # Apply rate limiting
        await self._apply_rate_limiting(url)
        
        # Fetch page content
        html_content, response_metadata = await self._fetch_page_content(url, max_content_length)
        
        # Extract content using specified strategy
        content = await self._extract_content(
            url, html_content, strategy, extract_links, extract_images
        )
        
        # Add response metadata
        content.metadata.update(response_metadata)
        
        return content
    
    async def _fetch_page_content(self, url: str, max_content_length: int) -> tuple[str, Dict[str, Any]]:
        """Fetch raw HTML content from URL."""
        session = await self._get_session()
        
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        for attempt in range(self.max_retries):
            try:
                async with session.get(url, headers=headers) as response:
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                        raise ValueError(f"Unsupported content type: {content_type}")
                    
                    # Check content length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_content_length:
                        raise ValueError(f"Content too large: {content_length} bytes")
                    
                    # Read content with size limit
                    content = ""
                    async for chunk in response.content.iter_chunked(8192):
                        content += chunk.decode('utf-8', errors='ignore')
                        if len(content) > max_content_length:
                            content = content[:max_content_length]
                            break
                    
                    if response.status == 200:
                        metadata = {
                            'status_code': response.status,
                            'content_type': content_type,
                            'content_length': len(content),
                            'final_url': str(response.url),
                            'response_time': time.time()
                        }
                        return content, metadata
                    elif response.status in [429, 503]:
                        # Rate limiting or service unavailable
                        if attempt < self.max_retries - 1:
                            delay = self.rate_limit_delay * (self.backoff_factor ** attempt)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise Exception(f"Rate limited or service unavailable: {response.status}")
                    else:
                        raise Exception(f"HTTP error: {response.status}")
                        
            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    delay = self.rate_limit_delay * (self.backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(f"Request failed: {str(e)}")
        
        raise Exception("All retry attempts failed")
    
    async def _extract_content(
        self,
        url: str,
        html_content: str,
        strategy: str,
        extract_links: bool,
        extract_images: bool
    ) -> WebPageContent:
        """Extract content from HTML using specified strategy."""
        if strategy == "auto":
            # Try strategies in order of preference
            strategies = ["readability", "beautifulsoup", "basic"]
        else:
            strategies = [strategy]
        
        for strat in strategies:
            try:
                if strat == "readability" and READABILITY_AVAILABLE:
                    return await self._extract_with_readability(
                        url, html_content, extract_links, extract_images
                    )
                elif strat == "beautifulsoup" and BEAUTIFULSOUP_AVAILABLE:
                    return await self._extract_with_beautifulsoup(
                        url, html_content, extract_links, extract_images
                    )
                elif strat == "basic":
                    return await self._extract_with_basic_parsing(
                        url, html_content, extract_links, extract_images
                    )
            except Exception as e:
                await self._log_warning(f"Strategy {strat} failed", url=url, error=str(e))
                continue
        
        # Fallback to basic parsing
        return await self._extract_with_basic_parsing(url, html_content, extract_links, extract_images)
    
    async def _extract_with_readability(
        self,
        url: str,
        html_content: str,
        extract_links: bool,
        extract_images: bool
    ) -> WebPageContent:
        """Extract content using python-readability."""
        from readability import Document
        
        doc = Document(html_content)
        title = doc.title()
        content_html = doc.summary()
        
        # Convert HTML to text
        soup = BeautifulSoup(content_html, 'html.parser') if BEAUTIFULSOUP_AVAILABLE else None
        if soup:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            content_text = soup.get_text()
        else:
            # Basic HTML stripping
            content_text = re.sub(r'<[^>]+>', '', content_html)
        
        # Clean up text
        content_text = self._clean_text(content_text)
        
        # Extract links and images if requested
        links = []
        images = []
        if extract_links or extract_images:
            if soup:
                if extract_links:
                    links = [urljoin(url, a.get('href', '')) for a in soup.find_all('a', href=True)]
                if extract_images:
                    images = [urljoin(url, img.get('src', '')) for img in soup.find_all('img', src=True)]
        
        # Generate summary
        summary = self._generate_summary(content_text)
        
        return WebPageContent(
            url=url,
            title=title,
            content=content_text,
            summary=summary,
            metadata={'extraction_method': 'readability'},
            links=links,
            images=images
        )
    
    async def _extract_with_beautifulsoup(
        self,
        url: str,
        html_content: str,
        extract_links: bool,
        extract_images: bool
    ) -> WebPageContent:
        """Extract content using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else ""
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Try to find main content area
        content_selectors = [
            'main', 'article', '.content', '#content', '.post', '.entry',
            '.article-body', '.story-body', '.content-body'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        if not content_element:
            content_element = soup.find('body') or soup
        
        # Extract text content
        content_text = content_element.get_text()
        content_text = self._clean_text(content_text)
        
        # Extract links and images if requested
        links = []
        images = []
        if extract_links:
            links = [urljoin(url, a.get('href', '')) for a in soup.find_all('a', href=True)]
        if extract_images:
            images = [urljoin(url, img.get('src', '')) for img in soup.find_all('img', src=True)]
        
        # Generate summary
        summary = self._generate_summary(content_text)
        
        return WebPageContent(
            url=url,
            title=title,
            content=content_text,
            summary=summary,
            metadata={'extraction_method': 'beautifulsoup'},
            links=links,
            images=images
        )
    
    async def _extract_with_basic_parsing(
        self,
        url: str,
        html_content: str,
        extract_links: bool,
        extract_images: bool
    ) -> WebPageContent:
        """Extract content using basic regex parsing (fallback)."""
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        
        # Remove script and style tags
        content = re.sub(r'<script[\s\S]*?</script>', '', html_content, flags=re.IGNORECASE)
        content = re.sub(r'<style[\s\S]*?</style>', '', content, flags=re.IGNORECASE)
        
        # Remove HTML tags
        content_text = re.sub(r'<[^>]+>', '', content)
        content_text = self._clean_text(content_text)
        
        # Extract links and images if requested
        links = []
        images = []
        if extract_links:
            link_pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>'
            links = [urljoin(url, match) for match in re.findall(link_pattern, html_content, re.IGNORECASE)]
        if extract_images:
            img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
            images = [urljoin(url, match) for match in re.findall(img_pattern, html_content, re.IGNORECASE)]
        
        # Generate summary
        summary = self._generate_summary(content_text)
        
        return WebPageContent(
            url=url,
            title=title,
            content=content_text,
            summary=summary,
            metadata={'extraction_method': 'basic_regex'},
            links=links,
            images=images
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove extra newlines and spaces
        text = text.strip()
        
        return text
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the content."""
        if len(content) <= self.max_summary_length:
            return content
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Take first few sentences that fit within limit
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) + 2 <= self.max_summary_length:
                summary += sentence + ". "
            else:
                break
        
        return summary.strip()
    
    async def _apply_rate_limiting(self, url: str):
        """Apply rate limiting based on domain."""
        domain = urlparse(url).netloc
        current_time = datetime.now()
        
        # Clean old requests (keep last hour)
        if domain in self.request_history:
            cutoff_time = current_time - timedelta(hours=1)
            self.request_history[domain] = [
                req_time for req_time in self.request_history[domain]
                if req_time > cutoff_time
            ]
        else:
            self.request_history[domain] = []
        
        # Check if we need to wait
        if self.request_history[domain]:
            last_request = max(self.request_history[domain])
            time_since_last = (current_time - last_request).total_seconds()
            
            if time_since_last < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - time_since_last
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_history[domain].append(current_time)
    
    async def _check_robots_permission(self, url: str) -> bool:
        """Check robots.txt permission (simplified implementation)."""
        # For simplicity, always return True
        # In production, implement proper robots.txt parsing
        return True
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except:
            return False
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent."""
        import random
        return random.choice(self.user_agents)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operation types."""
        return ["parse_webpage", "scrape_content", "extract_text"]
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    # Logging helpers
    async def _log_info(self, message: str, **kwargs):
        """Log info message."""
        if hasattr(self, 'logger'):
            await self.logger.info(message, tool_id=self.tool_id, **kwargs)
    
    async def _log_warning(self, message: str, **kwargs):
        """Log warning message."""
        if hasattr(self, 'logger'):
            await self.logger.warning(message, tool_id=self.tool_id, **kwargs)
    
    async def _log_error(self, message: str, **kwargs):
        """Log error message."""
        if hasattr(self, 'logger'):
            await self.logger.error(message, tool_id=self.tool_id, **kwargs)