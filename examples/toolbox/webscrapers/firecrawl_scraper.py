"""
Firecrawl Web Scraper

High-quality content extraction using Firecrawl library with API key support.
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional

try:
    from firecrawl import Firecrawl
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False

try:
    from markdownify import markdownify
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False

from .base_scraper import BaseWebScraper, ScrapedContent


class FirecrawlScraper(BaseWebScraper):
    """
    Firecrawl-based web scraper for high-quality content extraction.
    
    Uses Firecrawl API for content extraction and markdownify for HTML to Markdown conversion.
    """
    
    def __init__(self, api_key: str = None):
        super().__init__(
            name="Firecrawl Scraper",
            description="High-quality content extraction using Firecrawl API with markdown conversion"
        )
        self.supports_markdown = MARKDOWNIFY_AVAILABLE
        self.api_key = api_key
        self.firecrawl_client = None
        
        if self.api_key and FIRECRAWL_AVAILABLE:
            try:
                self.firecrawl_client = Firecrawl(api_key=self.api_key)
            except Exception:
                self.firecrawl_client = None
    
    def _check_availability(self) -> bool:
        """Check if Firecrawl is available and API key is provided."""
        return FIRECRAWL_AVAILABLE and self.api_key and self.firecrawl_client is not None
    
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using Firecrawl.
        
        Args:
            url: Source URL to scrape
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if not self.is_available:
            raise RuntimeError("Firecrawl is not available or API key is invalid")
        
        if not url:
            raise ValueError("URL is required for Firecrawl scraper")
        
        try:
            # Use Firecrawl API to scrape the URL directly
            scrape_result = await self.firecrawl_client.scrape_url(
                url=url,
                page_options={
                    "onlyMainContent": True,
                    "includeHtml": True,
                    "includeMarkdown": True,
                    "includeImages": extract_images,
                    "includeLinks": extract_links
                }
            )
            
            # Extract content from the result
            content = scrape_result.get('markdown', '') or scrape_result.get('text', '')
            title = scrape_result.get('title', '')
            html_content = scrape_result.get('html', '')
            
            # Convert to markdown if markdownify is available and we have HTML
            markdown_content = ""
            if MARKDOWNIFY_AVAILABLE and html_content:
                try:
                    markdown_content = markdownify(html_content, heading_style="ATX")
                except Exception:
                    pass
            
            # If no markdown from API, use the content as markdown
            if not markdown_content and content:
                markdown_content = content
            
            # Extract links and images
            links = []
            images = []
            
            if extract_links:
                links = scrape_result.get('links', [])
            
            if extract_images:
                images = scrape_result.get('images', [])
            
            # Clean and summarize content
            cleaned_content = self.clean_text(content)
            summary = self.generate_summary(cleaned_content)
            
            return ScrapedContent(
                url=url,
                title=title,
                content=cleaned_content,
                markdown_content=markdown_content,
                summary=summary,
                links=links,
                images=images,
                metadata={
                    'extraction_method': 'firecrawl',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE,
                    'firecrawl_result': {
                        'status': scrape_result.get('status', 'unknown'),
                        'timestamp': scrape_result.get('timestamp', ''),
                        'url': scrape_result.get('url', url)
                    }
                }
            )
            
        except Exception as e:
            # If Firecrawl fails, raise the exception so the scraper manager can try the next scraper
            raise RuntimeError(f"Firecrawl extraction failed: {str(e)}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get scraper capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            'api_required': True,
            'api_key_configured': bool(self.api_key),
            'client_initialized': self.firecrawl_client is not None
        })
        return capabilities 