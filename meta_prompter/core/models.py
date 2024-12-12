from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class SpiderOptions(BaseModel):
    """Spider configuration options."""
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    restrict_domain: bool = Field(default=True, description="Restrict to domain of seed URL")
    restrict_path: bool = Field(default=True, description="Restrict to path of seed URL")
    max_depth: int = Field(default=5, description="How deep to crawl from seed URL")
    exclusion_patterns: List[str] = Field(
        default=[],
        description="URLs matching these patterns will be skipped"
    )

class ScrapeJobConfig(BaseModel):
    """Scraping job configuration."""
    name: str = Field(default="default", description="Name of the scraping job")
    seed_urls: List[HttpUrl] = Field(..., description="Starting URLs for scraping")
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    domain_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same domain as seed URLs")
    path_restricted: bool = Field(default=True, description="Whether to restrict scraping to the same path and below")
    max_pages: Optional[int] = Field(default=5, description="Maximum number of pages to scrape (None for unlimited)")
    max_depth: Optional[int] = Field(default=5, description="Maximum link depth from seed URLs (None for unlimited)")
    exclusion_patterns: List[str] = Field(default_factory=list, description="URLs matching these patterns will be skipped")

class CleaningConfig(BaseModel):
    """Cleaning phase configuration."""
    prompt: str = Field(..., description="Prompt template for cleaning documents")
    max_docs: int = Field(default=5, description="Maximum number of documents to clean in one run")
    model: str = Field(default="gemini/gemini-1.5-flash", description="Model to use for cleaning for LiteLLM")
    max_tokens: int = Field(default=128000, description="Maximum tokens for cleaning prompt")
    temperature: float = Field(default=0.1, description="Temperature for cleaning")

class GenerationJobConfig(BaseModel):
    """Generation job configuration."""
    prompt: str = Field(..., description="Prompt template for docs prompt generation")
    topic: str = Field(..., description="Topic of the docs prompt generation")
    model: str = Field(default="gemini/gemini-1.5-flash", description="Model to use for generation for LiteLLM")
    max_tokens: int = Field(default=128000, description="Maximum tokens for generation prompt")
    temperature: float = Field(default=0.1, description="Temperature for generation")

class Page(BaseModel):
    """Represents a scraped webpage."""
    project_id: str = Field(..., description="ID of the project this page belongs to")
    url: str = Field(..., description="Original URL where the page content was scraped from")
    filename: Optional[str] = Field(None, description="Local filename where the page content is stored")
    content_hash: Optional[str] = Field(None, description="Hash of the page content for change detection")
    done: bool = Field(False, description="Flag indicating if the page has been processed")
    created_at: datetime = Field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if not isinstance(other, Page):
            return False
        return self.url == other.url
