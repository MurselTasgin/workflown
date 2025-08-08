"""
Google Search Python Library Tool

Performs web searches using the googlesearch-python library.
Simple to use but has limited features and may be blocked more easily.
"""

import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor

try:
    from googlesearch import search as google_search
    GOOGLESEARCH_AVAILABLE = True
except ImportError:
    GOOGLESEARCH_AVAILABLE = False

from .base_search import BaseSearchTool, SearchResult


class GoogleSearchPythonTool(BaseSearchTool):
    """
    Google search implementation using googlesearch-python library.
    
    This is a simple wrapper around the googlesearch-python library.
    It's easy to use but has limitations:
    - No snippet extraction (only titles and URLs)
    - More prone to being blocked by Google
    - Limited configuration options
    - Synchronous library (wrapped in async)
    
    Configuration:
    - pause_between_requests: Delay between requests (default: 2.0 seconds)
    - tld: Top-level domain to use (default: "com")
    - lang: Language for search (default: "en")
    - safe: Safe search setting (default: "off")
    - country: Country code for search (default: "US")
    """
    
    def __init__(self, tool_id: str = None, config: dict = None):
        if not GOOGLESEARCH_AVAILABLE:
            raise ImportError(
                "googlesearch-python is required for GoogleSearchPythonTool. "
                "Install with: pip install googlesearch-python"
            )
        
        super().__init__(
            tool_id=tool_id or "googlesearch_python_search",
            name="GoogleSearchPython",
            description="Performs web searches using googlesearch-python library",
            config=config
        )
        
        # Library-specific configuration
        self.pause_between_requests = self.config.get("pause_between_requests", 2.0)
        self.tld = self.config.get("tld", "com")
        self.lang = self.config.get("lang", "en")
        self.safe = self.config.get("safe", "off")
        self.country = self.config.get("country", "US")
        
        # Thread pool for running synchronous library in async context
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    def _initialize(self):
        """Initialize thread pool executor."""
        pass
    
    async def _perform_search(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """
        Perform Google search using googlesearch-python library.
        
        Note: This library doesn't provide snippets, so we only get titles and URLs.
        The library is synchronous, so we run it in a thread pool.
        """
        # Override language and region from parameters
        search_lang = language or self.lang
        search_country = region or self.country
        
        await self._log_info(
            f"Starting googlesearch-python search",
            query=query,
            max_results=max_results,
            lang=search_lang,
            country=search_country
        )
        
        try:
            # Run the synchronous search in a thread pool
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                self.executor,
                self._run_google_search,
                query,
                max_results,
                search_lang,
                search_country
            )
            
            # Convert URLs to SearchResult objects
            results = []
            for i, result in enumerate(search_results):
                if result:
                    # Extract domain for title (since library doesn't provide titles)
                    title = self._extract_title_from_url(result, query, i)
                    
                    description = result.description
                    if description:
                        description = description.replace(query, "").strip()
                    else:
                        description = f"Search result from googlesearch-python library for: {query}"
                    
                    results.append(SearchResult(
                        title=title,
                        url=result.url,     
                        snippet=description,
                        relevance=0.9 - (i * 0.05),
                        metadata={
                            "source": "googlesearch_python",
                            "position": i + 1,
                            "library_version": "googlesearch-python",
                            "note": "Limited metadata - library provides URLs only"
                        }
                    ))
            
            await self._log_info(
                f"googlesearch-python search completed",
                query=query,
                results_found=len(results)
            )
            
            return results
            
        except Exception as e:
            # Check for common googlesearch-python errors
            error_msg = str(e).lower()
            if "429" in error_msg or "too many requests" in error_msg:
                raise Exception("Google blocked requests - too many requests (429)")
            elif "403" in error_msg or "forbidden" in error_msg:
                raise Exception("Google access forbidden - possible IP blocking (403)")
            elif "captcha" in error_msg:
                raise Exception("Google CAPTCHA detected - IP may be blocked")
            elif "connection" in error_msg:
                raise Exception(f"Connection error: {str(e)}")
            else:
                raise Exception(f"googlesearch-python error: {str(e)}")
    
    def _run_google_search(
        self,
        query: str,
        max_results: int,
        language: str,
        country: str
    ) -> List[str]:
        """
        Run the actual Google search using googlesearch-python.
        
        This runs in a thread pool since the library is synchronous.
        """
        try:
            #---------------------------------------------------------------------------------------
            # Search Parameters: 
            #---------------------------------------------------------------------------------------
            ###  term, num_results=10, lang="en", proxy=None, advanced=False, sleep_interval=0, 
            ###  timeout=5, safe="active", ssl_verify=None, region=None, start_num=0, unique=False
            #---------------------------------------------------------------------------------------

            # Configure search parameters
            search_params = {
                'term': query,
                'num_results': max_results,
                'lang': language,
                'advanced': True,
                'safe': self.safe,
                'ssl_verify': None,
                'region': None,
                'start_num': 0,
                'unique': False
            }
            
            # Add pause to be respectful to Google
            if self.pause_between_requests > 0:
                search_params['sleep_interval'] = self.pause_between_requests
            
            # Perform search and collect URLs
            results = []
            for result in google_search(**search_params):
                results.append(result)
                if len(results) >= max_results:
                    break
            
            return results
            
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"googlesearch-python library error: {str(e)}")
    
    def _extract_title_from_url(self, result: SearchResult, query: str, position: int) -> str:
        """
        Extract a reasonable title from the URL since the library doesn't provide titles.
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(result.url)
            domain = parsed.netloc
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            if result.title:
                return result.title
            else:
                # Create a title based on domain and query
                title = f"{domain.title()} - {query}"            
                # Limit length
                if len(title) > 100:
                    title = f"{domain.title()} - Result {position + 1}"
                
                return title
            
        except Exception:
            return f"Search Result {position + 1}"
    
    def get_library_info(self) -> dict:
        """Get information about the googlesearch-python library."""
        info = {
            "library_available": GOOGLESEARCH_AVAILABLE,
            "library_name": "googlesearch-python",
            "features": {
                "provides_urls": True,
                "provides_titles": False,
                "provides_snippets": False,
                "provides_metadata": False
            },
            "limitations": [
                "No title extraction (URLs only)",
                "No snippet extraction", 
                "More prone to Google blocking",
                "Synchronous library (wrapped in async)",
                "Limited configuration options"
            ],
            "configuration": {
                "pause_between_requests": self.pause_between_requests,
                "tld": self.tld,
                "lang": self.lang,
                "safe": self.safe,
                "country": self.country
            }
        }
        
        if GOOGLESEARCH_AVAILABLE:
            try:
                import googlesearch
                info["library_version"] = getattr(googlesearch, '__version__', 'unknown')
            except:
                info["library_version"] = 'unknown'
        
        return info
    
    async def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=True)