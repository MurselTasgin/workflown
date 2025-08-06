#!/usr/bin/env python3
"""
Comprehensive Test Suite for WebSearch Tools

Tests all web search implementations with the query "Agentic AI frameworks in 2025":
- DuckDuckGo Search
- Google Classic Search (API-based)
- Google Selenium Search (Browser-based)
- Google Search Python Library

Usage:
    python examples/test_websearch_tools.py

Dependencies:
    pip install aiohttp selenium googlesearch-python webdriver-manager
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the websearch tools to Python path
sys.path.insert(0, str(Path(__file__).parent / "tools" / "websearch"))
sys.path.insert(0, str(Path(__file__).parent / "tools"))

# Test query
TEST_QUERY = "Agentic AI frameworks in 2025"


class MockLogger:
    """Mock logger for testing."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    async def info(self, message: str, **kwargs):
        if self.verbose:
            print(f"[INFO] {message} | {self._format_kwargs(kwargs)}")
    
    async def warning(self, message: str, **kwargs):
        if self.verbose:
            print(f"[WARNING] {message} | {self._format_kwargs(kwargs)}")
    
    async def error(self, message: str, **kwargs):
        print(f"[ERROR] {message} | {self._format_kwargs(kwargs)}")
    
    def _format_kwargs(self, kwargs: dict) -> str:
        if not kwargs:
            return ""
        return " | ".join([f"{k}={v}" for k, v in kwargs.items()])


