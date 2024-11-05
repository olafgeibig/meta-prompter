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

def test_scraping_job_depth_limit():
    """Test that scraping job respects depth limits from seed URLs"""
    job = ScrapingJob(
        name="test_depth",
        seed_urls=["https://example.com"],
        max_depth=2
    )
    
    # Simulate URL discovery at different depths
    # Depth 0 (seed URL)
    assert "https://example.com" in job.url_depths
    assert job.url_depths["https://example.com"] == 0
    
    # Depth 1
    depth1_urls = ["https://example.com/page1", "https://example.com/page2"]
    added1 = job.add_urls(depth1_urls, "https://example.com")
    assert len(added1) == 2
    assert all(job.url_depths[url] == 1 for url in added1)
    
    # Depth 2
    depth2_urls = ["https://example.com/page1/sub1", "https://example.com/page2/sub2"]
    added2 = job.add_urls(depth2_urls, "https://example.com/page1")
    assert len(added2) == 2
    assert all(job.url_depths[url] == 2 for url in added2)
    
    # Depth 3 (should not be added due to max_depth=2)
    depth3_urls = ["https://example.com/page1/sub1/deep"]
    added3 = job.add_urls(depth3_urls, "https://example.com/page1/sub1")
    assert len(added3) == 0

def test_scraping_job_statistics():
    """Test statistics gathering"""
    job = ScrapingJob(
        name="test_stats",
        seed_urls=["https://example.com"]
    )
    
    # Add some pages and mark some as done
    job.add_urls(["https://example.com/page1", "https://example.com/page2"])
    job.mark_page_done("https://example.com/page1")
    
    stats = job.get_statistics()
    assert stats["total_pages_discovered"] == 2
    assert stats["pages_scraped"] == 1
    assert stats["pages_pending"] == 1
