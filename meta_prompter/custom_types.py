from typing import List, Optional, Dict, Set
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
import logging

class Page(BaseModel):
    url: str
    done: bool = False
    scraped_at: Optional[datetime] = None

    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, other):
        if not isinstance(other, Page):
            return False
        return self.url == other.url
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_url

    @classmethod
    def validate_url(cls, v):
        if isinstance(v, HttpUrl):
            return str(v)
        return v

class ScraperResponse(BaseModel):
    content: str = Field(..., description="The main textual content extracted from the page.")
    links: Optional[List[str]] = Field(default_factory=list, description="List of URLs extracted from the page, if available.")
    images: Optional[List[str]] = Field(default_factory=list, description="List of image URLs extracted from the page, if available.")

class ScrapingJob(BaseModel):
    name: str = Field(..., description="Name of the scraping job")
    seed_urls: List[HttpUrl] = Field(..., description="Initial URLs to start scraping from")
    pages: Set[Page] = Field(default_factory=set, description="All pages discovered and their status")
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    domain_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same domain as seed URLs")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    max_pages: Optional[int] = Field(default=None, description="Maximum number of pages to scrape (None for unlimited)")

    def add_urls(self, urls: List[str]) -> List[str]:
        """
        Add multiple URLs to the job if they meet criteria
        Returns list of URLs that were actually added
        """
        added_urls = []
        for url in urls:
            if self.max_pages and len(self.pages) >= self.max_pages:
                logging.info(f"Maximum pages limit ({self.max_pages}) reached")
                break

            if not self.is_url_scraped(url) and self.should_scrape_url(url):
                self.pages.add(Page(url=str(url)))
                added_urls.append(url)
        
        return added_urls
    
    def mark_page_done(self, url: str) -> None:
        """Mark a page as scraped with timestamp"""
        old_page = next((p for p in self.pages if p.url == url), None)
        if old_page:
            self.pages.remove(old_page)
            self.pages.add(Page(url=url, done=True, scraped_at=datetime.now()))
        self.updated_at = datetime.now()
    
    def get_pending_urls(self) -> List[str]:
        """Get list of URLs that haven't been scraped yet"""
        return [str(page.url) for page in self.pages if not page.done]
    
    def is_url_scraped(self, url: str) -> bool:
        """Check if a URL has already been scraped"""
        return any(page.done and str(page.url) == str(url) for page in self.pages)
    
    def should_scrape_url(self, url: str) -> bool:
        """Determine if a URL should be scraped based on job settings"""
        try:
            if self.domain_restricted:
                # Get domains from seed URLs
                seed_domains = {HttpUrl(seed_url).host for seed_url in self.seed_urls}
                new_domain = HttpUrl(url).host
                return new_domain in seed_domains
            return True
        except Exception as e:
            logging.warning(f"Invalid URL {url}: {str(e)}")
            return False

    def get_statistics(self) -> dict:
        """Get current job statistics"""
        return {
            "total_pages_discovered": len(self.pages),
            "pages_scraped": len([p for p in self.pages if p.done]),
            "pages_pending": len(self.get_pending_urls()),
            "running_time": (datetime.now() - self.created_at).total_seconds()
        }
