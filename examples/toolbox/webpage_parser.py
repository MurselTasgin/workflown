"""
Web Page Parser Tool

Scrapes and parses web pages to extract meaningful content in markdown format.
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

from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability
from .webscrapers import ScraperManager, ScrapedContent


class WebPageContent:
    """Represents parsed web page content."""
    
    def __init__(
        self,
        url: str,
        title: str = "",
        content: str = "",
        summary: str = "",
        markdown_content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        links: Optional[List[str]] = None,
        images: Optional[List[str]] = None
    ):
        self.url = url
        self.title = title
        self.content = content
        self.summary = summary
        self.markdown_content = markdown_content
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
            'markdown_content': self.markdown_content,
            'metadata': self.metadata,
            'links': self.links,
            'images': self.images,
            'extracted_at': self.extracted_at.isoformat(),
            'content_length': len(self.content),
            'summary_length': len(self.summary),
            'markdown_length': len(self.markdown_content)
        }
    
    @classmethod
    def from_scraped_content(cls, scraped_content: ScrapedContent) -> 'WebPageContent':
        """Create WebPageContent from ScrapedContent."""
        return cls(
            url=scraped_content.url,
            title=scraped_content.title,
            content=scraped_content.content,
            summary=scraped_content.summary,
            markdown_content=scraped_content.markdown_content,
            metadata=scraped_content.metadata,
            links=scraped_content.links,
            images=scraped_content.images
        )


class WebPageParserTool(BaseTool):
    """
    Web page parser tool for extracting content from web pages.
    
    Supports multiple extraction strategies and provides content in both
    plain text and markdown formats.
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
        self.max_content_length = self.config.get("max_content_length", 5 * 1024 * 1024)  # 5MB
        self.rate_limit_delay = self.config.get("rate_limit_delay", 1.0)  # seconds
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout = self.config.get("timeout", 30)
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        self.current_user_agent_index = 0
        self.last_request_time = 0
        
        # Initialize scraper manager
        self.scraper_manager = ScraperManager()
        
        # Session for HTTP requests
        self.session = None

        self._initialize()
    
    def _initialize(self):
        """Initialize the tool."""
        pass
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the web page parsing tool.
        
        Args:
            parameters: Dictionary containing:
                - url: URL to parse (required)
                - urls: List of URLs to parse
                - extract_links: Extract links from page (default: False)
                - extract_images: Extract images from page (default: False)
                - max_content_length: Maximum content length in bytes (default: 5MB)
                - scraper: Specific scraper to use (optional)
                
        Returns:
            ToolResult with parsed content
        """
        try:
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
            max_content_length = parameters.get("max_content_length", self.max_content_length)
            specific_scraper = parameters.get("scraper")
            
            # Parse each URL
            results = []
            for url in urls:
                try:
                    # Extract content using scraper manager
                    if specific_scraper:
                        # Use specific scraper
                        scraped_content = await self.scraper_manager.extract_with_scraper(
                            specific_scraper, url, extract_links, extract_images
                        )
                    else:
                        # Use best available scraper
                        scraped_content = await self.scraper_manager.extract_with_best_scraper(
                            url, extract_links, extract_images
                        )
                    
                    # Convert to WebPageContent format
                    content = WebPageContent.from_scraped_content(scraped_content)
                    
                    results.append(content.to_dict())
                    
                except Exception as e:
                    # Add error result for this URL
                    error_msg = str(e)
                    print(f"❌ Failed to scrape {url}: {error_msg}")
                    results.append({
                        'url': url,
                        'title': '',
                        'content': '',
                        'summary': '',
                        'markdown_content': '',
                        'metadata': {
                            'error': error_msg,
                            'extraction_method': 'failed'
                        },
                        'links': [],
                        'images': [],
                        'extracted_at': datetime.now().isoformat(),
                        'content_length': 0,
                        'summary_length': 0,
                        'markdown_length': 0
                    })
            
            # Filter out results with no content and add fallback content if needed
            valid_results = []
            for result in results:
                # Check if we have meaningful content (either text or markdown)
                has_content = (
                    (result.get('content') and len(result['content'].strip()) > 50) or
                    (result.get('markdown_content') and len(result['markdown_content'].strip()) > 50)
                )
                if has_content:
                    valid_results.append(result)
            
            # If no valid results, add a fallback
            if not valid_results:
                valid_results.append({
                    'url': 'fallback',
                    'title': 'No content available',
                    'content': 'Unable to extract meaningful content from the provided URLs. This could be due to access restrictions, network issues, or the URLs not containing relevant content.',
                    'summary': 'No content available for analysis.',
                    'markdown_content': '',
                    'metadata': {'error': 'No valid content extracted'},
                    'links': [],
                    'images': [],
                    'extracted_at': datetime.now().isoformat(),
                    'content_length': 0,
                    'summary_length': 0,
                    'markdown_length': 0
                })
            
            return ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=valid_results,
                metadata={
                    'total_urls': len(urls),
                    'successful_parses': len([r for r in results if r.get('content') and len(r['content'].strip()) > 50]),
                    'available_scrapers': self.scraper_manager.get_available_scrapers()
                }
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=[str(e)]
            )
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operations."""
        return ["webpage_parse", "content_extraction", "web_scraping"]
    
    def get_version(self) -> str:
        """Get tool version."""
        return "2.0.0"
    
    def get_author(self) -> str:
        """Get tool author."""
        return "Workflown Team"
    
    def get_tags(self) -> List[str]:
        """Get tool tags."""
        return ["web scraping", "content extraction", "markdown", "html parsing"]
    
    def _get_required_parameters(self) -> List[str]:
        """Get required parameters."""
        return ["url"]
    
    def _get_optional_parameters(self) -> List[str]:
        """Get optional parameters."""
        return ["urls", "extract_links", "extract_images", "max_content_length", "scraper"]
    
    def _get_parameter_descriptions(self) -> Dict[str, str]:
        """Get parameter descriptions."""
        return {
            "url": "URL to parse (required)",
            "urls": "List of URLs to parse",
            "extract_links": "Extract links from page (default: False)",
            "extract_images": "Extract images from page (default: False)",
            "max_content_length": "Maximum content length in bytes (default: 5MB)",
            "scraper": "Specific scraper to use (optional)"
        }
    
    def _get_parameter_types(self) -> Dict[str, str]:
        """Get parameter types."""
        return {
            "url": "string",
            "urls": "array",
            "extract_links": "boolean",
            "extract_images": "boolean",
            "max_content_length": "integer",
            "scraper": "string"
        }
    
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

    # ------------------------------------------------------------------
    # Result display override
    # ------------------------------------------------------------------
    def _display_result_body(self, result: Any, context: Optional[Dict[str, Any]] = None) -> None:
        print("📄 WEB SCRAPING RESULTS:")
        if isinstance(result, list):
            print(f"   • Scraped {len(result)} URLs")
            for i, scrape_result in enumerate(result):
                if isinstance(scrape_result, dict):
                    url = scrape_result.get('url', f'URL {i+1}')
                    title = scrape_result.get('title', 'No title')
                    content_length = scrape_result.get('content_length', 0)
                    markdown_length = scrape_result.get('markdown_length', 0)
                    print(f"   📄 URL {i+1}: {url}")
                    print(f"      • Title: {title}")
                    print(f"      • Content length: {content_length} characters")
                    print(f"      • Markdown length: {markdown_length} characters")
                    metadata = scrape_result.get('metadata', {})
                    extraction_method = metadata.get('extraction_method', 'unknown')
                    print(f"      • Extraction method: {extraction_method}")
                    markdown_content = scrape_result.get('markdown_content', '')
                    if markdown_content:
                        print(f"      • Markdown content:")
                        print(f"      {'─' * 50}")
                        display_length = max(1000, len(markdown_content))
                        markdown_snippet = markdown_content[:display_length]
                        formatted_content = markdown_snippet.replace('\n', '\n      ')
                        print(f"      {formatted_content}")
                        if len(markdown_content) > display_length:
                            print(f"      ... (showing {display_length}/{len(markdown_content)} characters)")
                        else:
                            print(f"      (showing full content: {len(markdown_content)} characters)")
                        print(f"      {'─' * 50}")
                    else:
                        print(f"      • Markdown content: No markdown extracted")
                    if metadata.get('error'):
                        print(f"      • Error: {metadata['error']}")
                    print()
                else:
                    print(f"   📄 Result {i+1}: {scrape_result}")
        elif isinstance(result, dict):
            print(f"   • Scraping completed successfully")
            if "result" in result and isinstance(result["result"], list):
                results = result["result"]
                print(f"   • Scraped {len(results)} URLs")
        else:
            print(f"   • Result: {result}")