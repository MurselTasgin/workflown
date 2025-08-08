#!/usr/bin/env python3
"""
Test script for Firecrawl scraper.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from toolbox.webscrapers import ScraperManager


async def test_firecrawl_scraper():
    """Test the Firecrawl scraper."""
    
    # Initialize scraper manager
    manager = ScraperManager()
    
    print("🔧 Available Scrapers:")
    for name in manager.get_available_scrapers():
        scraper = manager.get_scraper(name)
        capabilities = scraper.get_capabilities()
        print(f"   • {name}")
        print(f"     - Available: {capabilities['available']}")
        print(f"     - Supports Markdown: {capabilities['supports_markdown']}")
        if 'api_required' in capabilities:
            print(f"     - API Required: {capabilities['api_required']}")
            print(f"     - API Key Configured: {capabilities['api_key_configured']}")
            print(f"     - Client Initialized: {capabilities['client_initialized']}")
        print(f"     - Description: {capabilities['description']}")
    
    print(f"\n📊 Total available scrapers: {len(manager.get_available_scrapers())}")
    
    # Test URL
    test_url = "https://docs.firecrawl.dev/introduction"
    
    print(f"\n🧪 Testing scrapers with URL: {test_url}")
    
    # Test with best scraper
    print("\n🎯 Testing with best scraper:")
    try:
        result = await manager.extract_with_best_scraper(
            html_content="<html><head><title>Test Page</title></head><body><h1>Hello World</h1><p>This is a test page.</p></body></html>",
            url=test_url,
            extract_links=True,
            extract_images=True
        )
        print(f"   ✅ Success!")
        print(f"   • Title: {result.title}")
        print(f"   • Content length: {len(result.content)}")
        print(f"   • Markdown length: {len(result.markdown_content)}")
        print(f"   • Links: {len(result.links)}")
        print(f"   • Images: {len(result.images)}")
        print(f"   • Extraction method: {result.metadata.get('extraction_method', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
    
    # Test with all scrapers
    print("\n🔬 Testing with all scrapers:")
    try:
        results = await manager.extract_with_all_scrapers(
            html_content="<html><head><title>Test Page</title></head><body><h1>Hello World</h1><p>This is a test page.</p><a href='https://example.com'>Link</a><img src='https://example.com/image.jpg' /></body></html>",
            url=test_url,
            extract_links=True,
            extract_images=True
        )
        
        for scraper_name, result in results.items():
            print(f"   📄 {scraper_name}:")
            print(f"      • Title: {result.title}")
            print(f"      • Content length: {len(result.content)}")
            print(f"      • Markdown length: {len(result.markdown_content)}")
            print(f"      • Links: {len(result.links)}")
            print(f"      • Images: {len(result.images)}")
            print(f"      • Method: {result.metadata.get('extraction_method', 'unknown')}")
            if result.metadata.get('error'):
                print(f"      • Error: {result.metadata['error']}")
    
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_firecrawl_scraper()) 