from typing import Set
from pydantic import HttpUrl
import logging
from urllib.parse import urljoin

def normalize_url(url: str) -> str:
    """Remove fragments and trailing slashes from URL."""
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

def make_absolute_url(base_url: str, relative_url: str) -> str:
    """Convert a relative URL to an absolute URL."""
    if relative_url.startswith(('http://', 'https://')):
        return relative_url
    return urljoin(base_url, relative_url)

def should_scrape_url(url: str, config: 'ScrapeJobConfig', scraped_urls: Set[str]) -> bool:
    """Determine if a URL should be scraped based on job settings."""
    try:
        if url in scraped_urls:
            return False

        url_obj = HttpUrl(url)
        
        # Check domain restriction
        if config.domain_restricted:
            seed_domains = {HttpUrl(seed_url).host for seed_url in config.seed_urls}
            if url_obj.host not in seed_domains:
                logging.debug(f"Skipping {url} - domain {url_obj.host} not in {seed_domains}")
                return False
        
        # Check path restriction
        if config.path_restricted:
            seed_paths = {HttpUrl(seed_url).path.split('/')[1] for seed_url in config.seed_urls if HttpUrl(seed_url).path.split('/')[1:]}
            url_parts = url_obj.path.split('/')
            if len(url_parts) > 1 and url_parts[1]:
                if url_parts[1] not in seed_paths:
                    logging.debug(f"Skipping {url} - path {url_parts[1]} not in {seed_paths}")
                    return False
        
        # Check exclusion patterns
        for pattern in config.exclusion_patterns:
            if pattern in url:
                logging.debug(f"Skipping {url} - matches exclusion pattern {pattern}")
                return False
        
        return True
    except Exception as e:
        logging.warning(f"Invalid URL {url}: {str(e)}")
        return False
