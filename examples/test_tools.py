"""
Test Tools

Demonstrates the usage of the tools framework with real implementations.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.logging.logger import get_logger, LogLevel
from workflown.core.logging.handlers import ConsoleHandler
from workflown.core.logging.formatters import ColoredFormatter

# Import tools
from tools import WebSearchTool, ComposerTool, tool_registry


async def setup_logging():
    """Set up logging for the test."""
    logger = get_logger("TestTools")
    
    # Add console handler
    console_handler = ConsoleHandler()
    console_handler.set_formatter(ColoredFormatter())
    logger.add_handler(console_handler)
    
    # Set log level
    logger.set_level(LogLevel.INFO)
    
    return logger


async def test_web_search_tool():
    """Test the web search tool."""
    print("\n🔍 Testing WebSearchTool")
    print("-" * 40)
    
    # Create web search tool
    web_search = WebSearchTool(
        tool_id="test_web_search",
        config={
            "rate_limit_delay": 0.5,
            "max_retries": 2
        }
    )
    
    # Test search
    search_params = {
        "query": "agentic AI frameworks",
        "engine": "duckduckgo",
        "max_results": 5,
        "language": "en",
        "region": "US"
    }
    
    print(f"Searching for: {search_params['query']}")
    result = await web_search.execute_with_tracking(search_params)
    
    print("--------------------------------")
    print(f"result: {result}")
    print("--------------------------------")
    if result.success:
        print(f"✅ Search successful! Found {len(result.result)} results")
        print(f"⏱️  Execution time: {result.execution_time:.2f}s")
        
        # Display results
        for i, search_result in enumerate(result.result, 1):
            print(f"\n{i}. {search_result['title']}")
            print(f"   URL: {search_result['url']}")
            print(f"   Relevance: {search_result.get('relevance', 0.0):.2f}")
            print(f"   Snippet: {search_result['snippet'][:100]}...")
    else:
        print(f"❌ Search failed: {result.errors}")
    
    await web_search.cleanup()
    return result


async def test_composer_tool():
    """Test the composer tool."""
    print("\n📝 Testing ComposerTool")
    print("-" * 40)
    
    # Create composer tool
    composer = ComposerTool(
        tool_id="test_composer",
        config={
            "azure_openai": {
                "deployment_name": "gpt-4o-mini",
                "api_version": "2024-02-15-preview",
                "max_tokens": 2000,
                "temperature": 0.7
            }
        }
    )
    
    # Test content for summarization
    test_content = """
    Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines 
    capable of performing tasks that typically require human intelligence. These tasks include learning, 
    reasoning, problem-solving, perception, and language understanding. AI has applications in various 
    fields including healthcare, finance, transportation, and entertainment. Machine learning, a subset 
    of AI, enables computers to learn and improve from experience without being explicitly programmed.
    """
    
    # Test summarization
    print("Testing summarization...")
    summarize_params = {
        "operation": "summarize",
        "content": test_content,
        "format": "text",
        "style": "formal",
        "length": "short"
    }
    
    result = await composer.execute_with_tracking(summarize_params)
    
    if result.success:
        print(f"✅ Summarization successful!")
        print(f"⏱️  Execution time: {result.execution_time:.2f}s")
        print(f"📋 Summary: {result.result}")
    else:
        print(f"❌ Summarization failed: {result.errors}")
    
    # Test report composition
    print("\nTesting report composition...")
    compose_params = {
        "operation": "compose_report",
        "content": test_content,
        "format": "markdown",
        "style": "formal",
        "length": "medium"
    }
    
    result = await composer.execute_with_tracking(compose_params)
    
    if result.success:
        print(f"✅ Report composition successful!")
        print(f"⏱️  Execution time: {result.execution_time:.2f}s")
        print(f"📄 Report preview: {result.result[:200]}...")
    else:
        print(f"❌ Report composition failed: {result.errors}")
    
    await composer.cleanup()
    return result


async def test_tool_registry():
    """Test the tool registry."""
    print("\n🏪 Testing ToolRegistry")
    print("-" * 40)
    
    # Get registry status
    status = tool_registry.get_tool_status()
    print(f"Total tools: {status['total_tools']}")
    print(f"Available classes: {status['available_classes']}")
    
    # List available tool classes
    available_classes = tool_registry.get_available_tool_classes()
    print(f"Available tool classes: {available_classes}")
    
    # Create tools through registry
    print("\nCreating tools through registry...")
    
    web_search = tool_registry.create_tool("web_search", "registry_web_search")
    if web_search:
        print(f"✅ Created web search tool: {web_search.tool_id}")
        await web_search.cleanup()
    
    composer = tool_registry.create_tool("composer", "registry_composer")
    if composer:
        print(f"✅ Created composer tool: {composer.tool_id}")
        await composer.cleanup()
    
    # Test getting tools by capability
    from tools.base_tool import ToolCapability
    web_search_tools = tool_registry.get_tools_by_capability(ToolCapability.WEB_SEARCH)
    print(f"Tools with web search capability: {len(web_search_tools)}")
    
    # Test getting tools by operation
    search_tools = tool_registry.get_tools_by_operation("web_search")
    print(f"Tools supporting web_search operation: {len(search_tools)}")


async def test_integrated_workflow():
    """Test an integrated workflow using both tools."""
    print("\n🔄 Testing Integrated Workflow")
    print("-" * 40)
    
    # Create tools
    web_search = WebSearchTool(tool_id="workflow_web_search")
    composer = ComposerTool(tool_id="workflow_composer")
    
    try:
        # Step 1: Search for information
        print("Step 1: Searching for information...")
        search_result = await web_search.execute_with_tracking({
            "query": "agentic AI frameworks",
            "engine": "duckduckgo",
            "max_results": 2
        })
        
        if not search_result.success:
            print(f"❌ Search failed: {search_result.errors}")
            return
        
        print("--------------------------------")
        print(f"Search results: {search_result.result}")
        print("--------------------------------")
        
        # Step 2: Prepare content for summarization
        content = "Search Results:\n\n"
        for i, result in enumerate(search_result.result, 1):
            content += f"{i}. {result['title']}\n"
            content += f"   {result['snippet']}\n\n"
        
        # Step 3: Summarize the results
        print("Step 2: Summarizing results...")
        summary_result = await composer.execute_with_tracking({
            "operation": "summarize",
            "content": content,
            "format": "text",
            "style": "formal",
            "length": "medium"
        })
        
        if summary_result.success:
            print(f"✅ Integrated workflow completed!")
            print(f"📋 Summary: {summary_result.result}")
        else:
            print(f"❌ Summarization failed: {summary_result.errors}")
    
    finally:
        await web_search.cleanup()
        await composer.cleanup()


async def main():
    """Main function to run all tests."""
    print("=" * 60)
    print("🧪 TOOLS FRAMEWORK TEST SUITE")
    print("=" * 60)
    
    # Set up logging
    logger = await setup_logging()
    
    try:
        # Test individual tools
        await test_web_search_tool()
        await test_composer_tool()
        
        # Test tool registry
        await test_tool_registry()
        
        # Test integrated workflow
        await test_integrated_workflow()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        logger.error(f"Test failed", error=str(e))


if __name__ == "__main__":
    asyncio.run(main()) 