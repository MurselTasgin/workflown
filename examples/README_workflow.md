# Search-Scrape-Summarize Workflow

Complete workflow implementation for searching the web, scraping content, and generating AI-powered summaries.

## Overview

This workflow demonstrates the integration of three powerful tools:

1. **🔍 Web Search** - Find relevant URLs using Google search
2. **🕷️ Web Scraping** - Extract content from web pages  
3. **🤖 LLM Summarization** - Generate intelligent summaries using AI

## Architecture

```
User Query
    ↓
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Search    │ -> │   Web Scraper    │ -> │  LLM Composer   │
│                 │    │                  │    │                 │
│ • GoogleSearch  │    │ • Content Extract│    │ • Summarization │
│ • DuckDuckGo    │    │ • Rate Limiting  │    │ • Analysis      │
│ • SerpAPI       │    │ • Error Handling │    │ • Synthesis     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
    URLs                    Content                  Summary
```

## Tools Created

### 1. Web Page Parser (`webpage_parser.py`)

**Features:**
- Multiple extraction strategies (BeautifulSoup, readability, basic regex)
- Rate limiting and respectful crawling
- Content cleaning and text extraction
- Link and image extraction (optional)
- Robust error handling and retries

**Configuration:**
```python
config = {
    "request_timeout": 30,
    "max_content_length": 1024 * 1024,  # 1MB
    "rate_limit_delay": 1.0,
    "max_retries": 3,
    "min_content_length": 100
}
```

### 2. LLM Composer Tool (`composer_tool.py`)

**Features:**
- Text summarization and synthesis
- Multi-source content combination
- Configurable output formats (text, JSON, markdown)
- Mock LLM for testing (easily extensible to real APIs)

**Supported Tasks:**
- `summarize` - Create comprehensive summaries
- `analyze` - Provide analytical insights
- `compose` - Generate structured responses
- `combine` - Synthesize multiple sources

### 3. Integration Tests

**Simple Test (`test_simple_workflow.py`):**
- Basic workflow demonstration
- Uses existing googlesearch test as foundation
- Processes 3 URLs with simple output

**Comprehensive Test (`test_search_scrape_summarize.py`):**
- Full workflow with detailed logging
- Configurable parameters
- Performance metrics
- JSON result export
- Error handling and recovery

## Usage Examples

### Basic Workflow

```python
import asyncio
from examples.tools.websearch.googlesearch_python_search import GoogleSearchPythonTool
from examples.tools.webpage_parser import WebPageParserTool
from examples.tools.composer_tool import ComposerTool

async def search_scrape_summarize(query):
    # 1. Search
    search_tool = GoogleSearchPythonTool()
    search_result = await search_tool.execute({
        "query": query,
        "max_results": 5
    })
    
    # 2. Scrape
    urls = [item["url"] for item in search_result.result]
    scraper = WebPageParserTool()
    scrape_result = await scraper.execute({"urls": urls[:3]})
    
    # 3. Summarize
    composer = ComposerTool()
    summary_result = await composer.execute({
        "task": "combine",
        "content": scrape_result.result,
        "query": query
    })
    
    return summary_result.result

# Run workflow
summary = asyncio.run(search_scrape_summarize("Agentic AI frameworks in 2025"))
print(summary)
```

### Running the Tests

```bash
# Install dependencies
pip install -r examples/tools/requirements_extended.txt

# Run simple workflow test
python examples/test_simple_workflow.py

# Run comprehensive workflow test  
python examples/test_search_scrape_summarize.py "Your query here"

# Example with specific query
python examples/test_search_scrape_summarize.py "Machine learning trends 2025"
```

## Sample Output

