#!/usr/bin/env python3
"""
Search, Scrape, and Summarize Integration Test

This test demonstrates the complete workflow:
1. Search for content using GoogleSearchPython tool
2. Extract top 5 URLs from search results
3. Scrape web page content using WebPageParser tool
4. Summarize the combined content using ComposerTool (LLM)

Usage:
    python examples/test_search_scrape_summarize.py [query]

Example:
    python examples/test_search_scrape_summarize.py "Agentic AI frameworks in 2025"

Dependencies:
    pip install aiohttp beautifulsoup4 googlesearch-python
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add tools to Python path
sys.path.insert(0, str(Path(__file__).parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent / "tools" / "websearch"))


class MockLogger:
    """Mock logger for testing."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    async def info(self, message: str, **kwargs):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [INFO] {message}")
            if kwargs:
                print(f"         Details: {kwargs}")
    
    async def warning(self, message: str, **kwargs):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [WARNING] {message}")
        if kwargs:
            print(f"           Details: {kwargs}")
    
    async def error(self, message: str, **kwargs):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [ERROR] {message}")
        if kwargs:
            print(f"         Details: {kwargs}")


class SearchScrapeSummarizeTest:
    """Integration test for the complete search -> scrape -> summarize workflow."""
    
    def __init__(self, query: str, verbose: bool = True):
        self.query = query
        self.verbose = verbose
        self.logger = MockLogger(verbose)
        
        # Configuration
        self.search_config = {
            "pause_between_requests": 2.0,
            "safe": "off",
            "max_retries": 2
        }
        
        self.scraper_config = {
            "request_timeout": 15,
            "max_content_length": 500000,  # 500KB per page
            "rate_limit_delay": 1.5,
            "max_retries": 2,
            "min_content_length": 200
        }
        
        self.composer_config = {
            "provider": "mock",
            "model": "mock-llm",
            "max_tokens": 3000,
            "temperature": 0.7
        }
    
    async def run_complete_workflow(self) -> Dict[str, Any]:
        """Run the complete search -> scrape -> summarize workflow."""
        print(f"🔍 Starting Search-Scrape-Summarize Workflow")
        print(f"=" * 60)
        print(f"Query: '{self.query}'")
        print(f"=" * 60)
        
        workflow_start = time.time()
        results = {
            "query": self.query,
            "started_at": datetime.now().isoformat(),
            "steps": {}
        }
        
        try:
            # Step 1: Search for content
            print(f"\n📝 Step 1: Searching for content...")
            search_results = await self._perform_search()
            results["steps"]["search"] = search_results
            
            if not search_results["success"] or not search_results.get("urls"):
                print(f"❌ Search failed or returned no URLs")
                return results
            
            # Step 2: Scrape web pages
            print(f"\n🕷️  Step 2: Scraping web pages...")
            scraping_results = await self._scrape_pages(search_results["urls"])
            results["steps"]["scraping"] = scraping_results
            
            if not scraping_results["success"] or not scraping_results.get("pages"):
                print(f"❌ Scraping failed or returned no content")
                return results
            
            # Step 3: Summarize content
            print(f"\n🤖 Step 3: Summarizing with LLM...")
            summary_results = await self._summarize_content(scraping_results["pages"])
            results["steps"]["summary"] = summary_results
            
            # Final results
            workflow_time = time.time() - workflow_start
            results["completed_at"] = datetime.now().isoformat()
            results["total_time"] = workflow_time
            results["success"] = all([
                search_results["success"],
                scraping_results["success"], 
                summary_results["success"]
            ])
            
            # Display final summary
            self._display_final_results(results)
            
            # Save results to file
            await self._save_results(results)
            
            return results
            
        except Exception as e:
            print(f"\n💥 Workflow failed with error: {str(e)}")
            results["error"] = str(e)
            results["success"] = False
            return results
    
    async def _perform_search(self) -> Dict[str, Any]:
        """Perform web search to get URLs."""
        step_start = time.time()
        
        try:
            from googlesearch_python_search import GoogleSearchPythonTool
            
            # Initialize search tool
            search_tool = GoogleSearchPythonTool(config=self.search_config)
            search_tool.logger = self.logger
            
            # Perform search
            result = await search_tool.execute({
                "query": self.query,
                "max_results": 5,
                "language": "en",
                "region": "US"
            })
            
            elapsed = time.time() - step_start
            
            if result.success and result.result:
                urls = [item["url"] for item in result.result if item.get("url")]
                
                print(f"✅ Search completed in {elapsed:.2f}s")
                print(f"   Found {len(urls)} URLs:")
                for i, url in enumerate(urls, 1):
                    print(f"   {i}. {url}")
                
                return {
                    "success": True,
                    "urls": urls,
                    "search_metadata": result.metadata,
                    "elapsed_time": elapsed,
                    "raw_results": result.result
                }
            else:
                errors = result.errors if result.errors else ["Unknown search error"]
                print(f"❌ Search failed in {elapsed:.2f}s: {errors[0]}")
                
                return {
                    "success": False,
                    "urls": [],
                    "errors": errors,
                    "elapsed_time": elapsed
                }
                
        except ImportError:
            error = "googlesearch-python not available. Install with: pip install googlesearch-python"
            print(f"❌ {error}")
            return {"success": False, "urls": [], "errors": [error], "elapsed_time": 0}
        
        except Exception as e:
            elapsed = time.time() - step_start
            error = f"Search error: {str(e)}"
            print(f"❌ {error} (after {elapsed:.2f}s)")
            return {"success": False, "urls": [], "errors": [error], "elapsed_time": elapsed}
    
    async def _scrape_pages(self, urls: List[str]) -> Dict[str, Any]:
        """Scrape content from web pages."""
        step_start = time.time()
        
        try:
            from webpage_parser import WebPageParserTool
            
            # Initialize scraper tool
            scraper_tool = WebPageParserTool(config=self.scraper_config)
            scraper_tool.logger = self.logger
            
            # Scrape all URLs
            result = await scraper_tool.execute({
                "urls": urls,
                "extract_links": False,
                "extract_images": False,
                "strategy": "auto"
            })
            
            elapsed = time.time() - step_start
            
            if result.success and result.result:
                pages = result.result
                valid_pages = [p for p in pages if not p.get('metadata', {}).get('error') and len(p.get('content', '')) >= 200]
                
                print(f"✅ Scraping completed in {elapsed:.2f}s")
                print(f"   Processed {len(pages)} pages, {len(valid_pages)} with valid content:")
                
                for i, page in enumerate(valid_pages, 1):
                    title = page.get('title', 'Untitled')[:50]
                    content_len = len(page.get('content', ''))
                    print(f"   {i}. {title}... ({content_len} chars)")
                
                return {
                    "success": True,
                    "pages": valid_pages,
                    "total_pages": len(pages),
                    "valid_pages": len(valid_pages),
                    "scraping_metadata": result.metadata,
                    "elapsed_time": elapsed
                }
            else:
                errors = result.errors if result.errors else ["Unknown scraping error"]
                print(f"❌ Scraping failed in {elapsed:.2f}s: {errors[0]}")
                
                return {
                    "success": False,
                    "pages": [],
                    "errors": errors,
                    "elapsed_time": elapsed
                }
                
        except Exception as e:
            elapsed = time.time() - step_start
            error = f"Scraping error: {str(e)}"
            print(f"❌ {error} (after {elapsed:.2f}s)")
            return {"success": False, "pages": [], "errors": [error], "elapsed_time": elapsed}
    
    async def _summarize_content(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize scraped content using LLM."""
        step_start = time.time()
        
        try:
            from composer_tool import ComposerTool
            
            # Initialize composer tool
            composer_tool = ComposerTool(config=self.composer_config)
            composer_tool.logger = self.logger
            
            # Perform summarization
            result = await composer_tool.execute({
                "task": "combine",
                "content": pages,
                "query": self.query,
                "format": "text",
                "include_sources": True
            })
            
            elapsed = time.time() - step_start
            
            if result.success and result.result:
                summary = result.result
                word_count = len(summary.split())
                
                print(f"✅ Summarization completed in {elapsed:.2f}s")
                print(f"   Generated summary: {word_count} words")
                
                return {
                    "success": True,
                    "summary": summary,
                    "word_count": word_count,
                    "composition_metadata": result.metadata,
                    "elapsed_time": elapsed
                }
            else:
                errors = result.errors if result.errors else ["Unknown summarization error"]
                print(f"❌ Summarization failed in {elapsed:.2f}s: {errors[0]}")
                
                return {
                    "success": False,
                    "summary": "",
                    "errors": errors,
                    "elapsed_time": elapsed
                }
                
        except Exception as e:
            elapsed = time.time() - step_start
            error = f"Summarization error: {str(e)}"
            print(f"❌ {error} (after {elapsed:.2f}s)")
            return {"success": False, "summary": "", "errors": [error], "elapsed_time": elapsed}
    
    def _display_final_results(self, results: Dict[str, Any]):
        """Display the final workflow results."""
        print(f"\n{'=' * 60}")
        print(f"🎯 WORKFLOW RESULTS")
        print(f"{'=' * 60}")
        
        # Summary statistics
        total_time = results.get("total_time", 0)
        success = results.get("success", False)
        
        print(f"Query: {results['query']}")
        print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Total Time: {total_time:.2f} seconds")
        print()
        
        # Step breakdown
        steps = results.get("steps", {})
        
        search_step = steps.get("search", {})
        scraping_step = steps.get("scraping", {})
        summary_step = steps.get("summary", {})
        
        print(f"📊 Step Breakdown:")
        print(f"   1. Search:     {search_step.get('elapsed_time', 0):.2f}s - {'✅' if search_step.get('success') else '❌'}")
        print(f"   2. Scraping:   {scraping_step.get('elapsed_time', 0):.2f}s - {'✅' if scraping_step.get('success') else '❌'}")
        print(f"   3. Summary:    {summary_step.get('elapsed_time', 0):.2f}s - {'✅' if summary_step.get('success') else '❌'}")
        print()
        
        # Content statistics
        urls_found = len(search_step.get("urls", []))
        pages_scraped = scraping_step.get("valid_pages", 0)
        summary_words = summary_step.get("word_count", 0)
        
        print(f"📈 Content Statistics:")
        print(f"   URLs found:    {urls_found}")
        print(f"   Pages scraped: {pages_scraped}")
        print(f"   Summary words: {summary_words}")
        print()
        
        # Display summary if available  
        if success and summary_step.get("summary"):
            print(f"📋 GENERATED SUMMARY:")
            print(f"{'─' * 60}")
            summary = summary_step["summary"]
            
            # Display first 1000 characters with proper formatting
            if len(summary) > 1000:
                display_summary = summary[:1000] + "\\n\\n[Summary truncated for display...]"
            else:
                display_summary = summary
            
            print(display_summary)
            print(f"{'─' * 60}")
        
        # Display errors if any
        all_errors = []
        for step_name, step_data in steps.items():
            if step_data.get("errors"):
                all_errors.extend([f"{step_name}: {err}" for err in step_data["errors"]])
        
        if all_errors:
            print(f"⚠️  ERRORS ENCOUNTERED:")
            for error in all_errors:
                print(f"   • {error}")
    
    async def _save_results(self, results: Dict[str, Any]):
        """Save results to JSON file."""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c for c in self.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_query = safe_query.replace(' ', '_')[:30]
            
            filename = f"search_scrape_summary_{safe_query}_{timestamp}.json"
            filepath = Path(__file__).parent / filename
            
            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\\n💾 Results saved to: {filepath}")
            
        except Exception as e:
            print(f"\\n⚠️  Failed to save results: {str(e)}")


async def main():
    """Main function to run the integration test."""
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Agentic AI frameworks in 2025"
    
    print(f"🚀 Search-Scrape-Summarize Integration Test")
    print(f"Query: '{query}'")
    print()
    
    # Run the test
    test = SearchScrapeSummarizeTest(query, verbose=True)
    
    try:
        results = await test.run_complete_workflow()
        
        if results.get("success"):
            print(f"\\n🎉 Integration test completed successfully!")
            return 0
        else:
            print(f"\\n❌ Integration test failed.")
            return 1
            
    except KeyboardInterrupt:
        print(f"\\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\\n💥 Test failed with unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())