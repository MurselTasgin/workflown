"""
Web Scrapers Package

This package contains various web scraping implementations for extracting content
from web pages in different formats (text, markdown, structured data).
"""

from .base_scraper import BaseWebScraper, ScrapedContent
from .web_crawler import (
    WebCrawler, CrawlConfig, CrawledPage, CrawlResult, CrawlStrategy,
    crawl_url, crawl_urls
)
from .beautifulsoup_scraper import BeautifulSoupScraper
from .trafilatura_scraper import TrafilaturaScraper
from .newspaper3k_scraper import Newspaper3kScraper
from .readability_scraper import ReadabilityScraper
from .langchain_scraper import LangChainScraper
from .llamaindex_scraper import LlamaIndexScraper
from .firecrawl_scraper import FirecrawlScraper
from .scraper_manager import ScraperManager

__all__ = [
    'BaseWebScraper',
    'ScrapedContent',
    'WebCrawler',
    'CrawlConfig',
    'CrawledPage',
    'CrawlResult',
    'CrawlStrategy',
    'crawl_url',
    'crawl_urls',
    'BeautifulSoupScraper',
    'TrafilaturaScraper',
    'Newspaper3kScraper',
    'ReadabilityScraper',
    'LangChainScraper',
    'LlamaIndexScraper',
    'FirecrawlScraper',
    'ScraperManager'
] 