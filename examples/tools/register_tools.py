#!/usr/bin/env python3
"""
Tool Registration Script

Registers all available tools with rich metadata in the enhanced tool registry.
This script demonstrates how to register tools with comprehensive metadata
for intelligent task-to-tool mapping.
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "websearch"))

from enhanced_tool_registry import get_enhanced_tool_registry, ToolMetadata, ToolCategory
from base_tool import ToolCapability

# Import tool classes
from web_search_tool import WebSearchTool
from composer_tool import ComposerTool
from webpage_parser import WebPageParserTool
from websearch.googlesearch_python_search import GoogleSearchPythonTool
from websearch.duckduckgo_search import DuckDuckGoSearchTool
from websearch.google_classic_search import GoogleClassicSearchTool


def register_search_tools():
    """Register web search tools with metadata."""
    
    registry = get_enhanced_tool_registry()
    
    # Google Search Python Tool
    google_search_metadata = ToolMetadata(
        name="Google Search Python",
        description="Performs web searches using googlesearch-python library. Simple to use but has limited features and may be blocked more easily.",
        version="1.0.0",
        author="Workflown Team",
        category=ToolCategory.SEARCH,
        capabilities=[
            ToolCapability.WEB_SEARCH,
            ToolCapability.HTTP_REQUESTS
        ],
        keywords=[
            "google", "search", "web", "urls", "results", "query",
            "googlesearch", "python", "simple", "basic"
        ],
        tags=[
            "search", "web", "google", "urls", "basic", "simple"
        ],
        input_schema={
            "query": {"type": "string", "required": True, "description": "Search query"},
            "max_results": {"type": "integer", "required": False, "default": 10, "description": "Maximum number of results"},
            "language": {"type": "string", "required": False, "default": "en", "description": "Search language"},
            "region": {"type": "string", "required": False, "default": "US", "description": "Search region"}
        },
        output_schema={
            "urls": {"type": "array", "description": "List of search result URLs"},
            "titles": {"type": "array", "description": "List of search result titles"},
            "count": {"type": "integer", "description": "Number of results found"}
        },
        supported_operations=["search", "query"],
        task_types=["web_search", "search", "url_discovery"]
    )
    
    registry.register_tool(
        tool_class=GoogleSearchPythonTool,
        metadata=google_search_metadata,
        config={
            "pause_between_requests": 2.0,
            "safe": "off",
            "max_retries": 2
        },
        priority=80  # Lower priority than more robust tools
    )
    
    # DuckDuckGo Search Tool
    duckduckgo_metadata = ToolMetadata(
        name="DuckDuckGo Search",
        description="Performs web searches using DuckDuckGo. Privacy-focused and reliable alternative to Google search.",
        version="1.0.0",
        author="Workflown Team",
        category=ToolCategory.SEARCH,
        capabilities=[
            ToolCapability.WEB_SEARCH,
            ToolCapability.HTTP_REQUESTS
        ],
        keywords=[
            "duckduckgo", "search", "web", "privacy", "ddg",
            "alternative", "reliable", "no-tracking"
        ],
        tags=[
            "search", "web", "duckduckgo", "privacy", "alternative"
        ],
        input_schema={
            "query": {"type": "string", "required": True, "description": "Search query"},
            "max_results": {"type": "integer", "required": False, "default": 10, "description": "Maximum number of results"},
            "region": {"type": "string", "required": False, "default": "us-en", "description": "Search region"}
        },
        output_schema={
            "urls": {"type": "array", "description": "List of search result URLs"},
            "titles": {"type": "array", "description": "List of search result titles"},
            "snippets": {"type": "array", "description": "List of search result snippets"},
            "count": {"type": "integer", "description": "Number of results found"}
        },
        supported_operations=["search", "query"],
        task_types=["web_search", "search", "url_discovery"]
    )
    
    registry.register_tool(
        tool_class=DuckDuckGoSearchTool,
        metadata=duckduckgo_metadata,
        config={
            "max_retries": 3,
            "timeout": 10
        },
        priority=90  # Higher priority than Google Search Python
    )
    
    # Google Classic Search Tool
    google_classic_metadata = ToolMetadata(
        name="Google Classic Search",
        description="Performs web searches using Google's classic search interface. More robust than googlesearch-python.",
        version="1.0.0",
        author="Workflown Team",
        category=ToolCategory.SEARCH,
        capabilities=[
            ToolCapability.WEB_SEARCH,
            ToolCapability.HTTP_REQUESTS
        ],
        keywords=[
            "google", "search", "web", "classic", "robust",
            "reliable", "selenium", "browser"
        ],
        tags=[
            "search", "web", "google", "classic", "robust", "selenium"
        ],
        input_schema={
            "query": {"type": "string", "required": True, "description": "Search query"},
            "max_results": {"type": "integer", "required": False, "default": 10, "description": "Maximum number of results"},
            "language": {"type": "string", "required": False, "default": "en", "description": "Search language"}
        },
        output_schema={
            "urls": {"type": "array", "description": "List of search result URLs"},
            "titles": {"type": "array", "description": "List of search result titles"},
            "snippets": {"type": "array", "description": "List of search result snippets"},
            "count": {"type": "integer", "description": "Number of results found"}
        },
        supported_operations=["search", "query"],
        task_types=["web_search", "search", "url_discovery"]
    )
    
    registry.register_tool(
        tool_class=GoogleClassicSearchTool,
        metadata=google_classic_metadata,
        config={
            "headless": True,
            "timeout": 30,
            "max_retries": 2
        },
        priority=95  # Highest priority among search tools
    )


def register_processing_tools():
    """Register data processing tools with metadata."""
    
    registry = get_enhanced_tool_registry()
    
    # Web Page Parser Tool
    webpage_parser_metadata = ToolMetadata(
        name="Web Page Parser",
        description="Scrapes and parses web pages to extract content, links, and metadata. Supports multiple parsing strategies.",
        version="1.0.0",
        author="Workflown Team",
        category=ToolCategory.PROCESSING,
        capabilities=[
            ToolCapability.HTTP_REQUESTS,
            ToolCapability.DATA_PROCESSING
        ],
        keywords=[
            "webpage", "parser", "scraper", "content", "extraction",
            "html", "text", "links", "metadata", "beautifulsoup"
        ],
        tags=[
            "processing", "webpage", "parser", "scraper", "content"
        ],
        input_schema={
            "urls": {"type": "array", "required": True, "description": "List of URLs to parse"},
            "strategy": {"type": "string", "required": False, "default": "auto", "description": "Parsing strategy"},
            "extract_links": {"type": "boolean", "required": False, "default": False, "description": "Whether to extract links"},
            "extract_images": {"type": "boolean", "required": False, "default": False, "description": "Whether to extract images"}
        },
        output_schema={
            "content": {"type": "string", "description": "Extracted text content"},
            "title": {"type": "string", "description": "Page title"},
            "links": {"type": "array", "description": "List of extracted links"},
            "metadata": {"type": "object", "description": "Page metadata"}
        },
        supported_operations=["parse", "scrape", "extract"],
        task_types=["web_scraping", "content_extraction", "data_processing"]
    )
    
    registry.register_tool(
        tool_class=WebPageParserTool,
        metadata=webpage_parser_metadata,
        config={
            "request_timeout": 15,
            "max_content_length": 200000,
            "rate_limit_delay": 1.5,
            "max_retries": 2,
            "min_content_length": 200
        },
        priority=90
    )


def register_generation_tools():
    """Register text generation tools with metadata."""
    
    registry = get_enhanced_tool_registry()
    
    # Composer Tool
    composer_metadata = ToolMetadata(
        name="LLM Composer",
        description="Generates text content using Large Language Models. Supports various providers and models.",
        version="1.0.0",
        author="Workflown Team",
        category=ToolCategory.GENERATION,
        capabilities=[
            ToolCapability.TEXT_GENERATION,
            ToolCapability.TEXT_SUMMARIZATION
        ],
        keywords=[
            "llm", "generation", "text", "composer", "ai",
            "openai", "azure", "gpt", "completion", "summary"
        ],
        tags=[
            "generation", "llm", "text", "ai", "composer"
        ],
        input_schema={
            "task": {"type": "string", "required": True, "description": "Task type (combine, summarize, etc.)"},
            "content": {"type": "array", "required": False, "description": "Input content to process"},
            "query": {"type": "string", "required": False, "description": "Query or prompt"},
            "format": {"type": "string", "required": False, "default": "text", "description": "Output format"}
        },
        output_schema={
            "result": {"type": "string", "description": "Generated text content"},
            "word_count": {"type": "integer", "description": "Number of words generated"},
            "model_used": {"type": "string", "description": "Model used for generation"}
        },
        supported_operations=["generate", "summarize", "combine", "compose"],
        task_types=["text_generation", "summarization", "content_creation"]
    )
    
    registry.register_tool(
        tool_class=ComposerTool,
        metadata=composer_metadata,
        config={
            "provider": "azure_openai",
            "max_tokens": 2000,
            "temperature": 0.7
        },
        priority=95
    )


def register_all_tools():
    """Register all available tools with metadata."""
    print("🔧 Registering tools with enhanced metadata...")
    
    try:
        # Register tools by category
        register_search_tools()
        register_processing_tools()
        register_generation_tools()
        
        # Print registration summary
        registry = get_enhanced_tool_registry()
        stats = registry.get_statistics()
        print(f"\n✅ Tool registration completed!")
        print(f"📊 Registry Statistics:")
        print(f"   • Total tools: {stats['total_tools']}")
        print(f"   • Active tools: {stats['active_tools']}")
        print(f"   • Categories: {stats['categories']}")
        print(f"   • Capabilities: {stats['capabilities']}")
        
        # List all registered tools
        print(f"\n📋 Registered Tools:")
        tools = registry.list_tools()
        for tool in tools:
            print(f"   • {tool['name']} ({tool['category']}) - {tool['description'][:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = register_all_tools()
    sys.exit(0 if success else 1) 