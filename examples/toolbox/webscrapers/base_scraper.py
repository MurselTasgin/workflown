"""
Base Web Scraper

Abstract base class for web scrapers with common functionality.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .web_crawler import WebCrawler, CrawlConfig, CrawledPage


@dataclass
class ScrapedContent:
    """Represents scraped content from a web page."""
    
    url: str
    title: str = ""
    content: str = ""
    markdown_content: str = ""
    summary: str = ""
    links: List[str] = None
    images: List[str] = None
    metadata: Dict[str, Any] = None
    extracted_at: datetime = None
    
    def __post_init__(self):
        if self.links is None:
            self.links = []
        if self.images is None:
            self.images = []
        if self.metadata is None:
            self.metadata = {}
        if self.extracted_at is None:
            self.extracted_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'markdown_content': self.markdown_content,
            'summary': self.summary,
            'links': self.links,
            'images': self.images,
            'metadata': self.metadata,
            'extracted_at': self.extracted_at.isoformat(),
            'content_length': len(self.content),
            'markdown_length': len(self.markdown_content),
            'summary_length': len(self.summary)
        }


class BaseWebScraper(ABC):
    """
    Abstract base class for web scrapers.
    
    All web scraper implementations must inherit from this class and implement
    the required methods for content extraction.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize the web scraper.
        
        Args:
            name: Name of the scraper
            description: Description of the scraper's capabilities
        """
        self.name = name
        self.description = description
        self.is_available = self._check_availability()
        self.crawler: Optional[WebCrawler] = None
    
    @abstractmethod
    def _check_availability(self) -> bool:
        """
        Check if the required dependencies are available.
        
        Returns:
            True if the scraper can be used, False otherwise
        """
        pass
    
    async def _fetch_html_content(self, url: str, timeout: int = 30) -> str:
        """
        Fetch HTML content from a URL using the web crawler.
        
        Args:
            url: URL to fetch content from
            timeout: Request timeout in seconds
            
        Returns:
            HTML content as string
        """
        if not self.crawler:
            config = CrawlConfig(timeout=timeout)
            self.crawler = WebCrawler(config)
            await self.crawler._initialize()
        
        try:
            crawled_page = await self.crawler.crawl_single_page(url)
            if crawled_page.error:
                raise RuntimeError(f"Failed to fetch content from {url}: {crawled_page.error}")
            return crawled_page.html_content
        except Exception as e:
            raise RuntimeError(f"Failed to fetch content from {url}: {str(e)}")
    
    @abstractmethod
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content from a URL.
        
        Args:
            url: Source URL to fetch and extract content from
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        pass
    
    async def cleanup(self):
        """Clean up resources."""
        if self.crawler:
            await self.crawler.cleanup()
            self.crawler = None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get scraper capabilities.
        
        Returns:
            Dictionary describing the scraper's capabilities
        """
        return {
            'name': self.name,
            'description': self.description,
            'available': self.is_available,
            'supports_markdown': hasattr(self, 'supports_markdown') and self.supports_markdown,
            'supports_links': True,
            'supports_images': True,
            'supports_metadata': True
        }
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common HTML artifacts
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        return text.strip()
    
    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        Generate a summary of the content.
        
        Args:
            content: Full content text
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        if not content:
            return ""
        
        # Simple summary: take first few sentences
        sentences = content.split('.')
        summary = ""
        
        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + "."
            else:
                break
        
        return summary.strip() or content[:max_length].strip() 