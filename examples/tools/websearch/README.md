# WebSearch Tools

Modular web search implementations with robust rate limiting protection.

## Available Search Tools

### 1. DuckDuckGo Search (`duckduckgo_search.py`)
- **No API key required**
- Uses DuckDuckGo instant answer API + HTML fallback
- More lenient with rate limiting
- Good for general searches

### 2. Google Classic Search (`google_classic_search.py`)  
- **Requires API keys**
- Supports Google Custom Search API or SerpAPI
- High-quality results with rich metadata
- Strict rate limits and quota restrictions

### 3. Google Selenium Search (`google_selenium_search.py`)
- **No API key required**
- Uses headless Chrome/Firefox to scrape Google directly
- Bypasses API rate limits
- Slower but robust against blocking

### 4. Google Search Python (`googlesearch_python_search.py`)
- **No API key required**
- Uses googlesearch-python library
- Simple implementation but limited features
- More prone to being blocked

## Installation

```bash
# Install core dependencies
pip install aiohttp

# Install Selenium (recommended)
pip install selenium webdriver-manager

# Install googlesearch-python (optional)  
pip install googlesearch-python

# Or install all at once
pip install -r requirements.txt
```

## Configuration

### Environment Variables (for API-based tools)

```bash
# Google Custom Search API
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_CSE_ID="your_custom_search_engine_id"

# SerpAPI (alternative to Google API)
export SERPAPI_KEY="your_serpapi_key"
```

### Tool Configuration

```python
config = {
    # Rate limiting
    "rate_limit_delay": 1.0,                    # Base delay between requests
    "max_retries": 3,                          # Maximum retry attempts
    "exponential_backoff_base": 2.0,           # Backoff multiplier
    "max_backoff_delay": 30.0,                 # Maximum delay cap
    "jitter_range": 0.1,                       # Randomization range
    
    # Google Classic specific
    "preferred_api": "serpapi",                # "google" or "serpapi"
    
    # Selenium specific  
    "browser_type": "chrome",                  # "chrome" or "firefox"
    "headless": True,                          # Run headless
    "page_load_timeout": 30,                   # Page load timeout
    
    # googlesearch-python specific
    "pause_between_requests": 2.0,             # Delay between requests
    "tld": "com",                              # Top-level domain
}
```

## Usage Examples

### Basic Usage

```python
import asyncio
from websearch import DuckDuckGoSearchTool

async def search_example():
    tool = DuckDuckGoSearchTool(config={"rate_limit_delay": 1.0})
    
    result = await tool.execute({
        "query": "Agentic AI frameworks in 2025",
        "max_results": 5,
        "language": "en",
        "region": "US"
    })
    
    if result.success:
        for i, res in enumerate(result.result, 1):
            print(f"{i}. {res['title']}")
            print(f"   {res['url']}")
            print(f"   {res['snippet'][:100]}...")
            print()
    
    await tool.cleanup()

asyncio.run(search_example())
```

### Comparing Multiple Engines

```python
import asyncio
from websearch import (
    DuckDuckGoSearchTool,
    GoogleSeleniumSearchTool,
    GoogleClassicSearchTool
)

async def compare_engines():
    query = "Agentic AI frameworks in 2025"
    
    # Test DuckDuckGo
    ddg_tool = DuckDuckGoSearchTool()
    ddg_result = await ddg_tool.execute({"query": query, "max_results": 5})
    await ddg_tool.cleanup()
    
    # Test Google Selenium  
    selenium_tool = GoogleSeleniumSearchTool()
    selenium_result = await selenium_tool.execute({"query": query, "max_results": 5})
    await selenium_tool.cleanup()
    
    print(f"DuckDuckGo: {len(ddg_result.result)} results")
    print(f"Google Selenium: {len(selenium_result.result)} results")

asyncio.run(compare_engines())
```

## Testing

Run the comprehensive test suite:

```bash
# From the examples directory
python test_websearch_tools.py
```

The test suite will:
- Test all available search engines
- Check for required dependencies
- Validate API configurations  
- Measure performance and quality
- Generate detailed reports

## Features

### Rate Limiting Protection
- Exponential backoff retry mechanism
- Intelligent request throttling
- User agent rotation
- Request history tracking

### Error Handling
- Comprehensive error detection
- Rate limit error identification
- Graceful fallback mechanisms
- Detailed logging

### Result Standardization
- Consistent result format across all engines
- Rich metadata collection
- Relevance scoring
- Quality metrics

## Troubleshooting

### Common Issues

1. **"Selenium not available"**
   ```bash
   pip install selenium webdriver-manager
   ```

2. **"Chrome driver not found"**
   - webdriver-manager should handle this automatically
   - Ensure Chrome is installed

3. **"Google API quota exceeded"**
   - Check your Google Cloud Console quotas
   - Switch to SerpAPI or Selenium-based search

4. **"Rate limit exceeded"**
   - Increase `rate_limit_delay` in configuration
   - Use different search engines
   - Enable browser-based fallback

### Best Practices

1. **Use DuckDuckGo for development/testing** - no API keys required
2. **Use Google Selenium for production** - most robust against blocking  
3. **Keep API keys secure** - use environment variables
4. **Implement proper rate limiting** - respect search engine limits
5. **Have fallback mechanisms** - multiple search engines available

## Architecture

```
BaseSearchTool (Abstract)
├── Common rate limiting logic
├── Retry mechanisms  
├── Result standardization
└── Logging framework

├── DuckDuckGoSearchTool
│   ├── Instant Answer API
│   └── HTML parsing fallback
│
├── GoogleClassicSearchTool  
│   ├── Google Custom Search API
│   └── SerpAPI fallback
│
├── GoogleSeleniumSearchTool
│   ├── Chrome WebDriver
│   └── Firefox WebDriver
│
└── GoogleSearchPythonTool
    └── googlesearch-python library
```

This modular design allows for easy extension and customization while maintaining consistent behavior across all implementations.