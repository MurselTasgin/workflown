"""
BeautifulSoup Web Scraper

Vanilla HTML parsing using BeautifulSoup with markdown conversion.
"""

from typing import Dict, List, Any, Optional

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


class BeautifulSoupScraper(BaseWebScraper):
    """
    BeautifulSoup-based web scraper for HTML parsing.
    
    Uses BeautifulSoup for HTML parsing and markdownify for HTML to Markdown conversion.
    """
    
    def __init__(self):
        super().__init__(
            name="BeautifulSoup Scraper",
            description="Vanilla HTML parsing using BeautifulSoup with markdown conversion"
        )
        self.supports_markdown = MARKDOWNIFY_AVAILABLE
    
    def _check_availability(self) -> bool:
        """Check if BeautifulSoup is available."""
        return BEAUTIFULSOUP_AVAILABLE
    
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using BeautifulSoup.
        
        Args:
            url: Source URL to fetch and extract content from
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if not self.is_available:
            raise RuntimeError("BeautifulSoup is not available")
        
        # Fetch HTML content from URL
        html_content = await self._fetch_html_content(url)
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extract main content
            content = ""
            main_selectors = [
                'main', 'article', '[role="main"]', '.content', '.post-content',
                '.entry-content', '.article-content', '.main-content', '.post-body',
                '.article-body', '.content-body', '.text-content'
            ]
            
            for selector in main_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    content = main_content.get_text()
                    break
            
            # If no main content found, try body but exclude navigation and footer
            if not content:
                body = soup.find('body')
                if body:
                    # Remove navigation, footer, and other non-content elements
                    for element in body.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                        element.decompose()
                    content = body.get_text()
            
            # Convert to markdown if markdownify is available
            markdown_content = ""
            if MARKDOWNIFY_AVAILABLE:
                try:
                    # Try to get the main content HTML for better markdown conversion
                    main_html = ""
                    for selector in main_selectors:
                        main_content = soup.select_one(selector)
                        if main_content:
                            main_html = str(main_content)
                            break
                    
                    if main_html:
                        markdown_content = markdownify(main_html, heading_style="ATX")
                    else:
                        # Use the cleaned body HTML
                        body = soup.find('body')
                        if body:
                            for element in body.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                                element.decompose()
                            markdown_content = markdownify(str(body), heading_style="ATX")
                except Exception:
                    pass
            
            # Extract links and images
            links = []
            images = []
            
            if extract_links:
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href and href.startswith(('http', 'https')):
                        links.append(href)
            
            if extract_images:
                for img in soup.find_all('img', src=True):
                    src = img.get('src')
                    if src and src.startswith(('http', 'https')):
                        images.append(src)
            
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
                    'extraction_method': 'beautifulsoup',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE
                }
            )
            
        except Exception as e:
            raise RuntimeError(f"BeautifulSoup extraction failed: {str(e)}") 