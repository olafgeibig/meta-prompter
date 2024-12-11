"""Job manager for web scraping."""
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from pydantic import HttpUrl

from meta_prompter.models.page import Page
from meta_prompter.models.project import Project
from meta_prompter.scrapers.url_processor import normalize_url, should_follow_url


@dataclass
class ThreadSafeJobState:
    """Thread-safe state for a scraping job."""
    seed_urls: List[str]
    domain_restricted: bool
    path_restricted: bool
    exclusion_patterns: Optional[List[str]]
    max_pages: Optional[int]
    max_depth: Optional[int]
    output_dir: str
    discovered_urls: Set[str]
    scraped_urls: Set[str]
    unique_files: Set[str]
    pages_scraped: int
    max_depth_reached: int

    def __init__(self, project: Project, output_dir: str):
        """Initialize job state from project configuration."""
        scrape_config = project.scrape_job
        self.seed_urls = [str(normalize_url(url)) for url in scrape_config.seed_urls]
        self.domain_restricted = scrape_config.domain_restricted
        self.path_restricted = scrape_config.path_restricted
        self.exclusion_patterns = scrape_config.exclusion_patterns
        self.max_pages = scrape_config.max_pages
        self.max_depth = scrape_config.max_depth
        self.output_dir = output_dir
        self.discovered_urls = set()
        self.scraped_urls = set()
        self.unique_files = set()
        self.pages_scraped = 0
        self.max_depth_reached = 0

    def should_scrape_url(self, url: str, depth: int) -> bool:
        """Determine if a URL should be scraped based on various restrictions."""
        # Check if URL has already been scraped
        if url in self.scraped_urls:
            return False

        # Check depth limit
        if self.max_depth is not None and depth > self.max_depth:
            return False

        # Check page limit
        if self.max_pages is not None and self.pages_scraped >= self.max_pages:
            return False

        # Check URL restrictions
        for seed_url in self.seed_urls:
            if should_follow_url(url, seed_url, self.domain_restricted, self.path_restricted, self.exclusion_patterns):
                return True

        return False

    def _save_page(self, page: Page) -> None:
        """Save a scraped page to a file."""
        # Generate filename
        filename = self._generate_filename(page.url, page.title)
        filepath = os.path.join(self.output_dir, filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write content to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(page.content)
            
        logging.info(f"Successfully scraped {page.url} to {filepath}")
        
    def _generate_filename(self, url: str, title: str) -> str:
        """Generate a filename for the scraped content."""
        # Remove any URL fragments/anchors
        base_url = url.split('#')[0]
        
        # Try to use title if available, otherwise use URL path
        if title and title.strip():
            name = title.strip()
        else:
            path = urlparse(base_url).path
            name = path.strip('/').replace('/', '_') or 'index'
            
        # Clean the filename
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '-', name)
        
        return f"{name}"

    def process_page(self, page: Page, depth: int) -> None:
        """Process a scraped page."""
        # Save the page
        self._save_page(page)

        # Update state
        self.scraped_urls.add(str(page.url))
        self.pages_scraped += 1
        self.max_depth_reached = max(self.max_depth_reached, depth)

        # Log progress
        logging.info(f"Progress: {self.pages_scraped}/{self.max_pages} pages scraped")
