"""
Web Crawler Module

A comprehensive module for visiting URLs, extracting HTML content, and optionally following links
with configurable limits. Supports various crawling strategies and rate limiting.
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re
from enum import Enum
import random
from contextlib import asynccontextmanager
from typing import Tuple

# Optional browser engines
try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover
    _PLAYWRIGHT_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    _SELENIUM_AVAILABLE = True
except Exception:  # pragma: no cover
    _SELENIUM_AVAILABLE = False


class CrawlStrategy(Enum):
    """Crawling strategies."""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    PRIORITY_BASED = "priority_based"


@dataclass
class CrawlConfig:
    """Configuration for web crawling."""
    max_pages: int = 10
    max_depth: int = 3
    max_concurrent_requests: int = 5
    request_delay: float = 1.0  # seconds between requests
    timeout: int = 30
    follow_links: bool = False
    allowed_domains: Optional[List[str]] = None
    excluded_domains: Optional[List[str]] = None
    excluded_paths: Optional[List[str]] = None
    user_agents: Optional[List[str]] = None
    strategy: CrawlStrategy = CrawlStrategy.BREADTH_FIRST
    respect_robots_txt: bool = True
    max_content_length: int = 10 * 1024 * 1024  # 10MB
    max_retries: int = 3
    retry_backoff_base: float = 0.8
    # Browser fallback options
    enable_browser_fallback: bool = True
    browser_engine: str = "playwright"  # or "selenium"
    browser_type: str = "chromium"  # chromium|firefox|webkit (playwright), chrome|firefox (selenium)
    headless_browser: bool = True
    browser_max_wait_ms: int = 15000
    browser_wait_until: str = "networkidle"  # load|domcontentloaded|networkidle (playwright)
    min_html_length_for_success: int = 300


@dataclass
class CrawledPage:
    """Represents a crawled web page."""
    url: str
    title: str = ""
    html_content: str = ""
    status_code: int = 0
    content_type: str = ""
    content_length: int = 0
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    crawled_at: datetime = field(default_factory=datetime.now)
    depth: int = 0
    parent_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CrawlResult:
    """Result of a web crawling operation."""
    pages: List[CrawledPage] = field(default_factory=list)
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    total_links_found: int = 0
    total_images_found: int = 0
    crawl_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    config: CrawlConfig = field(default_factory=CrawlConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'pages': [page.__dict__ for page in self.pages],
            'total_pages': self.total_pages,
            'successful_pages': self.successful_pages,
            'failed_pages': self.failed_pages,
            'total_links_found': self.total_links_found,
            'total_images_found': self.total_images_found,
            'crawl_time': self.crawl_time,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'config': self.config.__dict__
        }


class WebCrawler:
    """
    Comprehensive web crawler for visiting URLs and extracting HTML content.
    
    Supports various crawling strategies, rate limiting, and configurable limits.
    """
    
    def __init__(self, config: Optional[CrawlConfig] = None):
        """
        Initialize the web crawler.
        
        Args:
            config: Crawling configuration
        """
        self.config = config or CrawlConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.visited_urls: Set[str] = set()
        self.url_queue: List[tuple[str, int]] = []  # (url, depth)
        self.semaphore: Optional[asyncio.Semaphore] = None
        
        # Default user agents
        if not self.config.user_agents:
            self.config.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def _initialize(self):
        """Initialize the crawler."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _is_allowed_url(self, url: str) -> bool:
        """
        Check if URL is allowed based on configuration.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is allowed
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        # Check excluded domains
        if self.config.excluded_domains:
            for excluded in self.config.excluded_domains:
                if domain.endswith(excluded.lower()):
                    return False
        
        # Check allowed domains
        if self.config.allowed_domains:
            allowed = False
            for allowed_domain in self.config.allowed_domains:
                if domain.endswith(allowed_domain.lower()):
                    allowed = True
                    break
            if not allowed:
                return False
        
        # Check excluded paths
        if self.config.excluded_paths:
            for excluded_path in self.config.excluded_paths:
                if path.startswith(excluded_path.lower()):
                    return False
        
        return True
    
    def _extract_links_and_images(self, html_content: str, base_url: str) -> tuple[List[str], List[str]]:
        """
        Extract links and images from HTML content.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links
            
        Returns:
            Tuple of (links, images)
        """
        links = []
        images = []
        
        # Extract links
        link_pattern = r'href=["\']([^"\']+)["\']'
        for match in re.finditer(link_pattern, html_content, re.IGNORECASE):
            link = match.group(1)
            if link.startswith(('http://', 'https://')):
                links.append(link)
            elif link.startswith('/'):
                links.append(urljoin(base_url, link))
            elif not link.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                links.append(urljoin(base_url, link))
        
        # Extract images
        img_pattern = r'src=["\']([^"\']+)["\']'
        for match in re.finditer(img_pattern, html_content, re.IGNORECASE):
            img_src = match.group(1)
            if img_src.startswith(('http://', 'https://')):
                images.append(img_src)
            elif img_src.startswith('/'):
                images.append(urljoin(base_url, img_src))
            else:
                images.append(urljoin(base_url, img_src))
        
        return links, images
    
    def _extract_title(self, html_content: str) -> str:
        """
        Extract title from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            Page title
        """
        title_pattern = r'<title[^>]*>([^<]+)</title>'
        match = re.search(title_pattern, html_content, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _build_browser_like_headers(self, url: str, user_agent: str, referer: Optional[str] = None) -> Dict[str, str]:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        # Some servers require a referer to not block
        if referer:
            headers['Referer'] = referer
        else:
            headers['Referer'] = 'https://www.google.com/'
        # Hints
        headers['sec-ch-ua'] = '"Chromium";v="127", "Not=A?Brand";v="24", "Google Chrome";v="127"'
        headers['sec-ch-ua-mobile'] = '?0'
        headers['sec-ch-ua-platform'] = '"macOS"'
        return headers

    async def _fetch_page(self, url: str, depth: int = 0) -> CrawledPage:
        """
        Fetch a single page.
        
        Args:
            url: URL to fetch
            depth: Current depth
            
        Returns:
            CrawledPage object
        """
        async with self.semaphore:
            # Rate limiting
            if self.config.request_delay > 0:
                # add small jitter to avoid patterns
                await asyncio.sleep(self.config.request_delay * (0.5 + random.random()))

            # Retry loop with header/UA variations
            attempts = max(1, self.config.max_retries)
            last_error: Optional[str] = None
            for attempt in range(attempts):
                # Rotate user agent per attempt and url
                ua_index = (hash(url) + attempt + random.randint(0, 1000)) % len(self.config.user_agents)
                user_agent = self.config.user_agents[ua_index]
                headers = self._build_browser_like_headers(url, user_agent)

                try:
                    async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                        if response.status == 200:
                            content = await response.text()

                            # Check content length
                            if len(content.encode('utf-8')) > self.config.max_content_length:
                                content = content[:self.config.max_content_length]

                            # Extract title, links, and images
                            title = self._extract_title(content)
                            links, images = self._extract_links_and_images(content, url)

                            # If content appears too short, try browser fallback
                            if len(content) < self.config.min_html_length_for_success and self.config.enable_browser_fallback:
                                browser_page = await self._fetch_with_browser(url, user_agent)
                                if browser_page is not None and browser_page.html_content and len(browser_page.html_content) >= self.config.min_html_length_for_success:
                                    return browser_page

                            return CrawledPage(
                                url=url,
                                title=title,
                                html_content=content,
                                status_code=response.status,
                                content_type=response.headers.get('content-type', ''),
                                content_length=len(content),
                                links=links,
                                images=images,
                                depth=depth,
                                metadata={
                                    'user_agent': user_agent,
                                    'response_headers': dict(response.headers)
                                }
                            )

                        # For 403/429/503, retry with backoff and different headers
                        if response.status in (403, 429, 503):
                            last_error = f"HTTP {response.status}: {response.reason}"
                            # Backoff with jitter
                            backoff = (self.config.retry_backoff_base ** attempt) + random.random()
                            await asyncio.sleep(backoff)
                            continue

                        # 404 or other client errors: no retry
                        return CrawledPage(
                            url=url,
                            status_code=response.status,
                            depth=depth,
                            error=f"HTTP {response.status}: {response.reason}"
                        )

                except Exception as e:
                    last_error = str(e)
                    # Backoff before next attempt
                    backoff = (self.config.retry_backoff_base ** attempt) + random.random()
                    await asyncio.sleep(backoff)
                    continue

            # All attempts failed; if 403/429/503 or unknown error and browser fallback is enabled, try browser
            if self.config.enable_browser_fallback:
                ua_index = (hash(url) + random.randint(0, 1000)) % len(self.config.user_agents)
                user_agent = self.config.user_agents[ua_index]
                browser_page = await self._fetch_with_browser(url, user_agent)
                if browser_page is not None:
                    return browser_page

            # If all attempts failed and no browser fallback or it failed
            return CrawledPage(
                url=url,
                depth=depth,
                error=last_error or "Failed to fetch page after retries"
            )

    async def _fetch_with_browser(self, url: str, user_agent: str) -> Optional[CrawledPage]:
        """
        Fetch page using a headless browser (Playwright preferred, Selenium fallback).
        Returns CrawledPage or None if browser engine not available or failed.
        """
        # Choose engine
        engine = self.config.browser_engine.lower() if self.config.browser_engine else "playwright"
        if engine == "playwright" and _PLAYWRIGHT_AVAILABLE:
            try:
                return await self._fetch_with_playwright(url, user_agent)
            except Exception as _e:
                # Fallback to selenium if available
                if _SELENIUM_AVAILABLE:
                    try:
                        return await self._fetch_with_selenium(url, user_agent)
                    except Exception:
                        return None
                return None
        elif engine == "selenium" and _SELENIUM_AVAILABLE:
            try:
                return await self._fetch_with_selenium(url, user_agent)
            except Exception:
                # Try playwright as a last resort
                if _PLAYWRIGHT_AVAILABLE:
                    try:
                        return await self._fetch_with_playwright(url, user_agent)
                    except Exception:
                        return None
                return None
        else:
            # Try whatever is available
            if _PLAYWRIGHT_AVAILABLE:
                try:
                    return await self._fetch_with_playwright(url, user_agent)
                except Exception:
                    pass
            if _SELENIUM_AVAILABLE:
                try:
                    return await self._fetch_with_selenium(url, user_agent)
                except Exception:
                    pass
            return None

    async def _fetch_with_playwright(self, url: str, user_agent: str) -> Optional[CrawledPage]:
        wait_until = self.config.browser_wait_until
        if wait_until not in ("load", "domcontentloaded", "networkidle"):
            wait_until = "networkidle"
        try:
            async with async_playwright() as p:
                browser_type = self.config.browser_type or "chromium"
                browser_launcher = getattr(p, browser_type, p.chromium)
                browser = await browser_launcher.launch(headless=self.config.headless_browser)
                context = await browser.new_context(user_agent=user_agent, java_script_enabled=True)
                page = await context.new_page()
                response = await page.goto(url, wait_until=wait_until, timeout=self.config.browser_max_wait_ms)
                content = await page.content()
                title = await page.title()
                await context.close()
                await browser.close()

                if not content:
                    return None

                # Trim content length if needed
                if len(content.encode('utf-8')) > self.config.max_content_length:
                    content = content[:self.config.max_content_length]

                links, images = self._extract_links_and_images(content, url)
                return CrawledPage(
                    url=url,
                    title=title or self._extract_title(content),
                    html_content=content,
                    status_code=(response.status if response else 200),
                    content_type=response.headers.get('content-type', '') if response else '',
                    content_length=len(content),
                    links=links,
                    images=images,
                    depth=0,
                    metadata={'fallback_engine': 'playwright', 'user_agent': user_agent}
                )
        except Exception:
            return None

    async def _fetch_with_selenium(self, url: str, user_agent: str) -> Optional[CrawledPage]:
        # Run blocking selenium in a thread
        def _selenium_get() -> Optional[Tuple[str, str]]:
            try:
                btype = (self.config.browser_type or "chrome").lower()
                headless = self.config.headless_browser
                if btype in ("chrome", "chromium"):
                    opts = ChromeOptions()
                    if headless:
                        opts.add_argument("--headless=new")
                    opts.add_argument(f"--user-agent={user_agent}")
                    opts.add_argument("--disable-gpu")
                    opts.add_argument("--no-sandbox")
                    driver = webdriver.Chrome(options=opts)
                else:
                    opts = FirefoxOptions()
                    if headless:
                        opts.add_argument("-headless")
                    profile = None
                    driver = webdriver.Firefox(options=opts)
                    # Firefox UA override sometimes requires prefs; skipping for brevity
                driver.set_page_load_timeout(self.config.browser_max_wait_ms / 1000)
                driver.get(url)
                html = driver.page_source
                title = driver.title
                driver.quit()
                return (html, title)
            except Exception:
                try:
                    driver.quit()
                except Exception:
                    pass
                return None

        try:
            result = await asyncio.to_thread(_selenium_get)
            if not result:
                return None
            html, title = result
            if not html:
                return None
            if len(html.encode('utf-8')) > self.config.max_content_length:
                html = html[:self.config.max_content_length]
            links, images = self._extract_links_and_images(html, url)
            return CrawledPage(
                url=url,
                title=title or self._extract_title(html),
                html_content=html,
                status_code=200,
                content_type='',
                content_length=len(html),
                links=links,
                images=images,
                depth=0,
                metadata={'fallback_engine': 'selenium', 'user_agent': user_agent}
            )
        except Exception:
            return None
    
    async def crawl_single_page(self, url: str) -> CrawledPage:
        """
        Crawl a single page.
        
        Args:
            url: URL to crawl
            
        Returns:
            CrawledPage object
        """
        if not self.session:
            await self._initialize()
        
        return await self._fetch_page(url)
    
    async def crawl_multiple_pages(
        self, 
        start_urls: List[str], 
        follow_links: bool = False
    ) -> CrawlResult:
        """
        Crawl multiple pages with optional link following.
        
        Args:
            start_urls: List of starting URLs
            follow_links: Whether to follow links found on pages
            
        Returns:
            CrawlResult object
        """
        if not self.session:
            await self._initialize()
        
        start_time = datetime.now()
        result = CrawlResult(config=self.config, start_time=start_time)
        
        # Initialize queue with start URLs
        self.url_queue = [(url, 0) for url in start_urls]
        self.visited_urls.clear()
        
        # Crawl pages
        tasks = []
        while self.url_queue and len(result.pages) < self.config.max_pages:
            if self.config.strategy == CrawlStrategy.BREADTH_FIRST:
                # Process all URLs at current depth
                current_depth = self.url_queue[0][1]
                current_batch = []
                while self.url_queue and self.url_queue[0][1] == current_depth:
                    url, depth = self.url_queue.pop(0)
                    if url not in self.visited_urls and self._is_allowed_url(url):
                        current_batch.append((url, depth))
                        self.visited_urls.add(url)
                
                # Create tasks for current batch
                for url, depth in current_batch:
                    task = self._crawl_page_with_links(url, depth, result)
                    tasks.append(task)
                
                # Wait for current batch to complete
                if tasks:
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    tasks.clear()
                    
                    # Process results and add new URLs to queue
                    for page_result in batch_results:
                        if isinstance(page_result, CrawledPage):
                            result.pages.append(page_result)
                            if page_result.error:
                                result.failed_pages += 1
                            else:
                                result.successful_pages += 1
                                result.total_links_found += len(page_result.links)
                                result.total_images_found += len(page_result.images)
                                
                                # Add new URLs to queue if following links
                                if follow_links and page_result.links:
                                    for link in page_result.links:
                                        if (link not in self.visited_urls and 
                                            self._is_allowed_url(link) and
                                            page_result.depth < self.config.max_depth):
                                            self.url_queue.append((link, page_result.depth + 1))
            
            elif self.config.strategy == CrawlStrategy.DEPTH_FIRST:
                # Process one URL at a time
                if self.url_queue:
                    url, depth = self.url_queue.pop(0)
                    if url not in self.visited_urls and self._is_allowed_url(url):
                        self.visited_urls.add(url)
                        page_result = await self._crawl_page_with_links(url, depth, result)
                        result.pages.append(page_result)
                        
                        if page_result.error:
                            result.failed_pages += 1
                        else:
                            result.successful_pages += 1
                            result.total_links_found += len(page_result.links)
                            result.total_images_found += len(page_result.images)
                            
                            # Add new URLs to queue if following links
                            if follow_links and page_result.links:
                                for link in page_result.links:
                                    if (link not in self.visited_urls and 
                                        self._is_allowed_url(link) and
                                        page_result.depth < self.config.max_depth):
                                        self.url_queue.append((link, page_result.depth + 1))
        
        result.total_pages = len(result.pages)
        result.end_time = datetime.now()
        result.crawl_time = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _crawl_page_with_links(self, url: str, depth: int, result: CrawlResult) -> CrawledPage:
        """
        Crawl a single page and update result statistics.
        
        Args:
            url: URL to crawl
            depth: Current depth
            result: CrawlResult to update
            
        Returns:
            CrawledPage object
        """
        page = await self._fetch_page(url, depth)
        return page


# Convenience functions
async def crawl_url(url: str, config: Optional[CrawlConfig] = None) -> CrawledPage:
    """
    Crawl a single URL.
    
    Args:
        url: URL to crawl
        config: Optional configuration
        
    Returns:
        CrawledPage object
    """
    async with WebCrawler(config) as crawler:
        return await crawler.crawl_single_page(url)


async def crawl_urls(
    urls: List[str], 
    follow_links: bool = False,
    config: Optional[CrawlConfig] = None
) -> CrawlResult:
    """
    Crawl multiple URLs with optional link following.
    
    Args:
        urls: List of URLs to crawl
        follow_links: Whether to follow links
        config: Optional configuration
        
    Returns:
        CrawlResult object
    """
    async with WebCrawler(config) as crawler:
        return await crawler.crawl_multiple_pages(urls, follow_links) 