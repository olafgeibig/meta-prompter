"""URL processing utilities for web scraping."""
from typing import Optional
from urllib.parse import urljoin, urlparse

from pydantic import HttpUrl
from meta_prompter.core.project import Project


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    domain1 = urlparse(url1).netloc
    domain2 = urlparse(url2).netloc
    return domain1 == domain2


def is_under_path(url: str, base_url: str) -> bool:
    """Check if a URL is under the path of the base URL.
    
    Args:
        url: URL to check
        base_url: Base URL to check against
        
    Returns:
        bool: True if url is under base_url's path
        
    Example:
        base_url: https://docs.example.com/guide/
        url: https://docs.example.com/guide/intro -> True
        url: https://docs.example.com/api -> False
    """
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    
    if parsed_url.netloc != parsed_base.netloc:
        return False
    
    # Normalize paths by stripping trailing slashes
    url_path = parsed_url.path.rstrip('/')
    base_path = parsed_base.path.rstrip('/')
    
    # Empty base path means root, which all paths are under
    if not base_path:
        return True
        
    # Check if URL path starts with base path
    return url_path.startswith(base_path)


def normalize_url(url: str, base_url: Optional[str] = None) -> HttpUrl:
    """Normalize a URL by joining it with a base URL if provided."""
    if base_url:
        url = urljoin(base_url, url)
    return HttpUrl(url)


def should_follow_url(url: str, seed_url: str, project: Project) -> bool:
    """Determine if a URL should be followed based on project configuration.
    
    Args:
        url: The URL to check
        seed_url: The reference seed URL to check against
        project: Project object containing scraping configuration
    """
    if project.scrape_job.domain_restricted and not is_same_domain(url, seed_url):
        return False

    if project.scrape_job.path_restricted and not is_under_path(url, seed_url):
        return False

    if project.scrape_job.exclusion_patterns:
        for pattern in project.scrape_job.exclusion_patterns:
            if pattern in url:
                return False
                
    return True
