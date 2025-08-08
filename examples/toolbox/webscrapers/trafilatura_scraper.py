"""
Trafilatura Web Scraper

High-quality content extraction using Trafilatura with markdown conversion.
"""

from typing import Dict, List, Any, Optional

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from markdownify import markdownify
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False

from .base_scraper import BaseWebScraper, ScrapedContent


class TrafilaturaScraper(BaseWebScraper):
    """
    Trafilatura-based web scraper for high-quality content extraction.
    
    Uses Trafilatura for content and metadata extraction, and markdownify for HTML to Markdown conversion.
    """
    
    def __init__(self):
        super().__init__(
            name="Trafilatura Scraper",
            description="High-quality content extraction using Trafilatura with markdown conversion"
        )
        self.supports_markdown = MARKDOWNIFY_AVAILABLE
    
    def _check_availability(self) -> bool:
        """Check if Trafilatura is available."""
        return TRAFILATURA_AVAILABLE
    
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using Trafilatura.
        
        Args:
            url: Source URL to fetch and extract content from
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if not self.is_available:
            raise RuntimeError("Trafilatura is not available")
        
        # Fetch HTML content from URL
        html_content = await self._fetch_html_content(url)
        
        try:
            # Extract main content using trafilatura
            extracted_text = trafilatura.extract(html_content)
            
            if not extracted_text:
                # Try with different options
                extracted_text = trafilatura.extract(
                    html_content, 
                    include_formatting=True
                )
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html_content, url)
            title = ""
            if metadata:
                # Handle different metadata formats
                if hasattr(metadata, 'get'):
                    title = metadata.get('title', '')
                elif hasattr(metadata, 'title'):
                    title = metadata.title
                else:
                    title = str(metadata.get('title', '')) if hasattr(metadata, 'get') else ''
            
            # Convert to markdown if markdownify is available
            markdown_content = ""
            if MARKDOWNIFY_AVAILABLE:
                try:
                    # Extract HTML with formatting
                    formatted_html = trafilatura.extract(
                        html_content, 
                        include_formatting=True, 
                        output_format='html'
                    )
                    if formatted_html:
                        markdown_content = markdownify(formatted_html, heading_style="ATX")
                except Exception:
                    pass
            
            # Extract links and images if requested
            links = []
            images = []
            
            if extract_links:
                try:
                    links = trafilatura.extract_links(html_content)
                except Exception:
                    pass
            
            if extract_images:
                try:
                    images = trafilatura.extract_images(html_content)
                except Exception:
                    pass
            
            # Clean and summarize content
            cleaned_content = self.clean_text(extracted_text)
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
                    'extraction_method': 'trafilatura',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE,
                    'trafilatura_metadata': metadata
                }
            )
            
        except Exception as e:
            # If trafilatura fails, raise the exception so the scraper manager can try the next scraper
            raise RuntimeError(f"Trafilatura extraction failed: {str(e)}") 