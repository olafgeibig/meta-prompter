from datetime import datetime
import logging
from typing import Optional, Set, Dict, List
from urllib.parse import urlparse
from meta_prompter.core.project import Project

from ..services.jina.client import JinaReader
from ..utils.file_utils import sanitize_filename, write_content

class SequentialScraper():
    """Simple sequential web scraper implementation."""
    
    def __init__(self, project: Project):
        self.project = project
        self.output_dir = project.get_scraped_dir()
        self.jina_reader = JinaReader()
        
        # Simple state tracking
        self.scraped_urls: Set[str] = set()
        self.url_depths: Dict[str, int] = {}
        self.discovered_urls: Set[str] = set()
        
    def _should_scrape_url(self, url: str, source_url: Optional[str]) -> bool:
        """Check if URL should be scraped based on configuration."""
        # Skip if already scraped
        base_url = url.split('#')[0]  # Remove anchor
        if base_url in self.scraped_urls:
            return False
            
        # Parse URLs
        parsed_url = urlparse(base_url)
        
        # For domain/path restrictions, use first seed URL as reference if no source_url
        reference_url = source_url
        if not reference_url and self.project.scrape_job.seed_urls:
            reference_url = str(self.project.scrape_job.seed_urls[0])
            
        if reference_url:
            parsed_ref = urlparse(reference_url.split('#')[0])  # Remove anchor from reference
            
            # Check domain restriction
            if self.project.scrape_job.domain_restricted and parsed_url.netloc != parsed_ref.netloc:
                logging.debug(f"Skipping {url} - different domain than {reference_url}")
                return False
                
            # Check path restriction - only up to last / in seed URL
            if self.project.scrape_job.path_restricted:
                ref_path_base = '/'.join(parsed_ref.path.rstrip('/').split('/')[:-1]) + '/'
                if not parsed_url.path.startswith(ref_path_base):
                    logging.debug(f"Skipping {url} - not under path {ref_path_base}")
                    return False
            
        # Check depth
        if source_url:
            source_depth = self.url_depths.get(source_url.split('#')[0], 0)
            new_depth = source_depth + 1
            if self.project.scrape_job.max_depth and new_depth > self.project.scrape_job.max_depth:
                logging.debug(f"Skipping {url} - exceeds max depth of {self.project.scrape_job.max_depth}")
                return False
                
        # Check exclusion patterns
        for pattern in self.project.scrape_job.exclusion_patterns:
            if pattern in url:
                logging.debug(f"Skipping {url} - matches exclusion pattern: {pattern}")
                return False
                
        return True
        
    def _scrape_url(self, url: str, depth: int) -> Optional[tuple[str, str, List[str]]]:
        """Scrape a single URL and return content, filename and discovered links."""
        try:
            logging.info(f"Scraping {url}")
            response = self.jina_reader.scrape_website(url)
            
            if not response.content:
                logging.warning(f"No content returned for {url}")
                return None
                
            # Extract title from the first line of content
            lines = response.content.split('\n')
            title = lines[0].strip('# ') if lines else url.split('/')[-1]
            
            # Save content to file
            filename = sanitize_filename(title) + ".md"
            output_path = self.output_dir / filename
            write_content(output_path, response.content)
            
            logging.info(f"Successfully scraped {url} to {output_path}")
            return response.content, str(output_path), response.links
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return None

    def run(self) -> None:
        """Run scraping job sequentially."""
        start_time = datetime.now()
        pages_scraped = 0
        urls_to_scrape = [(str(url), 0) for url in self.project.scrape_job.seed_urls]  # (url, depth)
        saved_files = set()  # Track unique files saved
        
        while urls_to_scrape and (not self.project.scrape_job.max_pages or pages_scraped < self.project.scrape_job.max_pages):
            url, depth = urls_to_scrape.pop(0)
            
            # Skip if already scraped or shouldn't scrape
            base_url = url.split('#')[0]
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
                    logging.info(f"Progress: {pages_scraped}/{self.project.scrape_job.max_pages} pages scraped")
                
                # Store the scraped URL
                self.scraped_urls.add(base_url)
                self.url_depths[base_url] = depth
                
                # Process discovered links if we should follow them
                if self.project.scrape_job.follow_links:
                    for link in discovered_links:
                        if self._should_scrape_url(link, url):
                            urls_to_scrape.append((link, depth + 1))
                            
            except Exception as e:
                logging.error(f"Error scraping {url}: {str(e)}")
                continue
                
            # Break if we've reached max pages
            if self.project.scrape_job.max_pages and pages_scraped >= self.project.scrape_job.max_pages:
                break
                
        # Log final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logging.info("Scraping completed!")
        logging.info(f"""
            - Duration: {duration:.2f} seconds
            - Total unique pages discovered: {len(self.discovered_urls)}
            - Unique pages scraped: {pages_scraped}
            - Maximum depth reached: {max(self.url_depths.values()) if self.url_depths else 0}
        """)
