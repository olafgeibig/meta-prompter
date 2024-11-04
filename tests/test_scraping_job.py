import pytest
from datetime import datetime, timedelta
from meta_prompter.custom_types import ScrapingJob, Page

def test_scraping_job_max_pages():
    """Test that scraping job respects maximum pages limit"""
    job = ScrapingJob(
        name="test_max",
        seed_urls=["https://example.com"],
        max_pages=2
    )
    
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3"
    ]
    
    added_urls = job.add_urls(urls)
    assert len(added_urls) == 2
    assert len(job.pages) == 2

def test_scraping_job_domain_restriction():
    """Test domain restriction functionality"""
    job = ScrapingJob(
        name="test_domain",
        seed_urls=["https://example.com"],
        domain_restricted=True
    )
    
    urls = [
        "https://example.com/page1",
        "https://example.com/sub/page2",
        "https://other-domain.com",
        "invalid-url"
    ]
    
    added_urls = job.add_urls(urls)
    assert len(added_urls) == 2
    assert all(url.startswith("https://example.com") for url in added_urls)

def test_scraping_job_statistics():
    """Test statistics gathering"""
    job = ScrapingJob(
        name="test_stats",
        seed_urls=["https://example.com"]
    )
    
    # Add some pages and mark some as done
    job.add_page("https://example.com/page1")
    job.add_page("https://example.com/page2")
    job.mark_page_done("https://example.com/page1")
    
    stats = job.get_statistics()
    assert stats["total_pages_discovered"] == 2
    assert stats["pages_scraped"] == 1
    assert stats["pages_pending"] == 1
