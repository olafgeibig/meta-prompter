import pytest
from datetime import datetime, timedelta
from meta_prompter.custom_types import ScrapingJob, Page

def test_scraping_job_depth_limit():
    """Test that scraping job respects depth limits"""
    job = ScrapingJob(
        name="test_depth",
        seed_urls=["https://example.com"],
        depth=2
    )
    
    # Simulate adding pages at different depths
    job.add_page("https://example.com")  # depth 0
    job.add_page("https://example.com/page1", "https://example.com")  # depth 1
    job.add_page("https://example.com/page2", "https://example.com/page1")  # depth 2
    
    # This should not be added (depth 3)
    result = job.add_page("https://example.com/page3", "https://example.com/page2")
    assert not result
    assert len(job.pages) == 3

def test_scraping_job_max_pages():
    """Test that scraping job respects maximum pages limit"""
    job = ScrapingJob(
        name="test_max",
        seed_urls=["https://example.com"],
        max_pages=2
    )
    
    assert job.add_page("https://example.com/page1")
    assert job.add_page("https://example.com/page2")
    assert not job.add_page("https://example.com/page3")
    assert len(job.pages) == 2

def test_scraping_job_domain_restriction():
    """Test domain restriction functionality"""
    job = ScrapingJob(
        name="test_domain",
        seed_urls=["https://example.com"],
        domain_restricted=True
    )
    
    assert job.should_scrape_url("https://example.com/page1")
    assert job.should_scrape_url("https://example.com/sub/page2")
    assert not job.should_scrape_url("https://other-domain.com")
    assert not job.should_scrape_url("invalid-url")

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
