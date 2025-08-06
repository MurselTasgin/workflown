"""
Web Search Tool

Performs web searches using various search engines and APIs with robust rate limiting protection.

Enhanced Features:
- Exponential backoff retry mechanism with configurable parameters
- Intelligent request throttling based on request history and failure patterns
- User agent rotation to avoid detection
- Selenium-based browser fallback for when APIs are rate limited
- Comprehensive rate limit error detection and handling

Configuration Options:
{
    "rate_limit_delay": 1.0,                    # Base delay between requests (seconds)
    "max_retries": 5,                          # Maximum retry attempts
    "exponential_backoff_base": 2.0,           # Base for exponential backoff calculation
    "max_backoff_delay": 60.0,                 # Maximum backoff delay (seconds)
    "jitter_range": 0.1,                       # Jitter range for randomizing delays
    "enable_browser_fallback": true,           # Enable Selenium browser fallback
    "browser_type": "chrome",                  # Browser type: "chrome" or "firefox"  
    "headless_browser": true                   # Run browser in headless mode
}

Dependencies:
- aiohttp: For HTTP requests
- selenium: For browser fallback (optional but recommended)
- webdriver-manager: For automatic driver management (recommended)

Install dependencies: pip install aiohttp selenium webdriver-manager
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
import time
import random
import logging
from datetime import datetime, timedelta
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from base_tool import BaseTool, ToolResult, ToolCapability
# Real config for LLM providers
def get_config():
    class Config:
        def get_azure_openai_config(self):
            return {
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                "model_name": os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4o-mini"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                "max_tokens": int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "2000")),
                "temperature": float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.7"))
            }
        
        def get_search_config(self):
            return {
                "serpapi_key": os.getenv("SERPAPI_KEY"),
                "default_engine": os.getenv("SEARCH_DEFAULT_ENGINE", "duckduckgo")
            }
    return Config()


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
        
        # Enhanced rate limiting and retry configuration
        self.rate_limit_delay = self.config.get("rate_limit_delay", 1.0)
        self.max_retries = self.config.get("max_retries", 5)
        self.exponential_backoff_base = self.config.get("exponential_backoff_base", 2.0)
        self.max_backoff_delay = self.config.get("max_backoff_delay", 60.0)
        self.jitter_range = self.config.get("jitter_range", 0.1)
        
        # Browser fallback configuration
        self.enable_browser_fallback = self.config.get("enable_browser_fallback", True)
        self.browser_type = self.config.get("browser_type", "chrome")  # chrome or firefox
        self.headless_browser = self.config.get("headless_browser", True)
        
        # Request tracking for intelligent throttling
        self.request_history = []
        self.last_request_time = None
        self.consecutive_failures = 0
        
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (compatible; Workflown/1.0)"
        ]
        
        # Session for HTTP requests
        self.session = None
        self.driver = None
        self._initialize()
    
    def _initialize(self):
        """Initialize HTTP session and other components."""
        # Session will be created on first use
        pass
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with rotating user agent."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            user_agent = random.choice(self.user_agents)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
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
        
        # Intelligent throttling with request history
        await self._apply_intelligent_throttling()
        
        # Perform search with retry mechanism
        return await self._search_with_retry(query, engine, max_results, language, region)
    
    async def _apply_intelligent_throttling(self):
        """Apply intelligent throttling based on request history and failures."""
        current_time = datetime.now()
        
        # Clean old request history (keep last hour)
        cutoff_time = current_time - timedelta(hours=1)
        self.request_history = [req_time for req_time in self.request_history if req_time > cutoff_time]
        
        # Calculate dynamic delay based on request frequency and consecutive failures
        requests_per_minute = len([req_time for req_time in self.request_history if req_time > current_time - timedelta(minutes=1)])
        
        # Base delay increases with consecutive failures
        base_delay = self.rate_limit_delay * (1 + self.consecutive_failures * 0.5)
        
        # Additional delay if too many requests per minute
        if requests_per_minute > 10:
            base_delay *= (requests_per_minute / 10)
        
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
        engine: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[Dict[str, Any]]:
        """Perform search with exponential backoff retry mechanism."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Try API-based search first
                results = await self._perform_api_search(query, engine, max_results, language, region)
                
                # Reset consecutive failures on success
                self.consecutive_failures = 0
                return results
                
            except Exception as e:
                last_exception = e
                self.consecutive_failures += 1
                
                # Check if this is a rate limit error
                is_rate_limit = self._is_rate_limit_error(e)
                
                await self.logger.warning(
                    f"Search attempt {attempt + 1} failed",
                    tool_id=self.tool_id,
                    query=query,
                    engine=engine,
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
                    
                    await self.logger.info(
                        f"Retrying in {total_delay:.2f} seconds",
                        tool_id=self.tool_id,
                        attempt=attempt + 1,
                        delay=total_delay
                    )
                    
                    await asyncio.sleep(total_delay)
        
        # If all API attempts failed and browser fallback is enabled, try browser search
        if self.enable_browser_fallback and SELENIUM_AVAILABLE:
            try:
                await self.logger.info(
                    f"Falling back to browser search",
                    tool_id=self.tool_id,
                    query=query
                )
                results = await self._search_with_browser(query, max_results)
                if results:
                    self.consecutive_failures = 0
                    return results
            except Exception as browser_e:
                await self.logger.error(
                    f"Browser fallback also failed",
                    tool_id=self.tool_id,
                    error=str(browser_e)
                )
        
        # All attempts failed
        raise last_exception or Exception("All search attempts failed")

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error indicates rate limiting."""
        error_str = str(error).lower()
        rate_limit_indicators = [
            "429", "too many requests", "rate limit", "quota exceeded",
            "throttled", "service unavailable", "503", "temporarily blocked"
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)

    async def _perform_api_search(
        self,
        query: str,
        engine: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[Dict[str, Any]]:
        """Perform API-based search with the specified engine."""
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

    async def _search_with_browser(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform search using headless browser as fallback."""
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium not available for browser fallback")
        
        driver = None
        try:
            # Setup browser options
            if self.browser_type.lower() == "firefox":
                options = FirefoxOptions()
                if self.headless_browser:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                driver = webdriver.Firefox(options=options)
            else:  # Default to Chrome
                options = ChromeOptions()
                if self.headless_browser:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                # Rotate user agent
                user_agent = random.choice(self.user_agents)
                options.add_argument(f"--user-agent={user_agent}")
                driver = webdriver.Chrome(options=options)
            
            # Search using DuckDuckGo as it's more browser-friendly
            search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
            driver.get(search_url)
            
            # Wait for results to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='result']")))
            
            # Extract search results
            results = []
            result_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='result']")
            
            for i, element in enumerate(result_elements[:max_results]):
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, "h2 a")
                    title = title_elem.text or f"Result {i+1}"
                    url = title_elem.get_attribute("href") or ""
                    
                    snippet_elem = element.find_element(By.CSS_SELECTOR, "[data-result='snippet']")
                    snippet = snippet_elem.text or "No description available"
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "relevance": 0.9 - (i * 0.1)
                    })
                except Exception as e:
                    # Skip this result if extraction fails
                    continue
            
            return results
            
        except TimeoutException:
            raise Exception("Browser search timed out waiting for results")
        except WebDriverException as e:
            raise Exception(f"WebDriver error during browser search: {str(e)}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

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
                elif response.status == 429:
                    raise Exception(f"SerpAPI rate limit exceeded (429)")
                elif response.status == 503:
                    raise Exception(f"SerpAPI service unavailable (503)")
                elif response.status == 402:
                    raise Exception(f"SerpAPI quota exceeded (402)")
                else:
                    raise Exception(f"SerpAPI search failed with status {response.status}")
        except aiohttp.ClientError as e:
            await self.logger.error(
                f"SerpAPI connection error",
                tool_id=self.tool_id,
                error=str(e)
            )
            raise Exception(f"SerpAPI connection error: {str(e)}")
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
                    "User-Agent": random.choice(self.user_agents)
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
                elif response.status == 429:
                    raise Exception(f"DuckDuckGo rate limit exceeded (429)")
                elif response.status == 503:
                    raise Exception(f"DuckDuckGo service unavailable (503)")
                elif response.status == 403:
                    raise Exception(f"DuckDuckGo access forbidden - possible IP blocking (403)")
                else:
                    raise Exception(f"DuckDuckGo search failed with status {response.status}")
        except aiohttp.ClientError as e:
            await self.logger.error(
                f"DuckDuckGo connection error",
                tool_id=self.tool_id,
                error=str(e)
            )
            raise Exception(f"DuckDuckGo connection error: {str(e)}")
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
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass 