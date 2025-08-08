"""
Newspaper3k Web Scraper

Article-focused content extraction using Newspaper3k with markdown conversion.
"""

from typing import Dict, List, Any, Optional

try:
    import newspaper
    from newspaper import Article
    NEWSPAPER3K_AVAILABLE = True
except ImportError:
    NEWSPAPER3K_AVAILABLE = False

try:
    from markdownify import markdownify
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False

from .base_scraper import BaseWebScraper, ScrapedContent


class Newspaper3kScraper(BaseWebScraper):
    """
    Newspaper3k-based web scraper for article-focused content extraction.
    
    Uses Newspaper3k for article extraction and markdownify for HTML to Markdown conversion.
    """
    
    def __init__(self):
        super().__init__(
            name="Newspaper3k Scraper",
            description="Article-focused content extraction using Newspaper3k with markdown conversion"
        )
        self.supports_markdown = MARKDOWNIFY_AVAILABLE
    
    def _check_availability(self) -> bool:
        """Check if Newspaper3k is available."""
        return NEWSPAPER3K_AVAILABLE
    
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using Newspaper3k.
        
        Args:
            url: Source URL to fetch and extract content from
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if not self.is_available:
            raise RuntimeError("Newspaper3k is not available")
        
        # Fetch HTML content from URL
        html_content = await self._fetch_html_content(url)
        
        try:
            # Create article object
            article = Article(url)
            article.download(input_html=html_content)
            article.parse()
            article.nlp()
            
            # Extract content
            content = article.text or ""
            title = article.title or ""
            
            # Convert to markdown if markdownify is available
            markdown_content = ""
            if MARKDOWNIFY_AVAILABLE and html_content:
                try:
                    markdown_content = markdownify(html_content, heading_style="ATX")
                except Exception:
                    pass
            
            # Extract links and images
            links = []
            images = []
            
            if extract_links:
                # Try different ways to get links
                try:
                    if hasattr(article, 'links'):
                        links = article.links or []
                    else:
                        # Extract links manually from HTML
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html_content, 'html.parser')
                        for link in soup.find_all('a', href=True):
                            href = link.get('href')
                            if href and href.startswith(('http', 'https')):
                                links.append(href)
                except Exception:
                    pass
            
            if extract_images:
                # Try different ways to get images
                try:
                    if hasattr(article, 'images'):
                        images = article.images or []
                    else:
                        # Extract images manually from HTML
                        from bs4 import BeautifulSoup
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
                    'extraction_method': 'newspaper3k',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE,
                    'authors': getattr(article, 'authors', []),
                    'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                    'top_image': getattr(article, 'top_image', None)
                }
            )
            
        except Exception as e:
            raise RuntimeError(f"Newspaper3k extraction failed: {str(e)}") 