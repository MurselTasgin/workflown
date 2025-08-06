#!/usr/bin/env python3
"""
Simple Search-Scrape-Summarize Test

A simplified version that uses the existing googlesearch test as a base
and adds web scraping and summarization.

Usage:
    python examples/test_simple_workflow.py
"""

import asyncio
import sys
from pathlib import Path

# Add tools to Python path
sys.path.insert(0, str(Path(__file__).parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent / "tools" / "websearch"))


class SimpleLogger:
    """Simple logger for the test."""
    
    async def info(self, message: str, **kwargs):
        print(f"[INFO] {message}")
    
    async def warning(self, message: str, **kwargs):
        print(f"[WARNING] {message}")
    
    async def error(self, message: str, **kwargs):
        print(f"[ERROR] {message}")


async def main():
    """Simple workflow test based on the existing googlesearch test."""
    
    print("🔍 Simple Search-Scrape-Summarize Workflow")
    print("=" * 50)
    
    # Initialize variables to None
    search_tool = None
    scraper = None
    composer = None
    
    try:
        # Step 1: Search (using existing logic)
        print("\\n📝 Step 1: Searching for content...")
        
        from tools.websearch.googlesearch_python_search import GoogleSearchPythonTool
        
        search_tool = GoogleSearchPythonTool()
        search_tool.logger = SimpleLogger()
        
        search_results = await search_tool.execute({
            "query": "Agentic AI frameworks in 2025", 
            "max_results": 5
        })
        
        if not search_results.success:
            print("❌ Search failed")
            return
        
        print("✅ Search completed")
        print("Found URLs:")
        
        urls = []
        for i, result in enumerate(search_results.result, 1):
            url = result['url']
            title = result['title']
            print(f"  {i}. {title}")
            print(f"     {url}")
            urls.append(url)
        
        # Step 2: Scrape top 3 URLs
        print("\\n🕷️  Step 2: Scraping web pages...")
        
        from tools.webpage_parser import WebPageParserTool
        
        scraper = WebPageParserTool({
            "request_timeout": 10,
            "max_content_length": 100000,  # 100KB limit
            "rate_limit_delay": 2.0
        })
        scraper.logger = SimpleLogger()
        
        # Take only first 3 URLs to keep test manageable
        scrape_urls = urls[:3]
        
        scrape_results = await scraper.execute({
            "urls": scrape_urls,
            "strategy": "basic"  # Use basic strategy for reliability
        })
        
        if not scrape_results.success:
            print("❌ Scraping failed")
            return
        
        print("✅ Scraping completed") 
        
        valid_pages = []
        for page in scrape_results.result:
            if not page.get('metadata', {}).get('error') and len(page.get('content', '')) > 100:
                valid_pages.append(page)
                title = page.get('title', 'No title')[:50]
                content_len = len(page.get('content', ''))
                print(f"  📄 {title}... ({content_len} chars)")
        
        if not valid_pages:
            print("❌ No valid content scraped")
            return
        
        # Step 3: Summarize
        print("\\n🤖 Step 3: Summarizing content...")
        
        from tools.composer_tool import ComposerTool
        
        composer = ComposerTool({
            "provider": "azure_openai",
            "max_tokens": 1500,
            "temperature": 0.7
        })
        composer.logger = SimpleLogger()
        
        summary_result = await composer.execute({
            "task": "combine",
            "content": valid_pages,
            "query": "Agentic AI frameworks in 2025",
            "format": "text"
        })
        
        if not summary_result.success:
            print("❌ Summarization failed")
            return
        
        print("✅ Summarization completed")
        
        # Display results
        print("\\n" + "=" * 50)
        print("📋 FINAL SUMMARY")
        print("=" * 50)
        
        summary = summary_result.result
        print(summary)
        
        print("\\n" + "=" * 50)
        print("🎉 Workflow completed successfully!")
        print(f"📊 Processed {len(valid_pages)} pages")
        print(f"📝 Generated {len(summary.split())} word summary")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install googlesearch-python beautifulsoup4")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up resources safely
        if scraper:
            try:
                await scraper.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup scraper: {e}")
        
        if search_tool:
            try:
                await search_tool.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup search_tool: {e}")
        
        if composer:
            try:
                await composer.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup composer: {e}")


if __name__ == "__main__":
    asyncio.run(main())