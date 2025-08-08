#!/usr/bin/env python3
"""
Test script for the web crawler module.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from toolbox.webscrapers import WebCrawler, CrawlConfig, CrawlStrategy, crawl_url, crawl_urls


async def test_single_page_crawl():
    """Test crawling a single page."""
    
    print("🕷️ Testing Single Page Crawl")
    print("=" * 50)
    
    url = "https://www.akbank.com"
    
    print(f"📄 Crawling: {url}")
    
    # Test with default config
    page = await crawl_url(url)
    
    print(f"   ✅ Success!")
    print(f"   • Title: {page.title}")
    print(f"   • Status Code: {page.status_code}")
    print(f"   • Content Length: {page.content_length}")
    print(f"   • Links Found: {len(page.links)}")
    print(f"   • Images Found: {len(page.images)}")
    print(f"   • Depth: {page.depth}")
    
    if page.error:
        print(f"   • Error: {page.error}")
    
    # Show first few links
    if page.links:
        print(f"   • First 3 links:")
        for i, link in enumerate(page.links[:3]):
            print(f"     {i+1}. {link}")


async def test_multi_page_crawl():
    """Test crawling multiple pages."""
    
    print("\n🕷️ Testing Multi-Page Crawl")
    print("=" * 50)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html"
    ]
    
    print(f"📄 Crawling {len(urls)} pages:")
    for url in urls:
        print(f"   • {url}")
    
    # Test with custom config
    config = CrawlConfig(
        max_pages=5,
        max_depth=2,
        request_delay=0.5,
        timeout=15
    )
    
    result = await crawl_urls(urls, follow_links=False, config=config)
    
    print(f"\n📊 Crawl Results:")
    print(f"   • Total Pages: {result.total_pages}")
    print(f"   • Successful: {result.successful_pages}")
    print(f"   • Failed: {result.failed_pages}")
    print(f"   • Total Links Found: {result.total_links_found}")
    print(f"   • Total Images Found: {result.total_images_found}")
    print(f"   • Crawl Time: {result.crawl_time:.2f} seconds")
    
    # Show details for each page
    for i, page in enumerate(result.pages):
        print(f"\n   📄 Page {i+1}: {page.url}")
        print(f"      • Title: {page.title}")
        print(f"      • Status: {page.status_code}")
        print(f"      • Content Length: {page.content_length}")
        print(f"      • Links: {len(page.links)}")
        print(f"      • Images: {len(page.images)}")
        print(f"      • Depth: {page.depth}")
        if page.error:
            print(f"      • Error: {page.error}")


async def test_link_following():
    """Test crawling with link following."""
    
    print("\n🕷️ Testing Link Following")
    print("=" * 50)
    
    start_urls = ["https://www.akbank.com"]
    
    print(f"📄 Starting from: {start_urls[0]}")
    print(f"🔗 Following links with limits...")
    
    # Test with link following
    config = CrawlConfig(
        max_pages=3,
        max_depth=1,
        request_delay=1.0,
        timeout=15,
        strategy=CrawlStrategy.BREADTH_FIRST
    )
    
    result = await crawl_urls(start_urls, follow_links=True, config=config)
    
    print(f"\n📊 Link Following Results:")
    print(f"   • Total Pages: {result.total_pages}")
    print(f"   • Successful: {result.successful_pages}")
    print(f"   • Failed: {result.failed_pages}")
    print(f"   • Total Links Found: {result.total_links_found}")
    print(f"   • Total Images Found: {result.total_images_found}")
    print(f"   • Crawl Time: {result.crawl_time:.2f} seconds")
    
    # Show pages by depth
    pages_by_depth = {}
    for page in result.pages:
        depth = page.depth
        if depth not in pages_by_depth:
            pages_by_depth[depth] = []
        pages_by_depth[depth].append(page)
    
    for depth in sorted(pages_by_depth.keys()):
        pages = pages_by_depth[depth]
        print(f"\n   📄 Depth {depth} ({len(pages)} pages):")
        for page in pages:
            print(f"      • {page.url} - {page.title}")


async def test_crawler_with_context_manager():
    """Test using the crawler as a context manager."""
    
    print("\n🕷️ Testing Context Manager")
    print("=" * 50)
    
    config = CrawlConfig(
        max_pages=2,
        request_delay=0.5,
        timeout=15
    )
    
    async with WebCrawler(config) as crawler:
        print(f"📄 Crawling with context manager...")
        
        page = await crawler.crawl_single_page("https://www.akbank.com")
        
        print(f"   ✅ Success!")
        print(f"   • Title: {page.title}")
        print(f"   • Status Code: {page.status_code}")
        print(f"   • Content Length: {page.content_length}")
        print(f"   • Links Found: {len(page.links)}")
        print(f"   • Images Found: {len(page.images)}")
    
    print(f"   ✅ Context manager cleanup completed")


async def test_custom_config():
    """Test custom crawler configuration."""
    
    print("\n🕷️ Testing Custom Configuration")
    print("=" * 50)
    
    # Custom configuration
    config = CrawlConfig(
        max_pages=3,
        max_depth=2,
        max_concurrent_requests=2,
        request_delay=0.5,
        timeout=10,
        strategy=CrawlStrategy.DEPTH_FIRST,
        allowed_domains=["example.com"],
        excluded_paths=["/admin", "/private"],
        user_agents=[
            "CustomBot/1.0",
            "TestCrawler/1.0"
        ]
    )
    
    print(f"📋 Custom Config:")
    print(f"   • Max Pages: {config.max_pages}")
    print(f"   • Max Depth: {config.max_depth}")
    print(f"   • Max Concurrent: {config.max_concurrent_requests}")
    print(f"   • Request Delay: {config.request_delay}s")
    print(f"   • Strategy: {config.strategy.value}")
    print(f"   • Allowed Domains: {config.allowed_domains}")
    print(f"   • Excluded Paths: {config.excluded_paths}")
    
    result = await crawl_urls(
        ["https://www.akbank.com"], 
        follow_links=True, 
        config=config
    )
    
    print(f"\n📊 Results with Custom Config:")
    print(f"   • Total Pages: {result.total_pages}")
    print(f"   • Successful: {result.successful_pages}")
    print(f"   • Failed: {result.failed_pages}")
    print(f"   • Crawl Time: {result.crawl_time:.2f} seconds")


async def main():
    """Run all tests."""
    
    print("🕷️ Web Crawler Test Suite")
    print("=" * 60)
    
    try:
        await test_single_page_crawl()
        await test_multi_page_crawl()
        await test_link_following()
        await test_crawler_with_context_manager()
        await test_custom_config()
        
        print(f"\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 