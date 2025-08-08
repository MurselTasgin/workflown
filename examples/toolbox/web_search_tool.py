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
- googlesearch-python: For Google search functionality

Install dependencies: pip install googlesearch-python
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
import time
import random
import logging
from datetime import datetime, timedelta

from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability

# Import the GoogleSearchPythonTool from websearch module
from .websearch.googlesearch_python_search import GoogleSearchPythonTool

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
    Tool for performing web searches using Google Search Python library.
    
    Wraps the GoogleSearchPythonTool for easy integration with the workflow system.
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
            description="Performs web searches using Google Search Python library",
            capabilities=[ToolCapability.WEB_SEARCH],
            config=config or {}
        )
        
        # Configuration
        self.default_engine = self.config.get("default_engine", "google")
        self.max_results = self.config.get("max_results", 10)
        self.language = self.config.get("language", "en")
        self.region = self.config.get("region", "US")
        
        # Google search tool will be initialized in _initialize()
        self.google_search_tool = None
        self._initialize()

    def _initialize(self):
        """Initialize the Google Search Python tool."""
        # Initialize the Google Search Python tool
        self.google_search_tool = GoogleSearchPythonTool(
            tool_id=f"{self.tool_id}_google",
            config=self.config
        )
        self.google_search_tool._initialize()
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute web search with given parameters.
        
        Args:
            parameters: Search parameters including:
                - query: Search query string
                - engine: Search engine to use (optional, defaults to google)
                - max_results: Maximum number of results (default: 10)
                - language: Language for search (optional)
                - region: Region for search (optional)
                
        Returns:
            ToolResult with search results
        """
        # Ensure the google search tool is initialized
        if self.google_search_tool is None:
            self._initialize()
        
        query = parameters.get("query", "")
        if not query:
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=["No search query provided"]
            )
        
        engine = parameters.get("engine", self.default_engine)
        max_results = parameters.get("max_results", self.max_results)
        language = parameters.get("language", self.language)
        region = parameters.get("region", self.region)
        
        await self.logger.info(
            f"Starting web search",
            tool_id=self.tool_id,
            query=query,
            engine=engine,
            max_results=max_results
        )
        
        try:
            # Use the Google Search Python tool to perform the search
            search_parameters = {
                "query": query,
                "max_results": max_results,
                "language": language,
                "region": region
            }
            
            # Execute the search using the Google Search Python tool
            search_result = await self.google_search_tool.execute(search_parameters)
            
            if not search_result.success:
                return ToolResult(
                    tool_id=self.tool_id,
                    success=False,
                    result=None,
                    errors=search_result.errors
                )
            
            # Convert SearchResult objects to dictionaries
            results = []
            if isinstance(search_result.result, list):
                for result in search_result.result:
                    if hasattr(result, 'to_dict'):
                        results.append(result.to_dict())
                    else:
                        results.append(result)
            else:
                results = search_result.result
            
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
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operations."""
        return ["web_search", "search", "find"]
    
    def get_version(self) -> str:
        """Get tool version."""
        return "1.0.0"
    
    def get_author(self) -> str:
        """Get tool author."""
        return "Workflown Team"
    
    def get_tags(self) -> List[str]:
        """Get tool tags for categorization."""
        return ["web_search", "search", "google", "googlesearch_python"]
    
    def _get_required_parameters(self) -> List[str]:
        """Get required parameters."""
        return ["query"]
    
    def _get_optional_parameters(self) -> List[str]:
        """Get optional parameters."""
        return ["engine", "max_results", "language", "region"]
    
    def _get_parameter_descriptions(self) -> Dict[str, str]:
        """Get parameter descriptions."""
        return {
            "query": "Search query to execute",
            "engine": "Search engine to use (google)",
            "max_results": "Maximum number of results to return",
            "language": "Language for search results",
            "region": "Region for search results"
        }
    
    def _get_parameter_types(self) -> Dict[str, str]:
        """Get parameter types."""
        return {
            "query": "string",
            "engine": "string",
            "max_results": "integer",
            "language": "string",
            "region": "string"
        }
    
    async def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'google_search_tool') and self.google_search_tool is not None:
            await self.google_search_tool.cleanup() 

    # ------------------------------------------------------------------
    # Result display override
    # ------------------------------------------------------------------
    def _display_result_body(self, result: Any, context: Optional[Dict[str, Any]] = None) -> None:
        print("🔍 WEB SEARCH RESULTS:")
        if isinstance(result, list):
            print(f"   • Found {len(result)} URLs")
            for i, search_result in enumerate(result[:5]):
                if isinstance(search_result, dict):
                    url = search_result.get("url", "Unknown URL")
                    title = search_result.get("title", "No title")
                    snippet = search_result.get("snippet", "")
                    print(f"   📄 {i+1}. {title[:60]}...")
                    print(f"      URL: {url}")
                    if snippet:
                        print(f"      Snippet: {snippet[:100]}...")
                else:
                    print(f"   📄 {i+1}. {search_result}")
        elif isinstance(result, dict):
            if "result" in result and isinstance(result["result"], list):
                results = result["result"]
                print(f"   • Found {len(results)} URLs")
                for i, search_result in enumerate(results[:5]):
                    if isinstance(search_result, dict):
                        url = search_result.get("url", "Unknown URL")
                        title = search_result.get("title", "No title")
                        print(f"   📄 {i+1}. {title[:60]}...")
                        print(f"      URL: {url}")
            else:
                print(f"   • Search completed successfully")
                print(f"   • Result: {result}")
        else:
            print(f"   • Result: {result}")