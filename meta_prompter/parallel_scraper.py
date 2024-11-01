import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional
import re
import logging
from meta_prompter.jina_reader import JinaReader

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

    def _scrape_single_url(self, url: str) -> None:
        """Scrape a single URL and save its content."""
        try:
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
            logging.info(f"Successfully scraped {url} to {output_path}")
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")

    def scrape_urls(self, urls: List[str]) -> None:
        """Scrape multiple URLs in parallel."""
        with ThreadPoolExecutor(max_workers=self.max_scrapers) as executor:
            # Submit all tasks and wait for them to complete
            futures = [executor.submit(self._scrape_single_url, url) for url in urls]
            # Wait for all futures to complete
            for future in futures:
                try:
                    future.result()  # This will raise any exceptions that occurred
                except Exception as e:
                    logging.error(f"Task failed with error: {str(e)}")
