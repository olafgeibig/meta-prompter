from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional
import threading

from .base import BaseScraper
from ..models.scrape_job import ScrapeJobConfig
from ..core.job_manager import ThreadSafeJobState
from ..services.jina.client import JinaReader
from ..utils.file_utils import sanitize_filename, write_content

class ParallelScraper(BaseScraper):
    """Parallel web scraper implementation."""
    
    def __init__(self, max_workers: Optional[int] = None, output_dir: Optional[Path] = None):
        super().__init__(max_workers)
        self.output_dir = output_dir or Path("output")
        self.jina_reader = JinaReader()
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def _scrape_url(self, url: str, job_state: ThreadSafeJobState) -> None:
        """Scrape a single URL and process discovered links."""
        try:
            # Double-check if URL has already been scraped
            if any(page.done and page.url == url for page in job_state._pages):
                logging.info(f"Skipping already scraped URL: {url}")
                return

            logging.info(f"Starting to scrape {url}")
            response = self.jina_reader.scrape_website(url)
            
            if not response.content:
                raise ValueError(f"No content returned for {url}")
            
            # Extract title from the first line of content
            lines = response.content.split('\n')
            title = lines[0].strip('# ') if lines else url.split('/')[-1]
            
            # Save content to file
            filename = sanitize_filename(title)
            output_path = self.output_dir / filename
            write_content(output_path, response.content)
            
            # Process discovered links
            if job_state.config.follow_links and response.links:
                added_urls = job_state.add_urls(response.links, url)
                logging.info(f"Discovered {len(response.links)} URLs in the page {url}")
                if added_urls:
                    logging.info(f"Added {len(added_urls)} new URLs to scrape")
            
            logging.info(f"Successfully scraped {url} to {output_path}")
            
            # Mark as done with metadata
            job_state.mark_done(url, filename=str(output_path), content_hash=str(hash(response.content)))
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return

    def scrape(self, config: ScrapeJobConfig) -> None:
        """Run scraping job."""
        start_time = datetime.now()
        job_state = ThreadSafeJobState(config)
        urls_to_scrape = list(config.seed_urls)
        scraped_count = 0

        while urls_to_scrape and scraped_count < config.max_pages:
            url = urls_to_scrape.pop(0)
            self._scrape_url(url, job_state)
            scraped_count = len([p for p in job_state._pages if p.done])
            
            # Get new URLs to scrape
            pending_urls = job_state.get_pending_urls()
            for url in pending_urls:
                if url not in urls_to_scrape:
                    urls_to_scrape.append(url)

            # Log progress
            logging.info(f"Progress: {scraped_count}/{config.max_pages} pages scraped")
            
        # Log final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        stats = job_state.get_statistics()
        
        logging.info("Scraping completed!")
        logging.info(f"Statistics:")
        logging.info(f"""
            - Duration: {duration:.2f} seconds
            - Total unique pages discovered: {stats['total_unique_pages']}
            - Unique pages scraped: {stats['unique_pages_scraped']}
            - Pages pending: {stats['pages_pending']}
            - Maximum depth reached: {stats['max_depth_reached']}
        """)
