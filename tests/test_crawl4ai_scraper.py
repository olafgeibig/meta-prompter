"""Tests for the Crawl4AI scraper implementation."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from meta_prompter.core.project import Project
from meta_prompter.scrapers.crawl4ai_scraper import Crawl4AIScraper
from meta_prompter.scrapers.models import ScrapingResult


class MockConfig(BaseModel):
    """Mock config for testing."""
    seed_urls: list[str] = ["https://example.com"]
    scraper_config: dict = {}


class MockProject:
    """Mock project for testing."""
    
    def __init__(self, tmp_path: Path):
        self.config = MockConfig()
        self.base_dir = tmp_path
        
    def get_scraped_dir(self) -> Path:
        """Get the scraped directory."""
        scraped_dir = self.base_dir / "scraped"
        scraped_dir.mkdir(exist_ok=True)
        return scraped_dir


@pytest.fixture
def mock_project(tmp_path):
    """Create a mock project."""
    return MockProject(tmp_path)


@pytest.fixture
def mock_crawl_result():
    """Create a mock crawl result."""
    result = MagicMock()
    result.success = True
    result.content = "Test content"
    result.markdown = "# Test markdown"
    result.title = "Test Title"
    result.language = "en"
    result.word_count = 100
    result.markdown_v2 = MagicMock()
    result.markdown_v2.fit_markdown = "# Test fit markdown"
    result.links = {
        "internal": [
            {"href": "https://example.com/page1"},
            {"href": "https://example.com/page2"}
        ]
    }
    return result


@pytest.mark.asyncio
async def test_scraper_initialization(mock_project):
    """Test that the scraper initializes correctly."""
    scraper = Crawl4AIScraper(mock_project)
    
    assert scraper.project == mock_project
    assert scraper.output_dir == mock_project.get_scraped_dir()
    assert len(scraper.scraped_urls) == 0
    assert len(scraper.url_depths) == 0
    assert len(scraper.discovered_urls) == 0
    assert isinstance(scraper.config, dict)
    assert scraper.config["max_depth"] == 3  # Default value


@pytest.mark.asyncio
@patch("meta_prompter.scrapers.crawl4ai_scraper.AsyncWebCrawler")
async def test_scrape_url(MockAsyncWebCrawler, mock_project, mock_crawl_result):
    """Test that scrape_url works correctly."""
    # Setup mock crawler
    mock_crawler_instance = AsyncMock()
    mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
    MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
    
    # Create scraper and mock _save_results to avoid file operations
    scraper = Crawl4AIScraper(mock_project)
    scraper._save_results = AsyncMock()
    
    # Run scrape_url
    result = await scraper.scrape_url("https://example.com")
    
    # Verify the result
    assert isinstance(result, ScrapingResult)
    assert result.url == "https://example.com"
    assert result.content == "Test content"
    assert result.markdown == "# Test fit markdown"
    assert result.success is True
    assert len(result.links) == 2
    
    # Verify state updates
    assert "https://example.com" in scraper.scraped_urls
    assert scraper.url_depths["https://example.com"] == 0
    assert len(scraper.discovered_urls) == 2
    
    # Verify save was called
    scraper._save_results.assert_called_once()


@pytest.mark.asyncio
@patch("meta_prompter.scrapers.crawl4ai_scraper.AsyncWebCrawler")
async def test_scrape_url_failure(MockAsyncWebCrawler, mock_project):
    """Test that scrape_url handles failures correctly."""
    # Setup mock crawler with failed result
    mock_failed_result = MagicMock()
    mock_failed_result.success = False
    mock_failed_result.error_message = "Test error"
    
    mock_crawler_instance = AsyncMock()
    mock_crawler_instance.arun = AsyncMock(return_value=mock_failed_result)
    MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
    
    # Create scraper and mock _save_results to avoid file operations
    scraper = Crawl4AIScraper(mock_project)
    scraper._save_results = AsyncMock()
    
    # Run scrape_url
    result = await scraper.scrape_url("https://example.com")
    
    # Verify the result
    assert isinstance(result, ScrapingResult)
    assert result.url == "https://example.com"
    assert result.success is False
    assert result.error_message == "Test error"
    
    # Verify _save_results was not called (since it should skip failed results)
    scraper._save_results.assert_not_called()


@pytest.mark.asyncio
@patch.object(Crawl4AIScraper, "_crawl_recursive")
async def test_run(mock_crawl_recursive, mock_project):
    """Test that run calls _crawl_recursive with seed URLs."""
    # Create scraper
    scraper = Crawl4AIScraper(mock_project)
    mock_crawl_recursive.return_value = None
    
    # Run
    await scraper.run()
    
    # Verify _crawl_recursive was called with the seed URL
    mock_crawl_recursive.assert_called_once_with("https://example.com")


@pytest.mark.asyncio
@patch.object(Crawl4AIScraper, "scrape_url")
async def test_crawl_recursive(mock_scrape_url, mock_project):
    """Test that _crawl_recursive follows links correctly."""
    # Set up mock results
    result1 = ScrapingResult(
        url="https://example.com",
        content="Test content 1",
        markdown="Test markdown 1",
        depth=0,
        links=["https://example.com/page1", "https://example.com/page2"],
        success=True
    )
    
    result2 = ScrapingResult(
        url="https://example.com/page1",
        content="Test content 2",
        markdown="Test markdown 2",
        depth=1,
        links=[],
        success=True
    )
    
    mock_scrape_url.side_effect = [result1, result2, None]  # Third call returns None
    
    # Create scraper with a small max_pages to limit testing
    scraper = Crawl4AIScraper(mock_project)
    scraper.config["max_pages"] = 2
    
    # Run _crawl_recursive
    await scraper._crawl_recursive("https://example.com")
    
    # Verify scrape_url was called correctly
    assert mock_scrape_url.call_count >= 2
    
    # The first call should be with the start URL
    args1, _ = mock_scrape_url.call_args_list[0]
    assert args1[0] == "https://example.com"
    assert args1[1] == 0  # depth
    
    # The second call should be with one of the discovered URLs
    args2, _ = mock_scrape_url.call_args_list[1]
    assert args2[0] in ["https://example.com/page1", "https://example.com/page2"]
    assert args2[1] == 1  # depth


def test_get_stats(mock_project):
    """Test that get_stats returns the expected statistics."""
    scraper = Crawl4AIScraper(mock_project)
    
    # Add some fake data
    scraper.scraped_urls = {"https://example.com", "https://example.com/page1"}
    scraper.discovered_urls = {"https://example.com", "https://example.com/page1", "https://example.com/page2"}
    scraper.url_depths = {"https://example.com": 0, "https://example.com/page1": 1}
    
    # Get stats
    stats = scraper.get_stats()
    
    # Verify stats
    assert stats["urls_crawled"] == 2
    assert stats["urls_discovered"] == 3
    assert stats["max_depth_reached"] == 1
    assert "config" in stats