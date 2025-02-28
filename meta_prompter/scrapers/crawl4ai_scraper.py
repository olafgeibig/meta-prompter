"""
Crawl4AI-based web scraper implementation.

This module implements a configurable web scraper using the crawl4ai library.
It supports domain and path restrictions, customizable markdown output, and
comprehensive error handling.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urlparse

# Custom exception to avoid import errors in tests
class CrawlError(Exception):
    """Exception raised when crawling fails."""
    pass

# Use try/except to make it testable without actual crawl4ai
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.exceptions import CrawlError as LibCrawlError
except ImportError:
    # Mock classes for testing
    class AsyncWebCrawler:
        def __init__(self, config=None): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def arun(self, url, config=None): pass
        
    class BrowserConfig:
        def __init__(self, headless=True, verbose=False): pass
        
    class CrawlerRunConfig:
        def __init__(self, **kwargs): pass
        
    class CacheMode:
        ENABLED = "enabled"
        DISABLED = "disabled"
        
    class DefaultMarkdownGenerator:
        def __init__(self, content_filter=None, options=None): pass
        
    class PruningContentFilter:
        def __init__(self, threshold=0.45, threshold_type="dynamic", min_word_threshold=5): pass
        
    # Use our custom CrawlError

from ..core.project import Project
from .models import ScrapingResult, ScraperConfig
from ..utils.file_utils import create_safe_filename
from ..utils.logging import get_logger


class Crawl4AIScraper:
    """Web scraper implementation using crawl4ai library.
    
    This scraper leverages crawl4ai's advanced features including:
    - Domain and path restriction
    - Markdown generation with content filtering
    - Recursive crawling with depth limits
    - Comprehensive error handling
    """

    def __init__(self, project: Project, config_override: Dict[str, Any] = None) -> None:
        """Initialize the scraper with project configuration.
        
        Args:
            project: Project configuration and settings
            config_override: Optional configuration override dictionary
        """
        self.project = project
        self.output_dir = project.get_scraped_dir()
        self.output_dir.mkdir(exist_ok=True)
        self.logger = get_logger(name=__name__)
        
        # State tracking with type hints
        self.scraped_urls: Set[str] = set()
        self.url_depths: Dict[str, int] = {}
        self.discovered_urls: Set[str] = set()
        
        # Extract configuration from project
        self.config = self._load_config(config_override)
        
    def _load_config(self, config_override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load scraper configuration from project settings.
        
        Args:
            config_override: Optional configuration override dictionary
            
        Returns:
            Dictionary with scraper configuration options
        """
        # Create default config
        scraper_config = ScraperConfig()
        config = scraper_config.model_dump()
        
        # Override with project config if available and accessible
        if hasattr(self.project, 'config') and hasattr(self.project.config, 'scraper_config'):
            project_config = self.project.config.scraper_config
            for key in config:
                if hasattr(project_config, key):
                    config[key] = getattr(project_config, key)
        
        # Override with direct parameters if provided
        if config_override:
            for key, value in config_override.items():
                if key in config:
                    config[key] = value
        
        # Get seed URLs from project
        config['seed_urls'] = [str(url) for url in self.project.scrape_job.seed_urls]
                    
        return config
        
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for file organization.
        
        Args:
            url: The URL to process
            
        Returns:
            The domain name extracted from the URL
        """
        return urlparse(url).netloc
        
    def _should_process_url(self, url: str, depth: int) -> bool:
        """Check if URL should be processed based on configuration.
        
        Args:
            url: The URL to check
            depth: Current crawl depth
            
        Returns:
            True if URL should be processed, False otherwise
        """
        if url in self.scraped_urls:
            return False
            
        if depth > self.config['max_depth']:
            self.logger.debug(f"Skipping {url}: max depth {self.config['max_depth']} exceeded")
            return False
        
        # Check path pattern if configured
        if self.config['path_pattern']:
            parsed = urlparse(url)
            if not re.match(self.config['path_pattern'], parsed.path):
                self.logger.debug(f"Skipping {url}: path doesn't match pattern")
                return False
                
        # Check domain exclusions
        if self.config['exclude_domains']:
            domain = self._get_domain(url)
            if domain in self.config['exclude_domains']:
                self.logger.debug(f"Skipping {url}: domain in exclusion list")
                return False
                
        return True

    async def _create_markdown_generator(self) -> DefaultMarkdownGenerator:
        """Create a configured markdown generator.
        
        Returns:
            Configured DefaultMarkdownGenerator instance
        """
        content_filter = PruningContentFilter(
            threshold=self.config['content_filter_threshold'],
            threshold_type="dynamic",
            min_word_threshold=5
        )
        
        return DefaultMarkdownGenerator(
            content_filter=content_filter,
            options={
                "ignore_links": self.config['ignore_links'],
                "ignore_images": self.config['ignore_images'],
                "body_width": self.config['body_width']
            }
        )
        
    async def scrape_url(self, url: str, depth: int = 0) -> Optional[ScrapingResult]:
        """Scrape a single URL using crawl4ai.
        
        Args:
            url: The URL to scrape
            depth: Current crawl depth
            
        Returns:
            ScrapingResult if successful, None otherwise
            
        Raises:
            CrawlError: If crawl4ai encounters an error during scraping
        """
        if not self._should_process_url(url, depth):
            return None
            
        # Configure browser
        browser_config = BrowserConfig(
            headless=self.config['headless'],
            verbose=self.config['verbose']
        )
        
        # Create markdown generator
        md_generator = await self._create_markdown_generator()
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Configure crawler run
                crawler_config = CrawlerRunConfig(
                    exclude_external_links=self.config['exclude_external_links'],
                    exclude_social_media_links=self.config['exclude_social_media_links'],
                    word_count_threshold=self.config['word_count_threshold'],
                    cache_mode=CacheMode.ENABLED if self.config['cache_mode'] else CacheMode.DISABLED,
                    exclude_domains=self.config['exclude_domains'],
                    css_selector=self.config['css_selector'],
                    markdown_generator=md_generator
                )
                
                self.logger.info(f"Scraping URL: {url} (depth: {depth})")
                result = await crawler.arun(url=url, config=crawler_config)
                
                if not result.success:
                    self.logger.error(f"Failed to scrape {url}: {result.error_message}")
                    return ScrapingResult(
                        url=url,
                        content="",
                        markdown="",
                        depth=depth,
                        success=False,
                        error_message=getattr(result, 'error_message', "Unknown error")
                    )
                
                # Extract markdown content
                markdown = ""
                if hasattr(result, 'markdown_v2') and result.markdown_v2:
                    if hasattr(result.markdown_v2, 'fit_markdown') and result.markdown_v2.fit_markdown:
                        markdown = result.markdown_v2.fit_markdown
                    elif hasattr(result.markdown_v2, 'raw_markdown'):
                        markdown = result.markdown_v2.raw_markdown
                else:
                    markdown = result.markdown
                
                # Extract links for further crawling
                internal_links = []
                if hasattr(result, 'links') and isinstance(result.links, dict):
                    internal_links = [
                        link.get('href') for link in result.links.get('internal', [])
                        if link.get('href')
                    ]
                
                # Create result with metadata
                timestamp = datetime.now().timestamp()
                metadata = {
                    'title': getattr(result, 'title', ""),
                    'language': getattr(result, 'language', ""),
                    'word_count': getattr(result, 'word_count', 0),
                    'timestamp': timestamp
                }
                
                scrape_result = ScrapingResult(
                    url=url,
                    content=result.content if hasattr(result, 'content') else "",
                    markdown=markdown,
                    depth=depth,
                    metadata=metadata,
                    timestamp=timestamp,
                    links=internal_links,
                    success=True
                )
                
                # Update state
                self.scraped_urls.add(url)
                self.url_depths[url] = depth
                self.discovered_urls.update(internal_links)
                
                # Save results
                await self._save_results(scrape_result)
                
                return scrape_result
                
        except Exception as e:
            error_msg = f"Failed to scrape {url}: {str(e)}"
            self.logger.error(error_msg)
            
            # Create error result
            return ScrapingResult(
                url=url,
                content="",
                markdown="",
                depth=depth,
                success=False,
                error_message=error_msg
            )
            
    async def _save_results(self, result: ScrapingResult) -> None:
        """Save scraping results to filesystem.
        
        Args:
            result: The scraping result to save
        """
        # Skip saving if scraping failed
        if not result.success:
            self.logger.debug(f"Not saving failed result for {result.url}")
            return
            
        domain_dir = self.output_dir / self._get_domain(result.url)
        domain_dir.mkdir(exist_ok=True)
        
        # Create filename based on URL
        filename_base = create_safe_filename(urlparse(result.url).path)
        if not filename_base:
            filename_base = "index"
        
        # Add timestamp to ensure uniqueness
        timestamp_str = datetime.fromtimestamp(result.timestamp).strftime("%Y%m%d%H%M%S")
        filename_base = f"{timestamp_str}_{filename_base}"
        
        # Save different content formats
        content_file = domain_dir / f"{filename_base}.txt"
        markdown_file = domain_dir / f"{filename_base}.md"
        metadata_file = domain_dir / f"{filename_base}.json"
        
        # Write content
        content_file.write_text(result.content)
        
        # Write markdown with URL header
        markdown_content = f"# {result.url}\n\n{result.markdown}"
        markdown_file.write_text(markdown_content)
        
        # Write metadata as proper JSON
        with open(metadata_file, 'w') as f:
            json.dump(result.metadata, f, indent=2)
        
        self.logger.debug(f"Saved results for {result.url} to {domain_dir}")
        
    async def _crawl_recursive(self, start_url: str) -> None:
        """Recursively crawl from a starting URL respecting depth limits.
        
        Args:
            start_url: The URL to start crawling from
        """
        # Initialize crawl queue with start URL
        to_crawl = [(start_url, 0)]  # (url, depth)
        crawled_count = 0
        
        while to_crawl and len(self.scraped_urls) < self.config['max_pages']:
            # Get next URL and depth
            url, depth = to_crawl.pop(0)
            
            # Skip if already processed
            if url in self.scraped_urls:
                continue
                
            # Scrape the URL
            result = await self.scrape_url(url, depth)
            if not result:
                continue
                
            # Only count successful scrapes
            if result.success:
                crawled_count += 1
                self.logger.info(f"Crawled {crawled_count}/{self.config['max_pages']} pages")
                
                # Add discovered links to crawl queue
                next_depth = depth + 1
                for link in result.links:
                    if link not in self.scraped_urls and self._should_process_url(link, next_depth):
                        to_crawl.append((link, next_depth))
            else:
                self.logger.warning(f"Failed to crawl {url}: {result.error_message}")
                
    async def run(self) -> None:
        """Main entry point for scraping process."""
        seed_urls = self.config['seed_urls']
        if not seed_urls:
            self.logger.warning("No seed URLs configured")
            return
            
        self.logger.info(f"Starting crawl with {len(seed_urls)} seed URLs")
        self.logger.info(f"Max depth: {self.config['max_depth']}, Max pages: {self.config['max_pages']}")
        
        # Process each seed URL as a separate crawl
        for url in seed_urls:
            try:
                await self._crawl_recursive(url)
            except Exception as e:
                self.logger.error(f"Failed to process seed URL {url}: {str(e)}")
                continue
                
        self.logger.info(f"Crawl completed. Processed {len(self.scraped_urls)} URLs.")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the crawling process.
        
        Returns:
            Dictionary with crawling statistics
        """
        return {
            "urls_crawled": len(self.scraped_urls),
            "urls_discovered": len(self.discovered_urls),
            "max_depth_reached": max(self.url_depths.values()) if self.url_depths else 0,
            "config": self.config
        }