"""
LangChain Web Scraper

Content extraction using LangChain document loaders and transformers.
"""

from typing import Dict, List, Any, Optional

try:
    from langchain_community.document_transformers import BeautifulSoupTransformer
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

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


class LangChainScraper(BaseWebScraper):
    """
    LangChain-based web scraper for content extraction.
    
    Uses LangChain document transformers for content extraction and markdownify for HTML to Markdown conversion.
    """
    
    def __init__(self):
        super().__init__(
            name="LangChain Scraper",
            description="Content extraction using LangChain document loaders and transformers"
        )
        self.supports_markdown = MARKDOWNIFY_AVAILABLE
    
    def _check_availability(self) -> bool:
        """Check if LangChain is available."""
        return LANGCHAIN_AVAILABLE
    
    async def extract_content(
        self,
        url: str,
        extract_links: bool = False,
        extract_images: bool = False
    ) -> ScrapedContent:
        """
        Extract content using LangChain.
        
        Args:
            url: Source URL to fetch and extract content from
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            
        Returns:
            ScrapedContent object with extracted information
        """
        if not self.is_available:
            raise RuntimeError("LangChain is not available")
        
        # Fetch HTML content from URL
        html_content = await self._fetch_html_content(url)
        
        try:
            # Use BeautifulSoup for initial parsing
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extract main content using LangChain transformer
            content = ""
            try:
                transformer = BeautifulSoupTransformer()
                # Create a simple document structure for the transformer
                from langchain_core.documents import Document
                doc = Document(page_content=html_content, metadata={"source": url})
                transformed_docs = transformer.transform_documents([doc])
                if transformed_docs:
                    content = transformed_docs[0].page_content
            except Exception:
                # Fallback to basic BeautifulSoup extraction
                body = soup.find('body')
                if body:
                    content = body.get_text()
            
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
                try:
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        if href and href.startswith(('http', 'https')):
                            links.append(href)
                except Exception:
                    pass
            
            if extract_images:
                try:
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
                    'extraction_method': 'langchain',
                    'supports_markdown': MARKDOWNIFY_AVAILABLE
                }
            )
            
        except Exception as e:
            raise RuntimeError(f"LangChain extraction failed: {str(e)}") 