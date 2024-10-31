import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional
import re
from jina_reader import JinaReader

class ParallelScraper:
    MAX_SCRAPERS = 3  # Default number of parallel scrapers
    OUTPUT_DIR = Path("scraped_content")  # Default output directory

    def __init__(self, max_scrapers: Optional[int] = None, output_dir: Optional[Path] = None):
        self.max_scrapers = max_scrapers or self.MAX_SCRAPERS
        self.output_dir = output_dir or self.OUTPUT_DIR
        self.jina_reader = JinaReader()
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
            content = self.jina_reader.read_website(url)
            
            # Extract title from the first line of content
            title = content.split('\n')[0].strip('# ')
            if not title:
                # Use URL as fallback if no title found
                title = url.split('/')[-1]
            
            filename = self._sanitize_filename(title)
            output_path = self.output_dir / filename
            
            output_path.write_text(content)
            print(f"Successfully scraped {url} to {output_path}")
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")

    def scrape_urls(self, urls: List[str]) -> None:
        """Scrape multiple URLs in parallel."""
        with ThreadPoolExecutor(max_workers=self.max_scrapers) as executor:
            executor.map(self._scrape_single_url, urls)

if __name__ == "__main__":
    # Example usage
    urls_to_scrape = [
        "https://docs.crewai.com/concepts/agents",
        "https://docs.crewai.com/concepts/tasks",
        "https://docs.crewai.com/concepts/crews",
    ]
    
    scraper = ParallelScraper(max_scrapers=3, output_dir=Path("output"))
    scraper.scrape_urls(urls_to_scrape)
