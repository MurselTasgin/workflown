"""
DuckDuckGo Search Tool

Performs web searches using the DuckDuckGo API with fallback to HTML parsing.
DuckDuckGo doesn't require API keys and is more lenient with rate limiting.
"""

import aiohttp
import json
import re
from typing import List
from urllib.parse import quote_plus

from .base_search import BaseSearchTool, SearchResult


class DuckDuckGoSearchTool(BaseSearchTool):
    """
    DuckDuckGo search implementation.
    
    Uses the DuckDuckGo instant answer API first, then falls back to HTML parsing
    if no results are found. DuckDuckGo is generally more forgiving with rate limits.
    """
    
    def __init__(self, tool_id: str = None, config: dict = None):
        super().__init__(
            tool_id=tool_id or "duckduckgo_search",
            name="DuckDuckGoSearch", 
            description="Performs web searches using DuckDuckGo API",
            config=config
        )
        self.session = None
    
    def _initialize(self):
        """Initialize HTTP session."""
        pass
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": self.get_random_user_agent(),
                    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
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
        Perform DuckDuckGo search.
        
        First tries the instant answer API, then falls back to HTML parsing.
        """
        session = await self._get_session()
        
        # Try instant answer API first
        results = await self._search_instant_answer(session, query, max_results)
        
        if results:
            await self._log_info(
                f"DuckDuckGo instant answer search completed",
                query=query,
                results_count=len(results)
            )
            return results
        
        # Fallback to HTML search
        await self._log_info(f"Falling back to DuckDuckGo HTML search", query=query)
        results = await self._search_html(session, query, max_results, language, region)
        
        await self._log_info(
            f"DuckDuckGo HTML search completed",
            query=query,
            results_count=len(results)
        )
        
        return results
    
    async def _search_instant_answer(
        self,
        session: aiohttp.ClientSession,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """Search using DuckDuckGo instant answer API."""
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "no_redirect": "1",
            "t": "workflown"
        }
        
        try:
            async with session.get("https://api.duckduckgo.com/", params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    try:
                        data = json.loads(content)
                        return self._parse_instant_answer_results(data, max_results)
                    except json.JSONDecodeError:
                        await self._log_warning("Failed to parse DuckDuckGo JSON response")
                        return []
                elif response.status == 429:
                    raise Exception("DuckDuckGo rate limit exceeded (429)")
                elif response.status == 503:
                    raise Exception("DuckDuckGo service unavailable (503)")
                else:
                    raise Exception(f"DuckDuckGo API failed with status {response.status}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"DuckDuckGo connection error: {str(e)}")
    
    async def _search_html(
        self,
        session: aiohttp.ClientSession,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """Search using DuckDuckGo HTML interface."""
        search_url = f"https://html.duckduckgo.com/html/"
        
        # Use POST to avoid URL length limits
        data = {
            "q": query,
            "b": "",  # No bias
            "kl": f"{region.lower()}-{language.lower()}",
            "df": "",  # No date filter
            "s": "0"   # Start from result 0
        }
        
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": f"{language}-{region},{language};q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://html.duckduckgo.com",
            "Connection": "keep-alive",
            "Referer": "https://html.duckduckgo.com/",
            "Upgrade-Insecure-Requests": "1"
        }
        
        try:
            async with session.post(search_url, data=data, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    return self._parse_html_results(content, max_results)
                elif response.status == 429:
                    raise Exception("DuckDuckGo rate limit exceeded (429)")
                elif response.status == 403:
                    raise Exception("DuckDuckGo access forbidden - possible IP blocking (403)")
                else:
                    raise Exception(f"DuckDuckGo HTML search failed with status {response.status}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"DuckDuckGo HTML connection error: {str(e)}")
    
    def _parse_instant_answer_results(self, data: dict, max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo instant answer API results."""
        results = []
        
        # Extract abstract (main result)
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("AbstractText", "DuckDuckGo Result")[:100],
                url=data.get("AbstractURL", ""),
                snippet=data.get("Abstract", "")[:300],
                relevance=0.9,
                metadata={"source": "abstract", "answer_type": data.get("AnswerType", "")}
            ))
        
        # Extract definition if available
        if data.get("Definition"):
            results.append(SearchResult(
                title=f"Definition: {data.get('DefinitionWord', 'Term')}",
                url=data.get("DefinitionURL", ""),
                snippet=data.get("Definition", "")[:300],
                relevance=0.85,
                metadata={"source": "definition"}
            ))
        
        # Extract related topics
        for i, topic in enumerate(data.get("RelatedTopics", [])[:max_results-len(results)]):
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(SearchResult(
                    title=topic.get("Text", "")[:100],
                    url=topic.get("FirstURL", ""),
                    snippet=topic.get("Text", "")[:300],
                    relevance=0.7 - (i * 0.05),
                    metadata={"source": "related_topic"}
                ))
        
        # Extract answer if available
        if data.get("Answer") and not results:
            results.append(SearchResult(
                title=f"Answer: {query[:50]}",
                url="",
                snippet=data.get("Answer", "")[:300],
                relevance=0.95,
                metadata={"source": "answer", "answer_type": data.get("AnswerType", "")}
            ))
        
        return results[:max_results]
    
    def _parse_html_results(self, content: str, max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML search results."""
        results = []
        
        # Look for result containers
        result_pattern = r'<div class="result__body".*?>(.*?)</div>\s*</div>'
        result_matches = re.findall(result_pattern, content, re.DOTALL)
        
        for i, result_html in enumerate(result_matches[:max_results]):
            try:
                # Extract title and URL
                title_pattern = r'<a rel="nofollow" href="([^"]*)"[^>]*class="result__a"[^>]*>(.*?)</a>'
                title_match = re.search(title_pattern, result_html)
                
                if title_match:
                    url = title_match.group(1)
                    title = re.sub(r'<[^>]*>', '', title_match.group(2)).strip()
                    
                    # Extract snippet
                    snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'
                    snippet_match = re.search(snippet_pattern, result_html)
                    snippet = ""
                    
                    if snippet_match:
                        snippet = re.sub(r'<[^>]*>', '', snippet_match.group(1)).strip()
                    
                    # Fallback snippet extraction
                    if not snippet:
                        snippet_text = re.sub(r'<[^>]*>', ' ', result_html)
                        snippet = ' '.join(snippet_text.split())[:200]
                    
                    if title and url:
                        results.append(SearchResult(
                            title=title[:150],
                            url=url,
                            snippet=snippet[:300],
                            relevance=0.8 - (i * 0.05),
                            metadata={"source": "html_search", "position": i + 1}
                        ))
                            
            except Exception as e:
                # Use print instead of async logging in sync method
                print(f"Warning: Failed to parse HTML result {i+1}: {str(e)}")
                continue
        
        return results
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()