```
🔍 Starting Search-Scrape-Summarize Workflow
============================================================
Query: 'Agentic AI frameworks in 2025'
============================================================

📝 Step 1: Searching for content...
✅ Search completed in 3.45s
   Found 5 URLs:
   1. https://example.com/agentic-ai-overview
   2. https://example.com/ai-frameworks-2025
   ...

🕷️ Step 2: Scraping web pages...
✅ Scraping completed in 8.23s
   Processed 5 pages, 4 with valid content:
   1. Agentic AI: The Future of Autonomous Systems... (2,341 chars)
   2. Top AI Frameworks for 2025... (1,892 chars)
   ...

🤖 Step 3: Summarizing with LLM...
✅ Summarization completed in 2.10s
   Generated summary: 487 words

============================================================
🎯 WORKFLOW RESULTS
============================================================
Query: Agentic AI frameworks in 2025
Status: ✅ SUCCESS
Total Time: 13.78 seconds

📋 GENERATED SUMMARY:
────────────────────────────────────────────────────────
# Comprehensive Report: Agentic AI frameworks in 2025

## Introduction
This report combines insights from multiple web sources to provide a 
comprehensive overview of Agentic AI frameworks in 2025.

## Key Findings:
1. **Technology Evolution**: Multiple frameworks are emerging with focus
   on autonomous agent development and deployment
2. **Market Trends**: Growing adoption across industries with emphasis 
   on practical applications
3. **Implementation**: Tools becoming more accessible with improved 
   documentation and community support

[... rest of summary ...]
────────────────────────────────────────────────────────
```

## Configuration Options

### Web Scraper Configuration

```python
scraper_config = {
    "request_timeout": 15,           # Request timeout in seconds
    "max_content_length": 500000,    # Max content size (500KB)
    "rate_limit_delay": 1.5,         # Delay between requests
    "max_retries": 2,                # Retry attempts
    "min_content_length": 200,       # Minimum valid content length
    "respect_robots_txt": True,      # Check robots.txt (simplified)
    "strategy": "auto"               # Extraction strategy
}
```

### LLM Composer Configuration

```python
composer_config = {
    "provider": "mock",              # LLM provider (mock/openai/anthropic)
    "model": "mock-llm",             # Model name
    "max_tokens": 3000,              # Maximum output tokens
    "temperature": 0.7,              # Creativity/randomness
    "max_input_tokens": 8000         # Maximum input tokens
}
```

## Error Handling

The workflow includes comprehensive error handling:

- **Search failures**: Graceful fallback and error reporting
- **Scraping errors**: Individual page failures don't stop the workflow
- **Rate limiting**: Intelligent delays and retry mechanisms
- **Content validation**: Minimum length and quality checks
- **LLM errors**: Fallback to mock responses for testing

## Performance Metrics

The comprehensive test tracks:
- Step-by-step timing
- Content statistics (URLs found, pages scraped, summary length)
- Success/failure rates
- Error categorization
- Total workflow time

## Integration with Existing Code

The workflow integrates seamlessly with your existing `test_googlesearch_python.py`:

```python
# Your existing search code
search_tool = GoogleSearchPythonTool()
results = await search_tool.execute({"query": "agentic AI frameworks", "max_results": 5})

# Add scraping and summarization
urls = [result['url'] for result in results.result]
scraper = WebPageParserTool()
pages = await scraper.execute({"urls": urls})

composer = ComposerTool()
summary = await composer.execute({
    "task": "combine", 
    "content": pages.result,
    "query": "agentic AI frameworks"
})

print(summary.result)
```

## Dependencies

```bash
# Core dependencies
pip install aiohttp beautifulsoup4 googlesearch-python

# Optional enhancements  
pip install python-readability selenium webdriver-manager

# For real LLM integration
pip install openai anthropic
```

## Future Enhancements

- **Real LLM Integration**: Connect to OpenAI, Anthropic, or Azure OpenAI
- **Content Filtering**: Add relevance scoring and content filtering
- **Caching**: Implement content caching to avoid re-scraping
- **Parallel Processing**: Concurrent scraping for better performance
- **Output Formats**: Support for PDF, Word, and other output formats

This workflow provides a solid foundation for building intelligent content aggregation and analysis systems.