#!/usr/bin/env python3
"""
Debug script to test scraper selection.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from toolbox.webscrapers import ScraperManager


async def test_scraper_selection():
    """Test which scraper is selected for a real URL."""
    
    # Initialize scraper manager
    manager = ScraperManager()
    
    # Test with a real URL
    test_url = "https://techvify.com/best-artificial-intelligence-framework/"
    
    print(f"🧪 Testing scraper selection with URL: {test_url}")
    
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
    asyncio.run(test_scraper_selection()) 