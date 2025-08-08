"""
Scraper Manager

Manages multiple web scrapers and selects the best one for content extraction.
"""

from typing import Dict, List, Any, Optional
from .base_scraper import BaseWebScraper, ScrapedContent
from .beautifulsoup_scraper import BeautifulSoupScraper
from .trafilatura_scraper import TrafilaturaScraper
from .newspaper3k_scraper import Newspaper3kScraper
from .readability_scraper import ReadabilityScraper
from .langchain_scraper import LangChainScraper
from .llamaindex_scraper import LlamaIndexScraper
from .firecrawl_scraper import FirecrawlScraper

# Import config to get API keys
try:
    from workflown.core.config.central_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class ScraperManager:
    """
    Manages multiple web scrapers and provides intelligent selection.
    """
    
    def __init__(self):
        """Initialize the scraper manager with all available scrapers."""
        self.scrapers = {}
        self._initialize_scrapers()
    
    def _initialize_scrapers(self):
        """Initialize all available scrapers."""
        # Get API keys from config
        firecrawl_api_key = None
        if CONFIG_AVAILABLE:
            try:
                config = get_config()
                firecrawl_api_key = config.get("api.firecrawl.api_key", "")
            except Exception:
                pass
        
        scraper_classes = [
            (FirecrawlScraper, {"api_key": firecrawl_api_key}),
            (TrafilaturaScraper, {}),
            (Newspaper3kScraper, {}),
            (ReadabilityScraper, {}),
            (BeautifulSoupScraper, {}),
            (LangChainScraper, {}),
            (LlamaIndexScraper, {})
        ]
        
        for scraper_class, kwargs in scraper_classes:
            scraper = scraper_class(**kwargs)
            if scraper.is_available:
                self.scrapers[scraper.name] = scraper
    
    def get_available_scrapers(self) -> List[str]:
        """Get list of available scraper names."""
        return list(self.scrapers.keys())
    
    def get_scraper(self, name: str) -> Optional[BaseWebScraper]:
        """Get a specific scraper by name."""
        return self.scrapers.get(name)
    
    def get_scraper_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get capabilities of all available scrapers."""
        capabilities = {}
        for name, scraper in self.scrapers.items():
            capabilities[name] = scraper.get_capabilities()
        return capabilities
    
    async def extract_with_scraper(
        self,
        scraper_name: str,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using a specific scraper.
        
        Args:
            scraper_name: Name of the scraper to use
            url: Source URL
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if scraper_name not in self.scrapers:
            raise ValueError(f"Scraper '{scraper_name}' not found")
        
        scraper = self.scrapers[scraper_name]
        return await scraper.extract_content(url, extract_links, extract_images)
    
    async def extract_with_best_scraper(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False,
        preferred_scrapers: List[str] = None
    ) -> ScrapedContent:
        """
        Extract content using the best available scraper.
        
        Args:
            url: Source URL
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            preferred_scrapers: List of preferred scraper names in order
            
        Returns:
            ScrapedContent object with extracted information
        """
        if preferred_scrapers is None:
            # Default preference order based on quality and reliability
            preferred_scrapers = [
                "Firecrawl Scraper",
                "Trafilatura Scraper",
                "Newspaper3k Scraper", 
                "Readability Scraper",
                "BeautifulSoup Scraper",
                "LangChain Scraper",
                "LlamaIndex Scraper"
            ]
        
        # Try preferred scrapers in order
        for scraper_name in preferred_scrapers:
            if scraper_name in self.scrapers:
                try:
                    result = await self.extract_with_scraper(
                        scraper_name, url, extract_links, extract_images
                    )
                    # Check if we got meaningful content (either text or markdown)
                    has_content = (
                        (result.content and len(result.content.strip()) > 50) or
                        (result.markdown_content and len(result.markdown_content.strip()) > 50)
                    )
                    if has_content:
                        return result
                except Exception as e:
                    # Log the error but continue with next scraper
                    print(f"⚠️  {scraper_name} failed for {url}: {str(e)}")
                    continue
        
        # If no preferred scrapers worked, try any available scraper
        for scraper_name, scraper in self.scrapers.items():
            if scraper_name not in preferred_scrapers:  # Only try scrapers not in preferred list
                try:
                    result = await scraper.extract_content(
                        url, extract_links, extract_images
                    )
                    # Check if we got meaningful content (either text or markdown)
                    has_content = (
                        (result.content and len(result.content.strip()) > 50) or
                        (result.markdown_content and len(result.markdown_content.strip()) > 50)
                    )
                    if has_content:
                        return result
                except Exception as e:
                    # Log the error but continue with next scraper
                    print(f"⚠️  {scraper_name} failed for {url}: {str(e)}")
                    continue
        
        # If all scrapers failed, return empty result
        return ScrapedContent(
            url=url,
            title="",
            content="",
            markdown_content="",
            summary="",
            links=[],
            images=[],
            metadata={
                'extraction_method': 'none',
                'error': 'All scrapers failed'
            }
        )
    
    async def extract_with_all_scrapers(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> Dict[str, ScrapedContent]:
        """
        Extract content using all available scrapers.
        
        Args:
            url: Source URL
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            Dictionary mapping scraper names to ScrapedContent objects
        """
        results = {}
        
        for scraper_name, scraper in self.scrapers.items():
            try:
                result = await scraper.extract_content(
                    url, extract_links, extract_images
                )
                results[scraper_name] = result
            except Exception as e:
                # Add error result for this scraper
                results[scraper_name] = ScrapedContent(
                    url=url,
                    title="",
                    content="",
                    markdown_content="",
                    summary="",
                    links=[],
                    images=[],
                    metadata={
                        'extraction_method': scraper_name,
                        'error': str(e)
                    }
                )
        
        return results 