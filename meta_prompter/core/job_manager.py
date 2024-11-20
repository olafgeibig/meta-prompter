from typing import Dict, Set, List
from threading import Lock
from ..models.page import Page
from ..models.scrape_job import ScrapeJobConfig
from .url_processor import normalize_url, should_scrape_url

class ThreadSafeJobState:
    """Thread-safe state management for scraping jobs."""
    
    def __init__(self, config: ScrapeJobConfig):
        self._lock = Lock()  # Single lock for all state
        self._pages: Set[Page] = set()
        self._url_depths: Dict[str, int] = {}
        self._pending_urls: Set[str] = set()
        self.config = config

        # Initialize with seed URLs
        for url in config.seed_urls:
            url_str = str(url).rstrip('/')
            with self._lock:
                self._url_depths[url_str] = 0
                self._pages.add(Page(project_id=config.name, url=url_str))
                self._pending_urls.add(url_str)

    def _check_max_pages(self) -> bool:
        """Check if max pages limit has been reached."""
        if self.config.max_pages is None:
            return False
        scraped_count = len([p for p in self._pages if p.done])
        return scraped_count >= self.config.max_pages

    def add_urls(self, urls: List[str], source_url: str) -> List[str]:
        """Add multiple URLs to the job if they meet criteria."""
        added_urls = []
        source_url = normalize_url(source_url)
        
        with self._lock:
            # Check max pages first
            if self._check_max_pages():
                return added_urls

            source_depth = self._url_depths.get(source_url, 0)
            new_depth = source_depth + 1

            # Check max depth before processing URLs
            if self.config.max_depth is not None and new_depth > self.config.max_depth:
                return added_urls

            scraped_urls = {normalize_url(str(p.url)) for p in self._pages if p.done}
            all_urls = {normalize_url(str(p.url)) for p in self._pages}
            
            # Process URLs in batches to maintain max pages limit
            remaining_slots = self.config.max_pages - len(scraped_urls)
            processed_count = 0
            
            for url in urls:
                if processed_count >= remaining_slots:
                    break
                    
                normalized_url = normalize_url(url)
                if normalized_url not in all_urls and should_scrape_url(normalized_url, self.config, scraped_urls):
                    self._pages.add(Page(url=normalized_url, project_id=self.config.name))
                    self._url_depths[normalized_url] = new_depth
                    self._pending_urls.add(normalized_url)
                    added_urls.append(normalized_url)
                    processed_count += 1
        
        return added_urls

    def mark_done(self, url: str, filename: str = None, content_hash: str = None) -> None:
        """Mark a page as scraped with optional metadata."""
        with self._lock:
            old_page = next((p for p in self._pages if p.url == url), None)
            if old_page:
                self._pages.remove(old_page)
                self._pages.add(Page(
                    project_id=self.config.name,
                    url=url,
                    done=True,
                    filename=filename or old_page.filename,
                    content_hash=content_hash or old_page.content_hash
                ))
                self._pending_urls.discard(url)

    def get_pending_urls(self) -> List[str]:
        """Get list of URLs that haven't been scraped yet."""
        with self._lock:
            if self._check_max_pages():
                self._pending_urls.clear()
                return []
            return list(self._pending_urls)

    def get_statistics(self) -> dict:
        """Get current job statistics."""
        with self._lock:
            unique_urls = {normalize_url(str(page.url)) for page in self._pages}
            scraped_pages = [p for p in self._pages if p.done]
            scraped_urls = {normalize_url(str(page.url)) for page in scraped_pages}
            max_depth = max(self._url_depths.values()) if self._url_depths else 0
            
            return {
                "total_unique_pages": len(unique_urls),
                "unique_pages_scraped": len(scraped_urls),
                "pages_pending": len(self._pending_urls),
                "max_depth_reached": max_depth,
                "max_pages": self.config.max_pages or float('inf')
            }
