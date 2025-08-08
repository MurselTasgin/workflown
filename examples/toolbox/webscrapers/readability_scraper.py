"""
Readability Web Scraper

Content extraction using Readability with markdown conversion.
"""

from typing import Dict, List, Any, Optional

try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

try:
    from markdownify import markdownify
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False

from .base_scraper import BaseWebScraper, ScrapedContent


class ReadabilityScraper(BaseWebScraper):
    """
    Readability-based web scraper for content extraction.
    
    Uses Readability for content extraction and markdownify for HTML to Markdown conversion.
    """
    
    def __init__(self):
        super().__init__(
            name="Readability Scraper",
            description="Content extraction using Readability with markdown conversion"
        )
        self.supports_markdown = MARKDOWNIFY_AVAILABLE
    
    def _check_availability(self) -> bool:
        """Check if Readability is available."""
        return READABILITY_AVAILABLE
    
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using Readability.
        
        Args:
            url: Source URL to fetch and extract content from
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if not self.is_available:
            raise RuntimeError("Readability is not available")
        
        # Fetch HTML content from URL
        html_content = await self._fetch_html_content(url)
        
        try:
            # Check if HTML content is empty or too short
            if not html_content or len(html_content.strip()) < 100:
                return ScrapedContent(
                    url=url,
                    title="",
                    content="",
                    markdown_content="",
                    summary="",
                    links=[],
                    images=[],
                    metadata={
                        'extraction_method': 'readability',
                        'error': 'Empty or insufficient HTML content',
                        'supports_markdown': MARKDOWNIFY_AVAILABLE
                    }
                )
            
            # Extract content using readability
            doc = Document(html_content)
            content_html = doc.summary()  # This returns HTML
            title = doc.title()
            
            # Convert HTML content to plain text using BeautifulSoup
            content = ""
            if content_html and BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(content_html, 'html.parser')
                content = soup.get_text()
            else:
                content = content_html or ""
            
            # Convert to markdown if markdownify is available
            markdown_content = ""
            if MARKDOWNIFY_AVAILABLE and content_html:
                try:
                    markdown_content = markdownify(content_html, heading_style="ATX")
                except Exception:
                    pass
            
            # Extract links and images
            links = []
            images = []
            
            if extract_links and BEAUTIFULSOUP_AVAILABLE:
                try:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        if href and href.startswith(('http', 'https')):
                            links.append(href)
                except Exception:
                    pass
            
            if extract_images and BEAUTIFULSOUP_AVAILABLE:
                try:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    for img in soup.find_all('img', src=True):
                        src = img.get('src')
                        if src and src.startswith(('http', 'https')):
                            images.append(src)
                except Exception:
                    pass
            
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
                    'extraction_method': 'readability',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE
                }
            )
            
        except Exception as e:
            # Return a structured error result instead of raising
            return ScrapedContent(
                url=url,
                title="",
                content="",
                markdown_content="",
                summary="",
                links=[],
                images=[],
                metadata={
                    'extraction_method': 'readability',
                    'error': f'Readability extraction failed: {str(e)}',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE
                }
            ) 