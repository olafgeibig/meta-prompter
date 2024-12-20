import pytest
from unittest.mock import patch, Mock
from meta_prompter.jina_reader import JinaReader
from meta_prompter.custom_types import ScraperResponse


@pytest.fixture
def mock_env_vars():
    with patch.dict("os.environ", {"JINA_API_KEY": "test_key"}):
        yield


@pytest.fixture
def jina_reader(mock_env_vars):
    return JinaReader()


def test_scrape_website_success(jina_reader):
    mock_response = {
        "data": {
            "content": "# Test Content\nSome text",
            "links": {"https://example.com": "Example"},
        }
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status = Mock()

        response = jina_reader.scrape_website("https://example.com")

        assert isinstance(response, ScraperResponse)
        assert response.content == "# Test Content\nSome text"
        assert response.links == ["https://example.com"]


def test_scrape_website_no_links(jina_reader):
    mock_response = {"data": {"content": "# Test Content\nSome text", "links": {}}}

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status = Mock()

        response = jina_reader.scrape_website("https://example.com")

        assert isinstance(response, ScraperResponse)
        assert response.content == "# Test Content\nSome text"
        assert response.links == []


def test_scrape_website_error(jina_reader):
    with patch("requests.post") as mock_post:
        mock_post.return_value.raise_for_status.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            jina_reader.scrape_website("https://example.com")
