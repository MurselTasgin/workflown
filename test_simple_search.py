#!/usr/bin/env python3
"""
Simple test for DuckDuckGo search with different queries
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from examples.tools.web_search_tool import WebSearchTool


async def test_simple_search():
    """Test simple search with different queries."""
    print("🔍 Testing Simple DuckDuckGo Search")
    print("=" * 50)
    
    # Create tool
    tool = WebSearchTool()
    
    # Test different queries
    test_queries = [
        "python programming",
        "machine learning",
        "openai",
        "web development"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing query: '{query}' ---")
        
        params = {
            "query": query,
            "engine": "duckduckgo",
            "max_results": 3
        }
        
        try:
            result = await tool.execute(params)
            
            print(f"Success: {result.success}")
            print(f"Results count: {len(result.result) if result.success else 0}")
            
            if result.success and result.result:
                print("Results:")
                for i, item in enumerate(result.result, 1):
                    print(f"  {i}. {item.get('title', 'No title')[:60]}...")
                    print(f"     URL: {item.get('url', 'No URL')}")
            else:
                print(f"Errors: {result.errors}")
                
        except Exception as e:
            print(f"Exception: {e}")
    
    # Cleanup
    await tool.cleanup()


if __name__ == "__main__":
    asyncio.run(test_simple_search()) 