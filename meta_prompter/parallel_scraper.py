import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional
import re
import logging
from datetime import datetime
from pydantic import HttpUrl
from meta_prompter.jina_reader import JinaReader
from meta_prompter.custom_types import ScrapeJob

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ParallelScraper:
    MAX_SCRAPERS = 3  # Default number of parallel scrapers
    OUTPUT_DIR = Path("output")  # Default output directory

    def __init__(self, max_scrapers: Optional[int] = None, output_dir: Optional[Path] = None, jina_reader: Optional[JinaReader] = None):
        self.max_scrapers = max_scrapers or self.MAX_SCRAPERS
        self.output_dir = output_dir or self.OUTPUT_DIR
        self.jina_reader = jina_reader or JinaReader()
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def _sanitize_filename(self, title: str) -> str:
        """Convert title to a valid filename."""
        # Remove invalid filename characters and replace spaces with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = sanitized.replace(' ', '_')
        return f"{sanitized}.md"

    def _scrape_single_url(self, url: str, job: ScrapeJob) -> None:
        """Scrape a single URL and add discovered links to job."""
        try:
            # Double-check if the URL has already been scraped
            if job.is_url_scraped(url):
                logging.info(f"Skipping already scraped URL: {url}")
                return

            logging.info(f"Starting to scrape {url}")
            response = self.jina_reader.scrape_website(url)
            
            if not response.content:
                raise ValueError(f"No content returned for {url}")
            
            # Extract title from the first line of content
            lines = response.content.split('\n')
            title = lines[0].strip('# ') if lines else url.split('/')[-1]
            
            filename = self._sanitize_filename(title)
            output_path = self.output_dir / filename
            
            output_path.write_text(response.content)
            logging.info(f"Discovered {len(response.links)} URLs in the page {url}")
            logging.info(f"Successfully scraped {url} to {output_path}")
            
            # Mark the page as done in the job
            job.mark_page_done(url)
            
            # Process discovered links
            if job.follow_links and response.links:
                added_urls = job.add_urls(response.links, url)
                if added_urls:
                    logging.info(f"Added {len(added_urls)} new URLs to scrape")
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return []

    def run(self, job: ScrapeJob) -> None:
        """Run spider starting from seed URLs."""
        start_time = datetime.now()
        
        # Initialize job with seed URLs
        # For seed URLs, use empty string as source since they are at depth 0
        job.add_urls([str(url) for url in job.seed_urls], "")

        with ThreadPoolExecutor(max_workers=self.max_scrapers) as executor:
            while True:
                pending_urls = job.get_pending_urls()
                if not pending_urls:
                    break

                # Create a set of URLs currently being processed
                processing_urls = set(pending_urls[:self.max_scrapers])
                
                # Submit batch of URLs for scraping
                futures = [
                    executor.submit(self._scrape_single_url, url, job)
                    for url in processing_urls
                ]

                # Wait for all futures to complete
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(f"Task failed with error: {str(e)}")

                # Log progress
                stats = job.get_statistics()
                logging.info(f"Progress: {stats['pages_scraped']}/{stats['total_pages_discovered']} pages scraped")

        # Log final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        stats = job.get_statistics()
        logging.info(f"""
        Scraping job completed:
        - Total pages discovered: {stats['total_pages_discovered']}
        - Pages scraped: {stats['pages_scraped']}
        - Pages pending: {stats['pages_pending']}
        - Total time: {duration:.2f} seconds
        """)
