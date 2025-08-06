"""
Google Selenium Search Tool

Performs web searches using Selenium WebDriver to scrape Google search results directly.
Uses headless Chrome/Firefox to bypass API rate limits and access real Google search.
"""

import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from base_search import BaseSearchTool, SearchResult


class GoogleSeleniumSearchTool(BaseSearchTool):
    """
    Google search implementation using Selenium WebDriver.
    
    Scrapes Google search results directly using a headless browser.
    More robust against rate limiting but slower than API calls.
    
    Configuration:
    - browser_type: "chrome" or "firefox" (default: "chrome")
    - headless: Run browser in headless mode (default: True)
    - page_load_timeout: Maximum time to wait for page load (default: 30)
    - element_timeout: Maximum time to wait for elements (default: 10)
    - window_size: Browser window size (default: "1920,1080")
    """
    
    def __init__(self, tool_id: str = None, config: dict = None):
        if not SELENIUM_AVAILABLE:
            raise ImportError(
                "Selenium is required for GoogleSeleniumSearchTool. "
                "Install with: pip install selenium webdriver-manager"
            )
        
        super().__init__(
            tool_id=tool_id or "google_selenium_search",
            name="GoogleSeleniumSearch",
            description="Performs web searches using Selenium WebDriver to scrape Google",
            config=config
        )
        
        # Browser configuration
        self.browser_type = self.config.get("browser_type", "chrome").lower()
        self.headless = self.config.get("headless", True)
        self.page_load_timeout = self.config.get("page_load_timeout", 30)
        self.element_timeout = self.config.get("element_timeout", 10)
        self.window_size = self.config.get("window_size", "1920,1080")
        
        # Driver will be created per search to avoid stale sessions
        self.driver = None
    
    def _initialize(self):
        """Initialize WebDriver settings."""
        pass
    
    def _create_driver(self):
        """Create a new WebDriver instance."""
        if self.browser_type == "firefox":
            options = FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument(f"--window-size={self.window_size}")
            
            # Set user agent
            user_agent = self.get_random_user_agent()
            options.set_preference("general.useragent.override", user_agent)
            
            # Privacy settings
            options.set_preference("privacy.trackingprotection.enabled", False)
            options.set_preference("dom.webnotifications.enabled", False)
            
            driver = webdriver.Firefox(options=options)
        else:
            # Default to Chrome
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument(f"--window-size={self.window_size}")
            
            # Set user agent
            user_agent = self.get_random_user_agent()
            options.add_argument(f"--user-agent={user_agent}")
            
            # Additional privacy/stealth options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set timeouts
        driver.set_page_load_timeout(self.page_load_timeout)
        driver.implicitly_wait(2)
        
        return driver
    
    async def _perform_search(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str
    ) -> List[SearchResult]:
        """
        Perform Google search using Selenium WebDriver.
        
        Creates a new driver instance for each search to avoid stale sessions.
        """
        driver = None
        try:
            # Create driver for this search
            await self._log_info(f"Creating WebDriver for Google search")
            driver = self._create_driver()
            
            # Build Google search URL
            search_url = self._build_search_url(query, language, region)
            
            await self._log_info(f"Navigating to Google search", url=search_url)
            driver.get(search_url)
            
            # Wait for search results to load
            wait = WebDriverWait(driver, self.element_timeout)
            
            # Handle potential consent/cookie dialogs
            await self._handle_consent_dialogs(driver)
            
            # Wait for search results
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ved]")))
            except TimeoutException:
                # Try alternative selector
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".g")))
                except TimeoutException:
                    raise Exception("Google search results did not load - possible blocking or CAPTCHA")
            
            # Extract search results
            results = await self._extract_search_results(driver, max_results)
            
            await self._log_info(
                f"Successfully extracted Google search results",
                query=query,
                results_count=len(results)
            )
            
            return results
            
        except WebDriverException as e:
            if "chrome not reachable" in str(e).lower():
                raise Exception("Chrome browser not accessible - may be blocked or crashed")
            elif "session not created" in str(e).lower():
                raise Exception("Failed to create browser session - driver may be outdated")
            else:
                raise Exception(f"WebDriver error: {str(e)}")
        
        except Exception as e:
            await self._log_error(f"Google Selenium search failed", query=query, error=str(e))
            raise
        
        finally:
            # Always clean up driver
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _build_search_url(self, query: str, language: str, region: str) -> str:
        """Build Google search URL with proper parameters."""
        # Base Google search URL
        base_url = "https://www.google.com/search"
        
        # URL parameters
        params = {
            'q': query,
            'hl': language,           # Interface language
            'gl': region.lower(),     # Geographic location
            'num': 20,               # Number of results per page
            'safe': 'off',           # Safe search off
            'filter': '0'            # Don't filter similar results
        }
        
        # Build URL manually to ensure proper encoding
        param_string = "&".join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    
    async def _handle_consent_dialogs(self, driver):
        """Handle Google consent/cookie dialogs."""
        try:
            # Wait briefly for consent dialog
            wait = WebDriverWait(driver, 3)
            
            # Try to accept cookies/consent
            consent_selectors = [
                "[id*='accept']",
                "[id*='consent']", 
                "button[aria-label*='Accept']",
                "button[aria-label*='I agree']",
                "#L2AGLb",  # Common Google consent button ID
                ".QS5gu"   # Another consent button class
            ]
            
            for selector in consent_selectors:
                try:
                    button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    button.click()
                    await self._log_info(f"Accepted consent dialog")
                    asyncio.sleep(1)  # Wait for dialog to close
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
                    
        except Exception:
            # Consent handling is optional - continue if it fails
            pass
    
    async def _extract_search_results(self, driver, max_results: int) -> List[SearchResult]:
        """Extract search results from the page."""
        results = []
        
        # Try multiple selectors for different Google layouts
        result_selectors = [
            ".g:has([data-ved])",  # Standard organic results
            ".g",                  # Fallback for organic results
            "[data-ved]:has(h3)",  # Results with h3 titles
        ]
        
        result_elements = []
        for selector in result_selectors:
            try:
                result_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if result_elements:
                    await self._log_info(f"Found {len(result_elements)} results with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not result_elements:
            raise Exception("No search results found - Google may have blocked the request")
        
        # Process each result element
        for i, element in enumerate(result_elements[:max_results]):
            try:
                result = await self._extract_single_result(element, i)
                if result:
                    results.append(result)
            except Exception as e:
                await self._log_warning(f"Failed to extract result {i+1}", error=str(e))
                continue
        
        return results
    
    async def _extract_single_result(self, element, position: int) -> Optional[SearchResult]:
        """Extract data from a single search result element."""
        try:
            # Extract title and URL
            title_link = None
            title_selectors = ["h3 a", "a h3", "[data-ved] h3", "h3"]
            
            for selector in title_selectors:
                try:
                    title_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    if title_elements:
                        # Find the link element
                        if selector.endswith(" a"):
                            title_link = title_elements[0]
                        else:
                            # Look for parent link
                            for te in title_elements:
                                parent_link = te.find_element(By.XPATH, "./ancestor-or-self::a")
                                if parent_link:
                                    title_link = parent_link
                                    break
                        
                        if title_link:
                            break
                except (NoSuchElementException, Exception):
                    continue
            
            if not title_link:
                return None
            
            # Get title and URL
            title = title_link.text.strip()
            url = title_link.get_attribute("href")
            
            if not title or not url or not url.startswith("http"):
                return None
            
            # Extract snippet
            snippet = ""
            snippet_selectors = [
                "[data-sncf]",           # Standard snippet
                ".VwiC3b",               # Alternative snippet class
                "[style*='-webkit-line-clamp']",  # Multi-line snippets
                ".s",                    # Legacy snippet class
                "span:contains('...'),div:contains('...')"  # Any text with ellipsis
            ]
            
            for selector in snippet_selectors:
                try:
                    snippet_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for se in snippet_elements:
                        text = se.text.strip()
                        if text and len(text) > len(snippet):
                            snippet = text
                except Exception:
                    continue
            
            # Fallback: get any text content from the result
            if not snippet:
                try:
                    snippet = element.text.strip()
                    # Clean up the snippet (remove title from beginning)
                    if snippet.startswith(title):
                        snippet = snippet[len(title):].strip()
                    # Limit length
                    snippet = snippet[:300]
                except Exception:
                    snippet = "No description available"
            
            return SearchResult(
                title=title[:150],
                url=url,
                snippet=snippet[:400],
                relevance=0.9 - (position * 0.05),
                metadata={
                    "source": "google_selenium",
                    "position": position + 1,
                    "extraction_method": "selenium_scraping"
                }
            )
            
        except Exception as e:
            # Use print instead of async logging in sync method
            print(f"Warning: Failed to extract single result {position+1}: {str(e)}")
            return None
    
    async def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None