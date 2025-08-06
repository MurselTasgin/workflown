"""
Google Classic Search Tool

Performs web searches using Google Custom Search API or SerpAPI.
Requires API keys and has strict rate limiting.
"""

import aiohttp
import os
from typing import List, Optional

from base_search import BaseSearchTool, SearchResult


class GoogleClassicSearchTool(BaseSearchTool):
    """
    Google search implementation using Custom Search API or SerpAPI.
    
    Supports both Google Custom Search API and SerpAPI for Google searches.
    Requires API keys and handles strict rate limits.
    
    Configuration:
    - google_api_key: Google Custom Search API key
    - google_cse_id: Google Custom Search Engine ID  
    - serpapi_key: SerpAPI key (alternative to Google API)
    - preferred_api: "google" or "serpapi" (default: "google")
    """
    
    def __init__(self, tool_id: str = None, config: dict = None):
        super().__init__(
            tool_id=tool_id or "google_classic_search",
            name="GoogleClassicSearch",
            description="Performs web searches using Google APIs (Custom Search or SerpAPI)",
            config=config
        )
        
        # API configuration
        self.google_api_key = self.config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = self.config.get("google_cse_id") or os.getenv("GOOGLE_CSE_ID")
        self.serpapi_key = self.config.get("serpapi_key") or os.getenv("SERPAPI_KEY")
        self.preferred_api = self.config.get("preferred_api", "google")
        
        # Determine which API to use
        self.use_google_api = bool(self.google_api_key and self.google_cse_id)
        self.use_serpapi = bool(self.serpapi_key)
        
        if not self.use_google_api and not self.use_serpapi:
            raise ValueError(
                "No valid API configuration found. Please provide either:\n"
                "1. google_api_key + google_cse_id for Google Custom Search API, or\n"
                "2. serpapi_key for SerpAPI\n"
                "Set via config dict or environment variables."
            )
        
        self.session = None
    
    def _initialize(self):
        """Initialize HTTP session."""
        pass
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=45)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self.get_random_user_agent()}
            )
        return self.session
    
    async def _perform_search(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """
        Perform Google search using available API.
        
        Tries preferred API first, then falls back to alternative if available.
        """
        # Determine which API to try first
        if self.preferred_api == "serpapi" and self.use_serpapi:
            try:
                return await self._search_serpapi(query, max_results, language, region)
            except Exception as e:
                if self.use_google_api:
                    await self._log_warning(f"SerpAPI failed, trying Google API", error=str(e))
                    return await self._search_google_api(query, max_results, language, region)
                raise
        else:
            # Default to Google API first
            if self.use_google_api:
                try:
                    return await self._search_google_api(query, max_results, language, region)
                except Exception as e:
                    if self.use_serpapi:
                        await self._log_warning(f"Google API failed, trying SerpAPI", error=str(e))
                        return await self._search_serpapi(query, max_results, language, region)
                    raise
            elif self.use_serpapi:
                return await self._search_serpapi(query, max_results, language, region)
            else:
                raise Exception("No valid API configuration available")
    
    async def _search_google_api(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """Search using Google Custom Search API."""
        session = await self._get_session()
        
        # Google Custom Search API parameters
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": query,
            "num": min(max_results, 10),  # Google API max is 10 per request
            "hl": language,
            "gl": region.lower(),
            "safe": "off",
            "searchType": "text"
        }
        
        url = "https://www.googleapis.com/customsearch/v1"
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_google_api_results(data, max_results)
                elif response.status == 429:
                    raise Exception("Google API rate limit exceeded (429) - daily quota may be exhausted")
                elif response.status == 403:
                    raise Exception("Google API access forbidden (403) - check API key and billing")
                elif response.status == 400:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                    raise Exception(f"Google API bad request (400): {error_msg}")
                else:
                    raise Exception(f"Google API failed with status {response.status}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Google API connection error: {str(e)}")
    
    async def _search_serpapi(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """Search using SerpAPI."""
        session = await self._get_session()
        
        # SerpAPI parameters
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "engine": "google",
            "num": min(max_results, 20),  # SerpAPI allows more results
            "hl": language,
            "gl": region.lower(),
            "safe": "off",
            "format": "json"
        }
        
        url = "https://serpapi.com/search"
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_serpapi_results(data, max_results)
                elif response.status == 429:
                    raise Exception("SerpAPI rate limit exceeded (429)")
                elif response.status == 402:
                    raise Exception("SerpAPI quota exceeded (402) - check your plan limits")
                elif response.status == 401:
                    raise Exception("SerpAPI unauthorized (401) - check your API key")
                else:
                    raise Exception(f"SerpAPI failed with status {response.status}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"SerpAPI connection error: {str(e)}")
    
    def _parse_google_api_results(self, data: dict, max_results: int) -> List[SearchResult]:
        """Parse Google Custom Search API results."""
        results = []
        
        items = data.get("items", [])
        search_info = data.get("searchInformation", {})
        
        for i, item in enumerate(items[:max_results]):
            # Extract snippet, handling pagemap data
            snippet = item.get("snippet", "")
            
            # Try to get better snippet from pagemap
            pagemap = item.get("pagemap", {})
            if pagemap.get("metatags"):
                meta_description = pagemap["metatags"][0].get("og:description") or \
                                pagemap["metatags"][0].get("description")
                if meta_description and len(meta_description) > len(snippet):
                    snippet = meta_description
            
            results.append(SearchResult(
                title=item.get("title", f"Result {i+1}")[:150],
                url=item.get("link", ""),
                snippet=snippet[:400],
                relevance=0.95 - (i * 0.05),
                metadata={
                    "source": "google_api",
                    "position": i + 1,
                    "display_link": item.get("displayLink", ""),
                    "formatted_url": item.get("formattedUrl", ""),
                    "search_time": search_info.get("searchTime"),
                    "total_results": search_info.get("totalResults")
                }
            ))
        
        return results
    
    def _parse_serpapi_results(self, data: dict, max_results: int) -> List[SearchResult]:
        """Parse SerpAPI results."""
        results = []
        
        organic_results = data.get("organic_results", [])
        search_metadata = data.get("search_metadata", {})
        
        for i, result in enumerate(organic_results[:max_results]):
            # Extract rich snippet if available
            snippet = result.get("snippet", "")
            rich_snippet = result.get("rich_snippet", {})
            
            if rich_snippet.get("top", {}).get("extensions"):
                extensions = " | ".join(rich_snippet["top"]["extensions"])
                snippet = f"{snippet}\n{extensions}" if snippet else extensions
            
            results.append(SearchResult(
                title=result.get("title", f"Result {i+1}")[:150],
                url=result.get("link", ""),
                snippet=snippet[:400],
                relevance=0.95 - (i * 0.05),
                metadata={
                    "source": "serpapi",
                    "position": result.get("position", i + 1),
                    "displayed_link": result.get("displayed_link", ""),
                    "favicon": result.get("favicon"),
                    "date": result.get("date"),
                    "cached_page_link": result.get("cached_page_link"),
                    "related_pages_link": result.get("related_pages_link"),
                    "search_id": search_metadata.get("id"),
                    "engine": search_metadata.get("engine")
                }
            ))
        
        return results
    
    def get_api_status(self) -> dict:
        """Get status of available APIs."""
        return {
            "google_api_available": self.use_google_api,
            "serpapi_available": self.use_serpapi,
            "preferred_api": self.preferred_api,
            "google_api_key_configured": bool(self.google_api_key),
            "google_cse_id_configured": bool(self.google_cse_id),
            "serpapi_key_configured": bool(self.serpapi_key)
        }
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()