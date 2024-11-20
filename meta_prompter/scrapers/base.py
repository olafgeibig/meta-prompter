from abc import ABC, abstractmethod
from typing import Optional
from ..models.scrape_job import ScrapeJobConfig
from ..core.job_manager import ThreadSafeJobState

class BaseScraper(ABC):
    """Base class for web scrapers."""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or 3
    
    @abstractmethod
    def scrape(self, config: ScrapeJobConfig) -> None:
        """Run the scraper with the given configuration."""
        pass
