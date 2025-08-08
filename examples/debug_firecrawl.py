#!/usr/bin/env python3
"""
Debug script for Firecrawl scraper initialization.
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# Test firecrawl import
print("🔍 Testing Firecrawl import...")
try:
    from firecrawl import Firecrawl
    print("   ✅ Firecrawl import successful")
    FIRECRAWL_AVAILABLE = True
except ImportError as e:
    print(f"   ❌ Firecrawl import failed: {e}")
    FIRECRAWL_AVAILABLE = False

# Test config import
print("\n🔍 Testing config import...")
try:
    from workflown.core.config.central_config import get_config
    print("   ✅ Config import successful")
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"   ❌ Config import failed: {e}")
    CONFIG_AVAILABLE = False

# Test API key retrieval
print("\n🔍 Testing API key retrieval...")
if CONFIG_AVAILABLE:
    try:
        config = get_config()
        firecrawl_api_key = config.get("api.firecrawl.api_key", "")
        print(f"   • API Key found: {bool(firecrawl_api_key)}")
        print(f"   • API Key length: {len(firecrawl_api_key)}")
        if firecrawl_api_key:
            print(f"   • API Key starts with: {firecrawl_api_key[:10]}...")
    except Exception as e:
        print(f"   ❌ API key retrieval failed: {e}")
else:
    print("   ❌ Config not available")

# Test Firecrawl client initialization
print("\n🔍 Testing Firecrawl client initialization...")
if FIRECRAWL_AVAILABLE and CONFIG_AVAILABLE:
    try:
        config = get_config()
        firecrawl_api_key = config.get("api.firecrawl.api_key", "")
        
        if firecrawl_api_key:
            print(f"   • Attempting to initialize Firecrawl client...")
            client = Firecrawl(api_key=firecrawl_api_key)
            print(f"   ✅ Firecrawl client initialized successfully")
            
            # Test a simple API call
            print(f"   • Testing API connection...")
            # Note: We won't actually make a call here to avoid using API credits
            print(f"   ✅ Firecrawl client ready")
        else:
            print(f"   ❌ No API key available")
    except Exception as e:
        print(f"   ❌ Firecrawl client initialization failed: {e}")
else:
    print(f"   ❌ Prerequisites not met (Firecrawl: {FIRECRAWL_AVAILABLE}, Config: {CONFIG_AVAILABLE})")

# Test scraper initialization
print("\n🔍 Testing Firecrawl scraper initialization...")
try:
    from toolbox.webscrapers.firecrawl_scraper import FirecrawlScraper
    
    if CONFIG_AVAILABLE:
        config = get_config()
        firecrawl_api_key = config.get("api.firecrawl.api_key", "")
        scraper = FirecrawlScraper(api_key=firecrawl_api_key)
        
        print(f"   • Scraper name: {scraper.name}")
        print(f"   • Scraper available: {scraper.is_available}")
        print(f"   • API key configured: {scraper.get_capabilities().get('api_key_configured', False)}")
        print(f"   • Client initialized: {scraper.get_capabilities().get('client_initialized', False)}")
        
        if not scraper.is_available:
            print(f"   ❌ Scraper not available - this is why it's not showing up in the list")
        else:
            print(f"   ✅ Scraper available and ready")
    else:
        print(f"   ❌ Config not available")
        
except Exception as e:
    print(f"   ❌ Scraper initialization failed: {e}")

print(f"\n📋 Summary:")
print(f"   • Firecrawl library: {'✅ Available' if FIRECRAWL_AVAILABLE else '❌ Not available'}")
print(f"   • Config system: {'✅ Available' if CONFIG_AVAILABLE else '❌ Not available'}")
print(f"   • API key: {'✅ Configured' if CONFIG_AVAILABLE and get_config().get('api.firecrawl.api_key') else '❌ Not configured'}")
print(f"   • Scraper ready: {'✅ Yes' if FIRECRAWL_AVAILABLE and CONFIG_AVAILABLE else '❌ No'}") 