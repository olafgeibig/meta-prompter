from datetime import datetime
from typing import Optional, Set, Dict, List
from collections import deque
from urllib.parse import urlparse

from meta_prompter.core.project import Project
from meta_prompter.utils.logging import get_logger

from .jina import JinaReader
from .utils import should_follow_url
from ..utils.file_utils import create_filename_from_url, write_content

class SequentialScraper:
    """Simple sequential web scraper implementation."""

    def __init__(self, project: Project):
        self.project = project
        self.output_dir = project.get_scraped_dir()
        self.output_dir.mkdir(exist_ok=True)
        self.jina_reader = JinaReader()
        self.logger = get_logger(name=__name__)

        # State tracking
        self.scraped_urls: Set[str] = set()  # URLs that have been scraped
        self.url_depths: Dict[str, int] = {}  # Track depth of each URL
        self.discovered_urls: Set[str] = set()  # URLs that meet criteria for scraping
        self.all_found_urls: Set[str] = set()  # All URLs found, regardless of criteria

    def _should_scrape_url(self, url: str, source_url: Optional[str]) -> bool:
        """Check if URL should be scraped based on configuration."""
        base_url = url.split("#")[0]  # Remove anchor

        # Skip if already scraped
        if base_url in self.scraped_urls:
            return False

        # For domain/path restrictions, use source_url as reference
        reference_url = source_url

        if not reference_url and self.project.scrape_job.seed_urls:
            # If no source_url, and we have seed URLs, it means this is a seed URL being checked initially.
            # Use the domain of the current URL as the reference to allow scraping of the seed itself.
            parsed_url = urlparse(url)
            reference_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if not reference_url:
            return True

        # Check URL against project restrictions
        try:
            if not should_follow_url(
                url=base_url, seed_url=reference_url, project=self.project
            ):
                self.logger.debug(f"Not following {url} based on restrictions (ref: {reference_url})")
                return False
        except Exception as e:
            self.logger.debug(f"Invalid URL {url}: {str(e)}")
            return False

        # Check depth
        if source_url:
            source_depth = self.url_depths.get(source_url.split("#")[0], 0)
            new_depth = source_depth + 1
            if (
                self.project.scrape_job.max_depth
                and new_depth > self.project.scrape_job.max_depth
            ):
                self.logger.debug(
                    f"Skipping {url} - exceeds max depth of {self.project.scrape_job.max_depth}"
                )
                return False

        # If we get here, the URL meets all criteria
        self.discovered_urls.add(base_url)
        return True

    def _scrape_url(self, url: str, depth: int) -> Optional[tuple[str, str, List[str]]]:
        """Scrape a single URL and return content, filename and discovered links."""
        try:
            response = self.jina_reader.scrape_website(url)

            if not response.content:
                self.logger.warning(f"No content returned for {url}")
                return None

            # Save content to file
            filename = create_filename_from_url(url, max_length=100)
            output_path = self.output_dir / filename
            write_content(output_path, response.content)

            self.logger.info(f"Scraped {url} to {filename}")
            return response.content, str(output_path), response.links

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return None

    def _process_discovered_links(self, links: List[str], source_url: str, depth: int) -> None:
        """Process newly discovered links and add valid ones to the queue."""
        for link in links:
            self.all_found_urls.add(link)  # Track all URLs found
            if self._should_scrape_url(link, source_url):
                self.url_depths[link] = depth + 1
                self.urls_to_scrape.append((link, depth + 1))

    def run(self) -> None:
        """Run the scraper."""
        start_time = datetime.now()
        pages_scraped = 0
        self.urls_to_scrape = deque(
            [(str(url), 0) for url in self.project.scrape_job.seed_urls]
        )  # (url, depth)
        saved_files = set()  # Track unique files saved

        while self.urls_to_scrape and (
            not self.project.scrape_job.max_pages
            or pages_scraped < self.project.scrape_job.max_pages
        ):
            url, depth = self.urls_to_scrape.popleft()
            base_url = url.split("#")[0]

            # Skip if already scraped
            if base_url in self.scraped_urls:
                continue

            # Check if we should scrape the URL
            if not self._should_scrape_url(url, None if depth == 0 else url):
                continue

            try:
                # Scrape the URL
                result = self._scrape_url(url, depth)
                if not result:
                    continue

                content, filename, discovered_links = result

                # Only count as new if we haven't saved to this file before
                if filename not in saved_files:
                    pages_scraped += 1
                    saved_files.add(filename)
                    # Log progress
                    if self.project.scrape_job.max_pages:
                        self.logger.info(
                            f"Progress: {pages_scraped}/{self.project.scrape_job.max_pages} pages scraped, {len(self.discovered_urls)} pages to scrape"
                        )
                    else:
                        self.logger.info(
                            f"Progress: {pages_scraped} pages scraped, {len(self.discovered_urls)} pages to scrape"
                        )

                # Store the scraped URL
                self.scraped_urls.add(base_url)

                # Process discovered links if we should follow them
                if self.project.scrape_job.follow_links:
                    self._process_discovered_links(discovered_links, base_url, depth)

            except Exception as e:
                self.logger.error(f"Error scraping {url}: {str(e)}")
                continue

            # Break if we've reached max pages
            if (
                self.project.scrape_job.max_pages
                and pages_scraped >= self.project.scrape_job.max_pages
            ):
                break

        # Log final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.logger.info("Scraping completed!")
        self.logger.info(f"""
            - Duration: {duration:.2f} seconds
            - Total URLs found: {len(self.all_found_urls)}
            - URLs meeting criteria: {len(self.discovered_urls)}
            - Pages scraped: {pages_scraped}
            - Average time per page: {duration/pages_scraped if pages_scraped else 0:.2f} seconds
        """)