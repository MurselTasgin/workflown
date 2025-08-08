#!/usr/bin/env python3
"""
Demo script for Firecrawl scraper - shows how it would work with proper setup.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from toolbox.webscrapers.firecrawl_scraper import FirecrawlScraper
from toolbox.webscrapers.beautifulsoup_scraper import BeautifulSoupScraper


async def demo_scraper_differences():
    """Demo the differences between local and API-based scrapers."""
    
    print("🔥 Scraper Architecture Demo")
    print("=" * 50)
    
    # Test HTML content
    test_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test page with some content.</p>
            <a href="https://example.com">Link</a>
            <img src="https://example.com/image.jpg" />
        </body>
    </html>
    """
    
    test_url = "https://example.com"
    
    print(f"\n📋 Test Setup:")
    print(f"   • HTML Content: {len(test_html)} characters")
    print(f"   • URL: {test_url}")
    
    # Test BeautifulSoup (local scraper)
    print(f"\n🔧 BeautifulSoup Scraper (Local):")
    print(f"   • Type: Local HTML parser")
    print(f"   • Uses: Pre-fetched HTML content")
    print(f"   • Process: Parses provided HTML")
    
    bs_scraper = BeautifulSoupScraper()
    if bs_scraper.is_available:
        try:
            result = await bs_scraper.extract_content(
                html_content=test_html,
                url=test_url,
                extract_links=True,
                extract_images=True
            )
            print(f"   ✅ Success!")
            print(f"   • Content length: {len(result.content)}")
            print(f"   • Links found: {len(result.links)}")
            print(f"   • Images found: {len(result.images)}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
    else:
        print(f"   ❌ Not available")
    
    # Test Firecrawl (API-based scraper)
    print(f"\n🔥 Firecrawl Scraper (API-based):")
    print(f"   • Type: API-based content fetcher")
    print(f"   • Uses: Direct URL access via API")
    print(f"   • Process: Ignores HTML content, fetches from URL")
    
    firecrawl_scraper = FirecrawlScraper(api_key="demo_key")
    print(f"   • Available: {firecrawl_scraper.is_available}")
    print(f"   • API Key Configured: {firecrawl_scraper.get_capabilities().get('api_key_configured', False)}")
    print(f"   • Client Initialized: {firecrawl_scraper.get_capabilities().get('client_initialized', False)}")
    
    print(f"\n📋 Key Differences:")
    print(f"   • Local scrapers (BeautifulSoup, Trafilatura, etc.):")
    print(f"     - Receive pre-fetched HTML content")
    print(f"     - Parse the HTML to extract content")
    print(f"     - More efficient (no duplicate HTTP requests)")
    print(f"     - Work offline with provided HTML")
    print(f"   • API-based scrapers (Firecrawl):")
    print(f"     - Ignore provided HTML content")
    print(f"     - Fetch content directly from URL via API")
    print(f"     - Higher quality extraction (server-side processing)")
    print(f"     - Require API key and internet connection")
    
    print(f"\n📋 Setup Instructions:")
    print(f"   1. Install firecrawl: pip install firecrawl")
    print(f"   2. Add FIRECRAWL_API_KEY to your .env file:")
    print(f"      FIRECRAWL_API_KEY=your_api_key_here")
    print(f"   3. The scraper will automatically be used as the preferred option")
    print(f"   4. It will extract high-quality content with markdown support")


if __name__ == "__main__":
    asyncio.run(demo_scraper_differences()) 