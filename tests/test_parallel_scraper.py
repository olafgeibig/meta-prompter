import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch
from meta_prompter.parallel_scraper import ParallelScraper
from meta_prompter.custom_types import ScraperResponse, ScrapingJob


@pytest.fixture
def scraper(mock_jina_reader):
    return ParallelScraper(
        max_scrapers=2, output_dir=Path("test_output"), jina_reader=mock_jina_reader
    )


@pytest.fixture
def mock_jina_reader():
    with patch("meta_prompter.parallel_scraper.JinaReader") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.scrape_website.return_value = ScraperResponse(
            content="# Test Title\nTest content", links=[]
        )
        yield mock_instance


def test_sanitize_filename(scraper):
    """Test filename sanitization"""
    test_cases = [
        ("Simple Title", "Simple_Title.md"),
        ("Title with: invalid chars?", "Title_with_invalid_chars.md"),
        ("Title/with\\slashes", "Titlewithslashes.md"),
    ]
    for input_title, expected in test_cases:
        assert scraper._sanitize_filename(input_title) == expected


def test_scrape_single_url(scraper, mock_jina_reader, tmp_path):
    """Test scraping a single URL"""
    scraper.output_dir = tmp_path
    test_url = "https://example.com/test"

    job = ScrapingJob(name="test_job", seed_urls=[test_url])
    scraper._scrape_single_url(test_url, job)

    # Verify JinaReader was called correctly
    mock_jina_reader.scrape_website.assert_called_once_with(test_url)

    # Verify file was created with correct content
    output_file = tmp_path / "Test_Title.md"
    assert output_file.exists()
    assert output_file.read_text() == "# Test Title\nTest content"


def test_error_handling(scraper, mock_jina_reader, tmp_path, caplog):
    """Test error handling during scraping"""
    caplog.set_level(logging.ERROR)
    scraper.output_dir = tmp_path
    test_url = "https://example.com/error"

    # Make the reader raise an exception
    mock_jina_reader.scrape_website.side_effect = Exception("Test error")

    job = ScrapingJob(name="test_job", seed_urls=[test_url])
    scraper._scrape_single_url(test_url, job)

    # Verify error was logged
    assert "Error scraping" in caplog.text
    assert "Test error" in caplog.text


def test_no_duplicate_scraping(scraper, mock_jina_reader, tmp_path):
    """Test that URLs are never scraped more than once"""
    scraper.output_dir = tmp_path
    test_urls = ["https://example.com/1"]

    # Configure mock to return a response with links
    mock_jina_reader.scrape_website.return_value = ScraperResponse(
        content="# Test Title\nTest content",
        links=["https://example.com/2", "https://example.com/3"],
    )

    # Create a job and run the spider multiple times
    job = ScrapingJob(name="test_no_duplicates", seed_urls=test_urls, follow_links=True)

    # Run spider twice
    scraper.run_spider(job)
    scraper.run_spider(job)  # Second run should not re-scrape anything

    # Verify each URL was only scraped once
    call_urls = [call[0][0] for call in mock_jina_reader.scrape_website.call_args_list]
    unique_urls = set(call_urls)
    assert len(call_urls) == len(unique_urls), "Some URLs were scraped multiple times"

    # Verify all discovered pages are marked as done
    assert all(page.done for page in job.pages), "Not all pages were marked as done"

    # Verify statistics
    stats = job.get_statistics()
    assert (
        stats["pages_scraped"] == stats["total_pages_discovered"]
    ), "Not all discovered pages were scraped"
