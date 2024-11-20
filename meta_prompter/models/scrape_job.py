from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class ScrapeJobConfig(BaseModel):
    """Configuration for a web scraping job."""
    name: str = Field(..., description="Name of the scraping job")
    seed_urls: List[HttpUrl] = Field(..., description="Initial URLs to start scraping from")
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    domain_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same domain as seed URLs")
    path_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same path and below")
    max_pages: Optional[int] = Field(default=None, description="Maximum number of pages to scrape (None for unlimited)")
    max_depth: Optional[int] = Field(default=None, description="Maximum link depth from seed URLs (None for unlimited)")
    exclusion_patterns: List[str] = Field(default_factory=list, description="URLs matching these patterns will be skipped")
