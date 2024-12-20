import os
import requests
from dotenv import load_dotenv
from .models import ScrapeResponse


class JinaReader:
    """Client for the Jina Reader API."""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY not found in .env file")
        self.base_url = "https://r.jina.ai/"

    def scrape_website(self, url: str) -> ScrapeResponse:
        """Scrape a website using Jina Reader API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-No-Cache": "true",
            "X-With-Links-Summary": "true",
        }

        payload = {
            "url": str(url),  # Convert URL to string
            "options": "Markdown",
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()

            # Parse the content and links from the API response
            data = response.json().get("data", {})
            content = data.get("content", "")
            links = data.get("links", {})

            return ScrapeResponse(
                content=content,
                links=list(links.values()) if isinstance(links, dict) else [],
                images=[],  # Add empty images list to match updated model
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to scrape {url}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing response for {url}: {str(e)}")
