#!/usr/bin/env python3
"""
Google search using httpx and BeautifulSoup
Handles JavaScript-heavy responses and provides fallback options
"""

import httpx
from bs4 import BeautifulSoup
import re
import json
import time

def google_search(query, max_results=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    params = {
        "q": query,
        "hl": "en",
        "num": str(max_results),
        "safe": "off",
        "source": "hp",
        "ie": "UTF-8",
        "oe": "UTF-8",
    }

    url = "https://www.google.com/search"
    
    try:
        with httpx.Client(http2=True, headers=headers, timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code != 200:
            print(f"⚠️ HTTP Error: {response.status_code}")
            return []
        
        # Check for JavaScript-heavy response or CAPTCHA
        html = response.text
        if "knitsail" in html or "IeG41gjVliAgplG0Jt0RWbFNVP9CId5MPRQ" in html:
            print("⚠️ Google is serving JavaScript-heavy response (anti-bot protection)")
            return _handle_js_response(html, query, max_results)
        
        if "captcha" in html.lower() or "our systems have detected unusual traffic" in html.lower():
            print("⚠️ Blocked by CAPTCHA or traffic detection.")
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        results = []
        
        # Try multiple selectors for Google search results
        selectors = [
            "div.g",  # Standard Google result
            "div[data-ved]",  # Results with data-ved attribute
            "div.rc",  # Alternative result container
            "div[jscontroller]",  # Results with jscontroller
            "div[data-hveid]",  # Results with data-hveid
            "div[jsname]",  # Results with jsname
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            print(f"Found {len(elements)} elements with selector: {selector}")
            
            for element in elements:
                # Try different title selectors
                title_selectors = ["h3", "h3.r", "h3.LC20lb", "div.vvjwJb", "a[data-ved]"]
                title = None
                
                for title_selector in title_selectors:
                    title_elem = element.select_one(title_selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                # Try different link selectors
                link_selectors = ["a[href]", "a[data-ved]", "a[ping]", "a[jsname]"]
                link = None
                
                for link_selector in link_selectors:
                    link_elem = element.select_one(link_selector)
                    if link_elem and link_elem.get("href", "").startswith("http"):
                        link = link_elem["href"]
                        break
                
                if title and link:
                    results.append({
                        "title": title,
                        "url": link
                    })
                    print(f"Found result: {title[:50]}... -> {link}")
                
                if len(results) >= max_results:
                    break
            
            if results:
                break
        
        # If no results found with structured selectors, try regex-based extraction
        if not results:
            print("Trying regex-based extraction...")
            results = _extract_with_regex(html, max_results)
        
        return results
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return []

def _handle_js_response(html, query, max_results):
    """Handle JavaScript-heavy Google responses."""
    print("Attempting to extract data from JavaScript response...")
    
    # Look for any URLs that might be search results
    url_pattern = r'href="(https?://[^"]*)"'
    urls = re.findall(url_pattern, html)
    external_urls = [url for url in urls if 'google.com' not in url and 'youtube.com' not in url]
    
    print(f"External URLs found: {len(external_urls)}")
    
    # Look for any text that might be titles
    title_pattern = r'<h[1-6][^>]*>([^<]+)</h[1-6]>'
    titles = re.findall(title_pattern, html)
    
    print(f"Potential titles found: {len(titles)}")
    
    results = []
    for i, url in enumerate(external_urls[:max_results]):
        title = titles[i] if i < len(titles) else f"Search result {i+1}"
        results.append({
            "title": title.strip(),
            "url": url
        })
        print(f"JS extracted: {title[:50]}... -> {url}")
    
    return results

def _extract_with_regex(html, max_results):
    """Extract search results using regex patterns."""
    results = []
    
    # Look for URLs in the HTML
    url_pattern = r'href="([^"]*)"[^>]*data-ved'
    urls = re.findall(url_pattern, html)
    
    # Look for titles
    title_pattern = r'<h3[^>]*>([^<]+)</h3>'
    titles = re.findall(title_pattern, html)
    
    for i, (url, title) in enumerate(zip(urls, titles)):
        if url.startswith("http") and len(results) < max_results:
            results.append({
                "title": title.strip(),
                "url": url
            })
            print(f"Regex found: {title[:50]}... -> {url}")
    
    return results

def search_with_fallback(query, max_results=10):
    """Search with multiple fallback options."""
    print(f"Searching for: {query}")
    
    # Try Google first
    results = google_search(query, max_results)
    
    if results:
        print(f"✅ Found {len(results)} results from Google")
        return results
    
    print("⚠️ Google search failed, trying alternative search engines...")
    
    # Try DuckDuckGo as fallback
    try:
        results = duckduckgo_search(query, max_results)
        if results:
            print(f"✅ Found {len(results)} results from DuckDuckGo")
            return results
    except Exception as e:
        print(f"❌ DuckDuckGo search failed: {e}")
    
    print("❌ All search methods failed")
    return []

def duckduckgo_search(query, max_results=10):
    """Search using DuckDuckGo API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Workflown/1.0)",
        "Accept": "application/json",
    }
    
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "t": "workflown"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get("https://api.duckduckgo.com/", params=params, headers=headers)
        
        if response.status_code == 200:
            try:
                data = response.json()
                results = []
                
                # Extract abstract
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("AbstractText", "DuckDuckGo Result"),
                        "url": data.get("AbstractURL", ""),
                    })
                
                # Extract related topics
                for topic in data.get("RelatedTopics", [])[:max_results-1]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                        })
                
                return results[:max_results]
            except json.JSONDecodeError:
                print("⚠️ DuckDuckGo returned non-JSON response")
                return []
        else:
            print(f"⚠️ DuckDuckGo HTTP Error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ DuckDuckGo search error: {e}")
        return []

# Example usage
if __name__ == "__main__":
    # Test with a simpler query first
    query = "artificial intelligence in finance"
    print(f"Testing with query: {query}")
    
    # Test DuckDuckGo directly
    print("\n=== Testing DuckDuckGo ===")
    results = duckduckgo_search(query, 5)
    
    if results:
        print(f"\n📋 Found {len(results)} results from DuckDuckGo:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print()
    else:
        print("❌ No results from DuckDuckGo")
    
    # Test Google
    print("\n=== Testing Google ===")
    results = google_search(query, 5)
    
    if results:
        print(f"\n📋 Found {len(results)} results from Google:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print()
    else:
        print("❌ No results from Google")
    
    # Test fallback search
    print("\n=== Testing Fallback Search ===")
    results = search_with_fallback(query, 5)
    
    if results:
        print(f"\n📋 Found {len(results)} results from fallback:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print()
    else:
        print("❌ No results found")
