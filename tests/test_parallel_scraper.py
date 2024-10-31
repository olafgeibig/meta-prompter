import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from meta_prompter.parallel_scraper import ParallelScraper

@pytest.fixture
def scraper():
    return ParallelScraper(max_scrapers=2, output_dir=Path("test_output"))

@pytest.fixture
def mock_jina_reader():
    with patch('meta_prompter.parallel_scraper.JinaReader') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.read_website.return_value = "# Test Title\nTest content"
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
    
    scraper._scrape_single_url(test_url)
    
    # Verify JinaReader was called correctly
    mock_jina_reader.read_website.assert_called_once_with(test_url)
    
    # Verify file was created with correct content
    output_file = tmp_path / "Test_Title.md"
    assert output_file.exists()
    assert output_file.read_text() == "# Test Title\nTest content"

def test_scrape_urls(scraper, mock_jina_reader, tmp_path):
    """Test scraping multiple URLs in parallel"""
    scraper.output_dir = tmp_path
    test_urls = [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]
    
    scraper.scrape_urls(test_urls)
    
    # Verify JinaReader was called for each URL
    assert mock_jina_reader.read_website.call_count == len(test_urls)
    
    # Verify files were created
    assert len(list(tmp_path.glob("*.md"))) == len(test_urls)

def test_error_handling(scraper, mock_jina_reader, tmp_path, caplog):
    """Test error handling during scraping"""
    scraper.output_dir = tmp_path
    test_url = "https://example.com/error"
    
    # Make the reader raise an exception
    mock_jina_reader.read_website.side_effect = Exception("Test error")
    
    scraper._scrape_single_url(test_url)
    
    # Verify error was logged
    assert "Error scraping" in caplog.text
    assert "Test error" in caplog.text
