"""URL processing utilities for web scraping."""
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from pydantic import HttpUrl


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    domain1 = urlparse(url1).netloc
    domain2 = urlparse(url2).netloc
    return domain1 == domain2


def is_under_path(url: str, base_url: str) -> bool:
    """Check if a URL is under the path of the base URL."""
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    
    if parsed_url.netloc != parsed_base.netloc:
        return False
    
    url_path = parsed_url.path.rstrip('/')
    base_path = '/'.join(parsed_base.path.rstrip('/').split('/')[:-1])  # Get parent path
    
    return url_path.startswith(base_path)


def normalize_url(url: str, base_url: Optional[str] = None) -> HttpUrl:
    """Normalize a URL by joining it with a base URL if provided."""
    if base_url:
        url = urljoin(base_url, url)
    return HttpUrl(url)


def should_follow_url(url: str, seed_url: str, domain_restricted: bool, path_restricted: bool,
                     exclusion_patterns: Optional[List[str]] = None) -> bool:
    """Determine if a URL should be followed based on various restrictions."""
    if domain_restricted and not is_same_domain(url, seed_url):
        return False

    if path_restricted and not is_under_path(url, seed_url):
        return False

    if exclusion_patterns:
        for pattern in exclusion_patterns:
            if pattern in url:
                return False

    return True
