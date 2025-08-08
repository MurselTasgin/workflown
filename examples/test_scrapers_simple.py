#!/usr/bin/env python3
"""
Simple test for scrapers with new web crawler.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from toolbox.webscrapers import BeautifulSoupScraper


async def test_simple_scraper():
    """Test a single scraper with the new web crawler."""
    
    print("🧪 Testing BeautifulSoup Scraper with Web Crawler")
    print("=" * 60)
    
    # Initialize scraper
    scraper = BeautifulSoupScraper()
    
    try:
        print(f"📄 Testing scraper: {scraper.name}")
        print(f"   • Available: {scraper.is_available}")
        print(f"   • Description: {scraper.description}")
        
        if scraper.is_available:
            # Test with a simple URL
            url = "https://example.com"
            print(f"\n🔍 Crawling: {url}")
            
            result = await scraper.extract_content(
                url=url,
                extract_links=True,
                extract_images=True
            )
            
            print(f"   ✅ Success!")
            print(f"   • Title: {result.title}")
            print(f"   • Content length: {len(result.content)}")
            print(f"   • Markdown length: {len(result.markdown_content)}")
            print(f"   • Links found: {len(result.links)}")
            print(f"   • Images found: {len(result.images)}")
            print(f"   • Extraction method: {result.metadata.get('extraction_method', 'unknown')}")
            
            # Show first few links
            if result.links:
                print(f"   • First 3 links:")
                for i, link in enumerate(result.links[:3]):
                    print(f"     {i+1}. {link}")
            
            # Show content snippet
            if result.content:
                snippet = result.content[:200].replace('\n', ' ').strip()
                if len(result.content) > 200:
                    snippet += "..."
                print(f"   • Content snippet: {snippet}")
            
            # Cleanup
            await scraper.cleanup()
            print(f"   ✅ Cleanup completed")
            
        else:
            print(f"   ❌ Scraper not available")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if scraper:
            await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(test_simple_scraper()) 