class WebSearchTestSuite:
    """Comprehensive test suite for web search tools."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = MockLogger(verbose)
        self.test_results = []
        
        # Test configuration
        self.test_config = {
            "rate_limit_delay": 1.0,
            "max_retries": 2,
            "exponential_backoff_base": 1.5,
            "max_backoff_delay": 10.0,
            "jitter_range": 0.1
        }
    
    async def run_all_tests(self):
        """Run all web search tool tests."""
        print(f"🔍 WebSearch Tools Test Suite")
        print(f"=" * 60)
        print(f"Test Query: '{TEST_QUERY}'")
        print(f"=" * 60)
        
        # Test each search tool
        await self._test_duckduckgo()
        await self._test_google_classic()
        #await self._test_google_selenium()
        await self._test_googlesearch_python()
        
        # Print summary
        self._print_summary()
        
        return self.test_results
    
    async def _test_duckduckgo(self):
        """Test DuckDuckGo search tool."""
        print(f"\n{'=' * 60}")
        print(f"🦆 Testing DuckDuckGo Search Tool")
        print(f"{'=' * 60}")
        
        try:
            from tools.websearch.duckduckgo_search import DuckDuckGoSearchTool
            
            tool = DuckDuckGoSearchTool(config=self.test_config)
            tool.logger = self.logger
            
            result = await self._run_search_test(
                tool=tool,
                engine_name="DuckDuckGo",
                query=TEST_QUERY,
                expected_features={
                    "provides_titles": True,
                    "provides_urls": True,
                    "provides_snippets": True,
                    "api_key_required": False
                }
            )
            
            await tool.cleanup()
            
        except ImportError as e:
            result = self._create_error_result("DuckDuckGo", f"Import error: {e}")
        except Exception as e:
            result = self._create_error_result("DuckDuckGo", f"Test error: {e}")
        
        self.test_results.append(result)
    
    async def _test_google_classic(self):
        """Test Google Classic Search tool (API-based)."""
        print(f"\n{'=' * 60}")
        print(f"🔍 Testing Google Classic Search Tool (API)")
        print(f"{'=' * 60}")
        
        try:
            from tools.websearch.google_classic_search import GoogleClassicSearchTool
            
            # Check if API keys are available
            google_api_key = os.getenv("GOOGLE_API_KEY")
            google_cse_id = os.getenv("GOOGLE_CSE_ID")
            serpapi_key = os.getenv("SERPAPI_KEY")
            
            if not (google_api_key and google_cse_id) and not serpapi_key:
                result = self._create_skip_result(
                    "Google Classic",
                    "No API keys configured. Set GOOGLE_API_KEY + GOOGLE_CSE_ID or SERPAPI_KEY"
                )
                self.test_results.append(result)
                return
            
            config = self.test_config.copy()
            config.update({
                "google_api_key": google_api_key,
                "google_cse_id": google_cse_id,
                "serpapi_key": serpapi_key,
                "preferred_api": "serpapi" if serpapi_key else "google"
            })
            
            tool = GoogleClassicSearchTool(config=config)
            tool.logger = self.logger
            
            # Print API status
            api_status = tool.get_api_status()
            print(f"API Status: {json.dumps(api_status, indent=2)}")
            
            result = await self._run_search_test(
                tool=tool,
                engine_name="Google Classic",
                query=TEST_QUERY,
                expected_features={
                    "provides_titles": True,
                    "provides_urls": True,
                    "provides_snippets": True,
                    "api_key_required": True,
                    "high_quality_results": True
                }
            )
            
            await tool.cleanup()
            
        except ImportError as e:
            result = self._create_error_result("Google Classic", f"Import error: {e}")
        except ValueError as e:
            result = self._create_skip_result("Google Classic", str(e))
        except Exception as e:
            result = self._create_error_result("Google Classic", f"Test error: {e}")
        
        self.test_results.append(result)
    
    async def _test_google_selenium(self):
        """Test Google Selenium search tool."""
        print(f"\n{'=' * 60}")
        print(f"🤖 Testing Google Selenium Search Tool (Browser)")
        print(f"{'=' * 60}")
        
        try:
            from tools.websearch.google_selenium_search import GoogleSeleniumSearchTool
            
            config = self.test_config.copy()
            config.update({
                "browser_type": "chrome",
                "headless": True,
                "page_load_timeout": 30,
                "element_timeout": 10
            })
            
            tool = GoogleSeleniumSearchTool(config=config)
            tool.logger = self.logger
            
            result = await self._run_search_test(
                tool=tool,
                engine_name="Google Selenium",
                query=TEST_QUERY,
                expected_features={
                    "provides_titles": True,
                    "provides_urls": True,
                    "provides_snippets": True,
                    "api_key_required": False,
                    "bypass_rate_limits": True,
                    "slower_execution": True
                },
                timeout=45  # Longer timeout for browser-based search
            )
            
            await tool.cleanup()
            
        except ImportError as e:
            result = self._create_skip_result("Google Selenium", f"Selenium not available: {e}")
        except Exception as e:
            result = self._create_error_result("Google Selenium", f"Test error: {e}")
        
        self.test_results.append(result)
    
    async def _test_googlesearch_python(self):
        """Test googlesearch-python library tool."""
        print(f"\n{'=' * 60}")
        print(f"🐍 Testing Google Search Python Library")
        print(f"{'=' * 60}")
        
        try:
            from tools.websearch.googlesearch_python_search import GoogleSearchPythonTool
            
            config = self.test_config.copy()
            config.update({
                "pause_between_requests": 2.0,
                "safe": "off",
                "ssl_verify": None,
                "region": None,
                "start_num": 0,
                "unique": False
            })
            
            tool = GoogleSearchPythonTool(config=config)
            tool.logger = self.logger
            
            # Print library info
            lib_info = tool.get_library_info()
            print(f"Library Info: {json.dumps(lib_info, indent=2)}")
            
            result = await self._run_search_test(
                tool=tool,
                engine_name="Google Search Python",
                query=TEST_QUERY,
                expected_features={
                    "provides_titles": True,  # Generated from URL
                    "provides_urls": True,
                    "provides_snippets": False,  # Library limitation
                    "api_key_required": False,
                    "simple_implementation": True,
                    "limited_features": True
                },
                timeout=30
            )
            
            await tool.cleanup()
            
        except ImportError as e:
            result = self._create_skip_result("Google Search Python", f"googlesearch-python not available: {e}")
        except Exception as e:
            result = self._create_error_result("Google Search Python", f"Test error: {e}")
        
        self.test_results.append(result)
    
    async def _run_search_test(
        self,
        tool,
        engine_name: str,
        query: str,
        expected_features: Dict[str, bool],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Run a search test for a specific tool."""
        start_time = time.time()
        
        try:
            print(f"\n🔍 Executing search: '{query}'")
            
            # Execute search with timeout
            search_task = tool.execute({
                "query": query,
                "max_results": 5,
                "language": "en",
                "region": "US"
            })
            
            result = await asyncio.wait_for(search_task, timeout=timeout)
            elapsed_time = time.time() - start_time
            
            # Analyze results
            analysis = self._analyze_search_results(result, expected_features)
            
            print(f"\n✅ Search completed successfully in {elapsed_time:.2f} seconds")
            print(f"Results found: {len(result.result) if result.result else 0}")
            
            # Display sample results
            if result.result and len(result.result) > 0:
                print(f"\n📋 Sample Results:")
                print("-" * 50)
                
                for i, res in enumerate(result.result[:5], 1):
                    print(f"{i}. Title: {res.get('title', 'N/A')[:100]}")
                    print(f"   URL: {res.get('url', 'N/A')}")
                    snippet = res.get('snippet', 'N/A')
                    if snippet and snippet != 'N/A':
                        print(f"   Snippet: {snippet[:150]}...")

                    description = res.get('description', 'N/A')
                    if description and description != 'N/A':
                        print(f"   Description: {description[:150]}...")

                    print(f"   Relevance: {res.get('relevance', 'N/A')}")
                    print()
            
            return {
                "engine": engine_name,
                "success": True,
                "results_count": len(result.result) if result.result else 0,
                "elapsed_time": elapsed_time,
                "metadata": result.metadata,
                "analysis": analysis,
                "errors": result.errors or []
            }
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"\n⏰ Search timed out after {elapsed_time:.2f} seconds")
            
            return {
                "engine": engine_name,
                "success": False,
                "results_count": 0,
                "elapsed_time": elapsed_time,
                "errors": [f"Search timed out after {timeout} seconds"],
                "analysis": {"timeout": True}
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ Search failed in {elapsed_time:.2f} seconds")
            print(f"Error: {str(e)}")
            
            return {
                "engine": engine_name,
                "success": False,
                "results_count": 0,
                "elapsed_time": elapsed_time,
                "errors": [str(e)],
                "analysis": {"exception": str(e)}
            }
    
    def _analyze_search_results(self, result, expected_features: Dict[str, bool]) -> Dict[str, Any]:
        """Analyze search results against expected features."""
        analysis = {
            "has_results": bool(result.result and len(result.result) > 0),
            "features_check": {},
            "quality_metrics": {}
        }
        
        if not result.result:
            return analysis
        
        # Check expected features
        sample_result = result.result[0] if result.result else {}
        
        analysis["features_check"] = {
            "has_titles": bool(sample_result.get("title")),
            "has_urls": bool(sample_result.get("url")),
            "has_snippets": bool(sample_result.get("snippet") and sample_result.get("snippet") != "N/A"),
            "has_descriptions": bool(sample_result.get("description") and sample_result.get("description") != "N/A"),
            "has_relevance": "relevance" in sample_result,
            "has_metadata": bool(sample_result.get("metadata"))
        }
        
        # Quality metrics
        if result.result:
            titles = [r.get("title", "") for r in result.result]
            urls = [r.get("url", "") for r in result.result]
            snippets = [r.get("snippet", "") for r in result.result]
            
            analysis["quality_metrics"] = {
                "avg_title_length": sum(len(t) for t in titles) / len(titles) if titles else 0,
                "avg_snippet_length": sum(len(s) for s in snippets) / len(snippets) if snippets else 0,
                "unique_domains": len(set(self._extract_domain(url) for url in urls if url)),
                "valid_urls": sum(1 for url in urls if url and url.startswith("http")),
                "results_with_snippets": sum(1 for s in snippets if s and s.strip())
            }
        
        return analysis
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return "unknown"
    
    def _create_error_result(self, engine_name: str, error: str) -> Dict[str, Any]:
        """Create an error result."""
        print(f"\n❌ {engine_name} test failed: {error}")
        return {
            "engine": engine_name,
            "success": False,
            "results_count": 0,
            "elapsed_time": 0,
            "errors": [error],
            "analysis": {"error": True}
        }
    
    def _create_skip_result(self, engine_name: str, reason: str) -> Dict[str, Any]:
        """Create a skip result."""
        print(f"\n⚠️  {engine_name} test skipped: {reason}")
        return {
            "engine": engine_name,
            "success": None,  # None indicates skipped
            "results_count": 0,
            "elapsed_time": 0,
            "errors": [],
            "skip_reason": reason,
            "analysis": {"skipped": True}
        }
    
    def _print_summary(self):
        """Print test summary."""
        print(f"\n{'=' * 60}")
        print(f"🎯 TEST SUMMARY")
        print(f"{'=' * 60}")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"] is True)
        failed_tests = sum(1 for r in self.test_results if r["success"] is False)
        skipped_tests = sum(1 for r in self.test_results if r["success"] is None)
        
        print(f"Total engines tested: {total_tests}")
        print(f"Successful searches: {successful_tests}")
        print(f"Failed searches: {failed_tests}")
        print(f"Skipped tests: {skipped_tests}")
        print()
        
        # Detailed results
        for result in self.test_results:
            engine = result["engine"]
            
            if result["success"] is True:
                status = "✅ SUCCESS"
                details = f"{result['results_count']} results in {result['elapsed_time']:.2f}s"
            elif result["success"] is False:
                status = "❌ FAILED"
                details = f"Error: {result['errors'][0] if result['errors'] else 'Unknown error'}"
            else:
                status = "⚠️  SKIPPED"
                details = f"Reason: {result.get('skip_reason', 'Unknown')}"
            
            print(f"{status} {engine:25} | {details}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 30)
        
        if successful_tests == 0:
            print("• No search engines worked - check internet connection and dependencies")
        else:
            working_engines = [r["engine"] for r in self.test_results if r["success"] is True]
            print(f"• Working engines: {', '.join(working_engines)}")
        
        if failed_tests > 0:
            print("• For failed engines, check error messages above")
        
        if skipped_tests > 0:
            print("• For skipped engines, install missing dependencies or configure API keys")
        
        print(f"\n🏁 Test suite completed!")


async def main():
    """Main test function."""
    test_suite = WebSearchTestSuite(verbose=True)
    
    try:
        results = await test_suite.run_all_tests()
        
        # Save results to file
        results_file = Path(__file__).parent / "websearch_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_query": TEST_QUERY,
                "timestamp": time.time(),
                "results": results
            }, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return results
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test suite interrupted by user")
        return []
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    asyncio.run(main())