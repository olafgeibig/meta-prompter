"""
Crawl4AI-based web scraper implementation.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, Dict, Any
from urllib.parse import urlparse

from crawl4ai.web_crawler import WebCrawler
from crawl4ai.extraction_strategy import ReadabilityExtractor, LLMExtractor
from crawl4ai.exceptions import CrawlError  # Assuming this exists, if not we'll create our own

from ..models import Project
from ..utils.logger import get_logger

@dataclass(frozen=True)
class ScrapeResult:
    """Container for scraping results with rich metadata."""
    url: str
    content: str
    depth: int
    metadata: Dict[str, Any]
    timestamp: float

class Crawl4AIScraper:
    """Web scraper implementation using crawl4ai library.
    
    This scraper leverages crawl4ai's advanced features while maintaining
    compatibility with the project's existing infrastructure.
    """

    def __init__(self, project: Project) -> None:
        """Initialize the scraper with project configuration.
        
        Args:
            project: Project configuration and settings
        """
        self.project = project
        self.output_dir = project.get_scraped_dir()
        self.output_dir.mkdir(exist_ok=True)
        self.logger = get_logger(name=__name__)
        
        # Initialize crawl4ai with configured strategies
        strategies = [ReadabilityExtractor()]
        if hasattr(project.config, 'llm_api_key') and project.config.llm_api_key:
            strategies.append(
                LLMExtractor(llm_api_key=project.config.llm_api_key)
            )
        
        self.crawler = WebCrawler(
            extraction_strategy=strategies,
            proxies=getattr(project.config, 'proxies', None),
            enable_javascript=True  # Enable JS rendering by default
        )
        
        # State tracking with type hints
        self.scraped_urls: Set[str] = set()
        self.url_depths: Dict[str, int] = {}
        
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
            
        max_depth = getattr(self.project.config, 'max_depth', 3)
        if depth > max_depth:
            self.logger.debug(f"Skipping {url}: max depth {max_depth} exceeded")
            return False
            
        return True
        
    async def scrape_url(self, url: str, depth: int = 0) -> Optional[ScrapeResult]:
        """Scrape a single URL using crawl4ai.
        
        Args:
            url: The URL to scrape
            depth: Current crawl depth
            
        Returns:
            ScrapeResult if successful, None otherwise
            
        Raises:
            CrawlError: If crawl4ai encounters an error during scraping
        """
        if not self._should_process_url(url, depth):
            return None
            
        try:
            result = self.crawler.run(url=url)
            
            # Create result with metadata
            scrape_result = ScrapeResult(
                url=url,
                content=result.cleaned_text,
                depth=depth,
                metadata={
                    'markdown': result.markdown,
                    'llm_format': result.llm_format,
                    'title': getattr(result, 'title', None),
                    'language': getattr(result, 'language', None),
                    'links': getattr(result, 'links', [])
                },
                timestamp=self.project.config.current_time
            )
            
            # Update state
            self.scraped_urls.add(url)
            self.url_depths[url] = depth
            
            # Save results
            await self._save_results(scrape_result)
            
            return scrape_result
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            raise CrawlError(f"Failed to scrape {url}") from e
            
    async def _save_results(self, result: ScrapeResult) -> None:
        """Save scraping results to filesystem.
        
        Args:
            result: The scraping result to save
        """
        domain_dir = self.output_dir / self._get_domain(result.url)
        domain_dir.mkdir(exist_ok=True)
        
        # Save different content formats
        content_file = domain_dir / f"{result.timestamp}_content.txt"
        markdown_file = domain_dir / f"{result.timestamp}_content.md"
        metadata_file = domain_dir / f"{result.timestamp}_metadata.json"
        
        content_file.write_text(result.content)
        markdown_file.write_text(result.metadata['markdown'])
        metadata_file.write_text(str(result.metadata))  # Convert to JSON in production
        
    async def run(self) -> None:
        """Main entry point for scraping process."""
        seed_urls = getattr(self.project.config, 'seed_urls', [])
        if not seed_urls:
            self.logger.warning("No seed URLs configured")
            return
            
        for url in seed_urls:
            try:
                await self.scrape_url(url)
            except CrawlError as e:
                self.logger.error(f"Failed to process seed URL {url}: {str(e)}")
                continue
