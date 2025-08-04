"""
Web Search Tool

Performs web searches using various search engines and APIs.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
import time

from .base_tool import BaseTool, ToolResult, ToolCapability
from workflown.core.config.central_config import get_config


class WebSearchTool(BaseTool):
    """
    Tool for performing web searches using various search engines.
    
    Supports multiple search engines and APIs with fallback mechanisms.
    """
    
    def __init__(
        self,
        tool_id: str = None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the web search tool.
        
        Args:
            tool_id: Unique tool identifier
            config: Configuration dictionary
        """
        super().__init__(
            tool_id=tool_id,
            name="WebSearchTool",
            description="Performs web searches using multiple search engines",
            capabilities=[ToolCapability.WEB_SEARCH, ToolCapability.HTTP_REQUESTS],
            config=config,
            max_concurrent_operations=10
        )
        
        # Get search configuration
        self.search_config = get_config().get_search_config()
        
        # Search engine configurations
        self.search_engines = {
            "duckduckgo": {
                "base_url": "https://api.duckduckgo.com/",
                "params": {"q": "", "format": "json", "no_html": "1"},
                "enabled": True
            },
            "serpapi": {
                "base_url": "https://serpapi.com/search",
                "params": {"q": "", "api_key": ""},
                "enabled": bool(self.search_config.get("serpapi_key"))
            }
        }
        
        # Rate limiting
        self.rate_limit_delay = self.config.get("rate_limit_delay", 1.0)
        self.max_retries = self.config.get("max_retries", 3)
        
        # Session for HTTP requests
        self.session = None
        self._initialize()
    
    def _initialize(self):
        """Initialize HTTP session and other components."""
        # Session will be created on first use
        pass
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Workflown/1.0)"
                }
            )
        return self.session
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute web search with given parameters.
        
        Args:
            parameters: Search parameters including:
                - query: Search query string
                - engine: Search engine to use (optional)
                - max_results: Maximum number of results (default: 10)
                - language: Language for search (optional)
                - region: Region for search (optional)
                
        Returns:
            ToolResult with search results
        """
        query = parameters.get("query", "")
        if not query:
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=["No search query provided"]
            )
        
        engine = parameters.get("engine", self.search_config.get("default_engine", "duckduckgo"))
        max_results = parameters.get("max_results", 10)
        language = parameters.get("language", "en")
        region = parameters.get("region", "US")
        
        await self.logger.info(
            f"Starting web search",
            tool_id=self.tool_id,
            query=query,
            engine=engine,
            max_results=max_results
        )
        
        try:
            # Perform search
            results = await self._perform_search(
                query=query,
                engine=engine,
                max_results=max_results,
                language=language,
                region=region
            )
            
            return ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=results,
                metadata={
                    "query": query,
                    "engine": engine,
                    "results_count": len(results),
                    "max_results": max_results,
                    "language": language,
                    "region": region
                }
            )
            
        except Exception as e:
            await self.logger.error(
                f"Web search failed",
                tool_id=self.tool_id,
                query=query,
                error=str(e)
            )
            
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                metadata={"query": query, "engine": engine},
                errors=[str(e)]
            )
    
    async def _perform_search(
        self,
        query: str,
        engine: str = "duckduckgo",
        max_results: int = 10,
        language: str = "en",
        region: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        Perform search using specified engine.
        
        Args:
            query: Search query
            engine: Search engine to use
            max_results: Maximum number of results
            language: Language for search
            region: Region for search
            
        Returns:
            List of search results
        """
        if engine not in self.search_engines:
            # Try with fallback engines
            for fallback_engine in ["duckduckgo", "serpapi"]:
                if fallback_engine in self.search_engines and self.search_engines[fallback_engine]["enabled"]:
                    engine = fallback_engine
                    break
            else:
                raise ValueError(f"Unsupported search engine: {engine}")
        
        engine_config = self.search_engines[engine]
        if not engine_config["enabled"]:
            raise ValueError(f"Search engine {engine} is disabled")
        
        # Rate limiting
        await asyncio.sleep(self.rate_limit_delay)
        
        # Perform search based on engine
        if engine == "duckduckgo":
            return await self._search_duckduckgo(query, max_results, language, region)
        elif engine == "serpapi":
            return await self._search_serpapi(query, max_results, language, region)
        else:
            # Try with fallback engines
            for fallback_engine in ["duckduckgo", "serpapi"]:
                if fallback_engine in self.search_engines and self.search_engines[fallback_engine]["enabled"]:
                    engine = fallback_engine
                    break
            else:
                raise ValueError(f"Unsupported search engine: {engine}")
            
            # Retry with fallback engine
            if engine == "duckduckgo":
                return await self._search_duckduckgo(query, max_results, language, region)
            elif engine == "serpapi":
                return await self._search_serpapi(query, max_results, language, region)
    
    async def _search_serpapi(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[Dict[str, Any]]:
        """Search using SerpAPI."""
        session = await self._get_session()
        
        params = {
            "q": query,
            "num": min(max_results, 10),
            "hl": language,
            "gl": region.lower(),
            "api_key": self.search_config.get("serpapi_key")
        }
        
        try:
            async with session.get(
                "https://serpapi.com/search",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_serpapi_results(data, max_results)
                else:
                    raise Exception(f"SerpAPI search failed with status {response.status}")
        except Exception as e:
            await self.logger.error(
                f"SerpAPI search failed",
                tool_id=self.tool_id,
                error=str(e)
            )
            raise e
    
    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo API."""
        session = await self._get_session()
        
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "t": "workflown"
        }
        
        try:
            async with session.get(
                "https://api.duckduckgo.com/",
                params=params,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; Workflown/1.0)"
                }
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    try:
                        data = json.loads(content)
                        results = self._parse_duckduckgo_results(data, max_results)
                        await self.logger.info(
                            f"DuckDuckGo search completed",
                            tool_id=self.tool_id,
                            query=query,
                            results_count=len(results) if results else 0
                        )
                        if results:
                            return results
                        else:
                            # If no results from JSON, try HTML parsing
                            html_results = self._parse_duckduckgo_html(content, max_results)
                            await self.logger.info(
                                f"DuckDuckGo HTML parsing completed",
                                tool_id=self.tool_id,
                                html_results_count=len(html_results) if html_results else 0
                            )
                            return html_results
                    except json.JSONDecodeError:
                        # If JSON parsing fails, try to extract results from HTML
                        html_results = self._parse_duckduckgo_html(content, max_results)
                        await self.logger.info(
                            f"DuckDuckGo HTML parsing completed (JSON decode error)",
                            tool_id=self.tool_id,
                            html_results_count=len(html_results) if html_results else 0
                        )
                        return html_results
                else:
                    raise Exception(f"DuckDuckGo search failed with status {response.status}")
        except Exception as e:
            await self.logger.error(
                f"DuckDuckGo search failed",
                tool_id=self.tool_id,
                error=str(e)
            )
            raise e
    
    def _parse_serpapi_results(self, data: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Parse SerpAPI search results."""
        results = []
        
        # Extract organic results from SerpAPI response
        organic_results = data.get("organic_results", [])
        
        for i, result in enumerate(organic_results[:max_results]):
            results.append({
                "title": result.get("title", f"Result {i+1}"),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", "Search result"),
                "relevance": 0.9 - (i * 0.1)
            })
        
        return results
    
    def _parse_duckduckgo_results(self, data: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo API results."""
        results = []
        
        # Extract abstract
        if data.get("Abstract"):
            results.append({
                "title": data.get("AbstractText", "DuckDuckGo Result"),
                "url": data.get("AbstractURL", ""),
                "snippet": data.get("Abstract", ""),
                "relevance": 0.9
            })
        
        # Extract related topics
        for topic in data.get("RelatedTopics", [])[:max_results-1]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                    "relevance": 0.7
                })
        
        return results[:max_results]
    
    def _parse_duckduckgo_html(self, content: str, max_results: int) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo HTML results as fallback."""
        results = []
        
        import re
        
        # Look for search result links
        link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>'
        matches = re.findall(link_pattern, content)
        
        for url, title in matches[:max_results]:
            if url.startswith('http') and 'duckduckgo.com' not in url:
                results.append({
                    "title": title.strip(),
                    "url": url,
                    "snippet": f"Search result for: {title}",
                    "relevance": 0.8
                })
        
        return results[:max_results]
    
    def _extract_title(self, line: str) -> str:
        """Extract title from HTML line."""
        # Simplified title extraction
        if 'title="' in line:
            start = line.find('title="') + 7
            end = line.find('"', start)
            return line[start:end]
        return "Search Result"
    
    def _extract_snippet(self, content: str, url: str) -> str:
        """Extract snippet from content."""
        # Simplified snippet extraction
        return "Search result snippet..."
    

    
    def get_supported_operations(self) -> List[str]:
        """Get supported operation types."""
        return ["web_search", "search", "query"]
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close() 