"""
Base Search Tool

Abstract base class for all web search implementations with common functionality
including rate limiting, retry mechanisms, and result standardization.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability


class SearchResult:
    """Standardized search result format."""
    
    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        relevance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.relevance = relevance
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'relevance': self.relevance,
            'metadata': self.metadata
        }


class BaseSearchTool(BaseTool, ABC):
    """
    Abstract base class for web search tools with rate limiting protection.
    
    Provides common functionality:
    - Intelligent request throttling
    - Exponential backoff retry mechanism  
    - User agent rotation
    - Request history tracking
    - Standardized result format
    """
    
    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        config: Dict[str, Any] = None
    ):
        super().__init__(
            tool_id=tool_id,
            name=name,
            description=description,
            capabilities=[ToolCapability.WEB_SEARCH, ToolCapability.HTTP_REQUESTS],
            config=config,
            max_concurrent_operations=5
        )
        
        # Rate limiting configuration
        self.rate_limit_delay = self.config.get("rate_limit_delay", 1.0)
        self.max_retries = self.config.get("max_retries", 3)
        self.exponential_backoff_base = self.config.get("exponential_backoff_base", 2.0)
        self.max_backoff_delay = self.config.get("max_backoff_delay", 30.0)
        self.jitter_range = self.config.get("jitter_range", 0.1)
        
        # Request tracking
        self.request_history = []
        self.last_request_time = None
        self.consecutive_failures = 0
        
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self._initialize()
    
    def _initialize(self):
        """Initialize tool-specific components. Override in subclasses."""
        pass
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.user_agents)
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute search with retry mechanism and rate limiting.
        
        Args:
            parameters: Search parameters including:
                - query: Search query string (required)
                - max_results: Maximum number of results (default: 10)
                - language: Language code (default: "en")
                - region: Region code (default: "US")
        
        Returns:
            ToolResult with search results
        """
        query = parameters.get("query", "").strip()
        if not query:
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=["No search query provided"]
            )
        
        max_results = parameters.get("max_results", 10)
        language = parameters.get("language", "en")
        region = parameters.get("region", "US")
        
        await self._log_info(
            f"Starting search",
            query=query,
            max_results=max_results,
            language=language,
            region=region
        )
        
        try:
            # Apply intelligent throttling
            await self._apply_intelligent_throttling()
            
            # Perform search with retry mechanism
            results = await self._search_with_retry(query, max_results, language, region)
            #print("------------------------------  SEARCH RESULTS ------------------------------")
            #print(f"results: {results}")
            #print("----------------------------------------------------------------------------")
            
            # Convert SearchResult objects to dictionaries
            result_dicts = [r.to_dict() if isinstance(r, SearchResult) else r for r in results]
            #print("------------------------------  RESULT DICTS ------------------------------")
            #print(f"result_dicts: {result_dicts}")
            #print("----------------------------------------------------------------------------")
            
            return ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=result_dicts,
                metadata={
                    "query": query,
                    "results_count": len(results),
                    "max_results": max_results,
                    "language": language,
                    "region": region,
                    "search_engine": self.name
                }
            )
            
        except Exception as e:
            await self._log_error(f"Search failed", query=query, error=str(e))
            
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                metadata={"query": query, "search_engine": self.name},
                errors=[str(e)]
            )
    
    async def _apply_intelligent_throttling(self):
        """Apply intelligent throttling based on request history and failures."""
        current_time = datetime.now()
        
        # Clean old request history (keep last hour)
        cutoff_time = current_time - timedelta(hours=1)
        self.request_history = [req_time for req_time in self.request_history if req_time > cutoff_time]
        
        # Calculate dynamic delay based on request frequency and consecutive failures
        requests_per_minute = len([
            req_time for req_time in self.request_history 
            if req_time > current_time - timedelta(minutes=1)
        ])
        
        # Base delay increases with consecutive failures
        base_delay = self.rate_limit_delay * (1 + self.consecutive_failures * 0.3)
        
        # Additional delay if too many requests per minute
        if requests_per_minute > 6:
            base_delay *= (requests_per_minute / 6)
        
        # Add jitter to avoid thundering herd
        jitter = random.uniform(-self.jitter_range, self.jitter_range) * base_delay
        total_delay = max(0, base_delay + jitter)
        
        # Respect minimum time between requests
        if self.last_request_time:
            time_since_last = (current_time - self.last_request_time).total_seconds()
            if time_since_last < total_delay:
                await asyncio.sleep(total_delay - time_since_last)
        else:
            await asyncio.sleep(total_delay)
        
        # Record request time
        self.request_history.append(current_time)
        self.last_request_time = current_time
    
    async def _search_with_retry(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """Perform search with exponential backoff retry mechanism."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Perform the actual search (implemented by subclasses)
                results = await self._perform_search(query, max_results, language, region)
                
                # Reset consecutive failures on success
                self.consecutive_failures = 0
                return results
                
            except Exception as e:
                last_exception = e
                self.consecutive_failures += 1
                
                # Check if this is a rate limit error
                is_rate_limit = self._is_rate_limit_error(e)
                
                await self._log_warning(
                    f"Search attempt {attempt + 1} failed",
                    query=query,
                    error=str(e),
                    is_rate_limit=is_rate_limit,
                    consecutive_failures=self.consecutive_failures
                )
                
                if attempt < self.max_retries - 1:
                    if is_rate_limit:
                        # Longer delay for rate limit errors  
                        delay = min(
                            self.exponential_backoff_base ** (attempt + 2),
                            self.max_backoff_delay
                        )
                    else:
                        # Standard exponential backoff
                        delay = min(
                            self.exponential_backoff_base ** attempt,
                            self.max_backoff_delay
                        )
                    
                    # Add jitter
                    jitter = random.uniform(0.1, 0.3) * delay
                    total_delay = delay + jitter
                    
                    await self._log_info(
                        f"Retrying in {total_delay:.2f} seconds",
                        attempt=attempt + 1,
                        delay=total_delay
                    )
                    
                    await asyncio.sleep(total_delay)
        
        # All attempts failed
        raise last_exception or Exception("All search attempts failed")
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error indicates rate limiting."""
        error_str = str(error).lower()
        rate_limit_indicators = [
            "429", "too many requests", "rate limit", "quota exceeded",
            "throttled", "service unavailable", "503", "temporarily blocked",
            "blocked", "captcha", "bot detected"
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)
    
    @abstractmethod
    async def _perform_search(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """
        Perform the actual search. Must be implemented by subclasses.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            language: Language code
            region: Region code
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operation types."""
        return ["web_search", "search", "query"]
    
    async def cleanup(self):
        """Clean up resources. Override in subclasses if needed."""
        pass
    
    # Logging helpers
    async def _log_info(self, message: str, **kwargs):
        """Log info message."""
        if hasattr(self, 'logger'):
            await self.logger.info(message, tool_id=self.tool_id, **kwargs)
    
    async def _log_warning(self, message: str, **kwargs):
        """Log warning message."""
        if hasattr(self, 'logger'):
            await self.logger.warning(message, tool_id=self.tool_id, **kwargs)
    
    async def _log_error(self, message: str, **kwargs):
        """Log error message."""
        if hasattr(self, 'logger'):
            await self.logger.error(message, tool_id=self.tool_id, **kwargs)