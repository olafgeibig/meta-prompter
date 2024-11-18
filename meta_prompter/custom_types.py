from typing import List, Optional, Dict, Set
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
import logging

class Project(BaseModel):
    name: str = Field(..., description="Name of the project")
    description: str = Field(..., description="Description of the project.")
    created: datetime = Field(default_factory=datetime.now)
    project_dir: str

class Page(BaseModel):
    project_id: str = Field(..., description="ID of the project this page belongs to")
    url: str = Field(..., description="Original URL where the page content was scraped from")
    filename: Optional[str] = Field(None, description="Local filename where the page content is stored")
    content_hash: Optional[str] = Field(None, description="Hash of the page content for change detection")
    done: bool = Field(False, description="Flag indicating if the page has been processed")

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

class ScrapeResponse(BaseModel):
    content: str = Field(..., description="The main textual content extracted from the page.")
    links: Optional[List[str]] = Field(default_factory=list, description="List of URLs extracted from the page, if available.")
    images: Optional[List[str]] = Field(default_factory=list, description="List of image URLs extracted from the page, if available.")

class ScrapeJob(BaseModel):
    name: str = Field(..., description="Name of the scraping job")
    seed_urls: List[HttpUrl] = Field(..., description="Initial URLs to start scraping from")
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    domain_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same domain as seed URLs")
    path_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same path and below")
    max_pages: Optional[int] = Field(default=None, description="Maximum number of pages to scrape (None for unlimited)")
    max_depth: Optional[int] = Field(default=None, description="Maximum link depth from seed URLs (None for unlimited)")
    exclusion_patterns: Optional[List[str]] = Field(default_factory=list, description="URLs matching these patterns will be skipped") 
    pages: Set[Page] = Field(default_factory=set, description="All pages discovered and their status")
    url_depths: Dict[str, int] = Field(default_factory=dict, exclude=True)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize depth tracking for seed URLs
        for url in self.seed_urls:
            url_str = str(url).rstrip('/')
            self.url_depths[url_str] = 0
            # Create initial Page objects for seed URLs
            page = Page(
                project_id=self.name,
                url=url_str,
            )
            self.pages.add(page)

    def normalize_url(self, url: str) -> str:
        """Remove fragments and trailing slashes from URL"""
        try:
            url_obj = HttpUrl(url)
            # Reconstruct URL without fragment
            normalized = f"{url_obj.scheme}://{url_obj.host}{url_obj.path}"
            if url_obj.query:
                normalized += f"?{url_obj.query}"
            return normalized.rstrip('/')
        except Exception as e:
            logging.warning(f"Invalid URL {url}: {str(e)}")
            return url.split('#')[0].rstrip('/')  # Fallback to simple fragment removal

    def add_urls(self, urls: List[str], source_url: str) -> List[str]:
        """
        Add multiple URLs to the job if they meet criteria
        Returns list of URLs that were actually added
        """
        added_urls = []
        source_url = self.normalize_url(source_url)
        source_depth = self.url_depths.get(source_url, 0)
        new_depth = source_depth + 1

        # Check max depth before processing URLs
        if self.max_depth is not None and new_depth > self.max_depth:
            logging.info(f"Maximum depth ({self.max_depth}) reached for URLs from {source_url}")
            return added_urls

        for url in urls:
            normalized_url = self.normalize_url(url)
            
            # Check max pages using unique normalized URLs count
            if self.max_pages and self.get_unique_pages_count() >= self.max_pages:
                logging.info(f"Maximum unique pages limit ({self.max_pages}) reached")
                break

            if not self.is_url_scraped(normalized_url) and self.should_scrape_url(normalized_url):
                self.pages.add(Page(url=normalized_url, project_id=self.name))
                self.url_depths[normalized_url] = new_depth
                added_urls.append(normalized_url)
        
        return added_urls

    def get_unique_pages_count(self) -> int:
        """Count unique pages (ignoring fragments)"""
        unique_urls = {self.normalize_url(str(page.url)) for page in self.pages}
        return len(unique_urls)

    def add_page(self, url: str) -> bool:
        """
        Legacy method for compatibility - adds a single page
        Returns True if page was added, False otherwise
        """
        added = self.add_urls([url])
        return bool(added)
    
    def mark_page_done(self, url: str) -> None:
        """Mark a page as scraped with timestamp"""
        old_page = next((p for p in self.pages if p.url == url), None)
        if old_page:
            self.pages.remove(old_page)
            # Create new page with all required fields
            self.pages.add(Page(
                project_id=self.name,
                url=url,
                done=True,
                filename=old_page.filename,
                content_hash=old_page.content_hash
            ))
    
    def get_pending_urls(self) -> List[str]:
        """Get list of URLs that haven't been scraped yet"""
        return [str(page.url) for page in self.pages if not page.done]
    
    def is_url_scraped(self, url: str) -> bool:
        """Check if a URL has already been scraped"""
        normalized_url = self.normalize_url(url)
        return any(page.done and self.normalize_url(str(page.url)) == normalized_url for page in self.pages)
    
    def should_scrape_url(self, url: str) -> bool:
        """Determine if a URL should be scraped based on job settings"""
        try:
            url_obj = HttpUrl(url)
            
            # Check domain restriction
            if self.domain_restricted:
                seed_domains = {HttpUrl(seed_url).host for seed_url in self.seed_urls}
                if url_obj.host not in seed_domains:
                    logging.debug(f"Skipping {url} - domain {url_obj.host} not in {seed_domains}")
                    return False
            
            # Check path restriction
            if self.path_restricted:
                seed_paths = {HttpUrl(seed_url).path.split('/')[1] for seed_url in self.seed_urls if HttpUrl(seed_url).path.split('/')[1:]}
                url_parts = url_obj.path.split('/')
                if len(url_parts) > 1 and url_parts[1]:
                    if url_parts[1] not in seed_paths:
                        logging.debug(f"Skipping {url} - path {url_parts[1]} not in {seed_paths}")
                        return False
            
            # Check exclusion patterns
            for pattern in self.exclusion_patterns:
                if pattern in url:
                    logging.debug(f"Skipping {url} - matches exclusion pattern {pattern}")
                    return False
            
            return True
        except Exception as e:
            logging.warning(f"Invalid URL {url}: {str(e)}")
            return False

    def get_statistics(self) -> dict:
        """Get current job statistics"""
        max_depth_reached = max(self.url_depths.values()) if self.url_depths else 0
        unique_pages = {self.normalize_url(str(page.url)) for page in self.pages}
        unique_scraped = {self.normalize_url(str(page.url)) for page in self.pages if page.done}
        
        return {
            "total_unique_pages": len(unique_pages),
            "unique_pages_scraped": len(unique_scraped),
            "pages_pending": len(self.get_pending_urls()),
            "max_depth_reached": max_depth_reached,
        }

class MetaPrompt(BaseModel):
    name: str
    description: str
    prompt: str
