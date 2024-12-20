from datetime import datetime
from typing import Optional, Set, Dict, List
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
        self.jina_reader = JinaReader()
        self.logger = get_logger(name=__name__)

        # Simple state tracking
        self.scraped_urls: Set[str] = set()
        self.url_depths: Dict[str, int] = {}
        self.discovered_urls: Set[str] = set()

    def _should_scrape_url(self, url: str, source_url: Optional[str]) -> bool:
        """Check if URL should be scraped based on configuration."""
        # Skip if already scraped
        base_url = url.split("#")[0]  # Remove anchor
        if base_url in self.scraped_urls:
            return False

        # For domain/path restrictions, use first seed URL as reference if no source_url
        reference_url = source_url
        if not reference_url and self.project.scrape_job.seed_urls:
            reference_url = str(self.project.scrape_job.seed_urls[0])

        if not reference_url:
            return True

        # Check URL validity and restrictions using utils
        try:
            if not should_follow_url(
                url=base_url, seed_url=reference_url, project=self.project
            ):
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

    def run(self) -> None:
        """Run scraping job sequentially."""
        start_time = datetime.now()
        pages_scraped = 0
        urls_to_scrape = [
            (str(url), 0) for url in self.project.scrape_job.seed_urls
        ]  # (url, depth)
        saved_files = set()  # Track unique files saved

        while urls_to_scrape and (
            not self.project.scrape_job.max_pages
            or pages_scraped < self.project.scrape_job.max_pages
        ):
            url, depth = urls_to_scrape.pop(0)

            # Skip if already scraped or shouldn't scrape
            base_url = url.split("#")[0]
            if base_url in self.scraped_urls:
                continue

            if not self._should_scrape_url(url, None):
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
                    self.logger.info(
                        f"Progress: {pages_scraped}/{len(urls_to_scrape) + len(self.scraped_urls)} pages scraped"
                    )

                # Store the scraped URL
                self.scraped_urls.add(base_url)
                self.url_depths[base_url] = depth

                # Process discovered links if we should follow them
                if self.project.scrape_job.follow_links:
                    for link in discovered_links:
                        if self._should_scrape_url(link, url):
                            urls_to_scrape.append((link, depth + 1))

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
            - Total unique pages discovered: {len(self.discovered_urls)}
            - Unique pages scraped: {pages_scraped}
            - Maximum depth reached: {max(self.url_depths.values()) if self.url_depths else 0}
        """)
