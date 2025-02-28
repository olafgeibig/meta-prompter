from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class ScrapeResponse(BaseModel):
    """Response from Jina Reader API."""

    content: str = Field(
        ..., description="The main textual content extracted from the page."
    )
    links: List[str] = Field(
        default_factory=list, description="List of URLs extracted from the page."
    )
    images: List[str] = Field(
        default_factory=list, description="List of image URLs extracted from the page."
    )


class ScraperConfig(BaseModel):
    """Configurable settings for web scrapers."""
    
    # Basic settings
    max_depth: int = Field(3, description="Maximum crawl depth")
    max_pages: int = Field(50, description="Maximum number of pages to scrape")
    seed_urls: List[str] = Field(default_factory=list, description="Initial URLs to start crawling")
    
    # Domain and path restrictions
    path_pattern: Optional[str] = Field(None, description="Regex pattern for URL paths to follow")
    exclude_domains: List[str] = Field(default_factory=list, description="List of domains to block")
    exclude_external_links: bool = Field(True, description="Stay within the same domain")
    exclude_social_media_links: bool = Field(True, description="Block social media links")
    
    # Browser and content configuration
    headless: bool = Field(True, description="Run browser invisibly")
    verbose: bool = Field(True, description="Enable detailed logging")
    word_count_threshold: int = Field(10, description="Filter out short text snippets")
    cache_mode: bool = Field(True, description="Enable caching for efficiency")
    css_selector: Optional[str] = Field(None, description="CSS selector to focus on specific content")
    
    # Markdown generation options
    content_filter_threshold: float = Field(0.45, description="Content quality threshold")
    body_width: int = Field(80, description="Wrap text at character count")
    ignore_links: bool = Field(False, description="Omit links from markdown")
    ignore_images: bool = Field(False, description="Omit images from markdown")


class ScrapingResult(BaseModel):
    """Standard result format for any scraper implementation."""
    
    url: str = Field(..., description="Source URL of the content")
    content: str = Field(..., description="Plain text content")
    markdown: str = Field(..., description="Markdown formatted content")
    depth: int = Field(0, description="Depth level in crawl tree")
    links: List[str] = Field(default_factory=list, description="Discovered links")
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp(), 
                             description="Time when scraped")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    success: bool = Field(True, description="Whether scraping was successful")
    error_message: Optional[str] = Field(None, description="Error message if unsuccessful")
