import os
import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any

class JinaReader:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("JINA_API_KEY not found in .env file")
        self.base_url = "https://r.jina.ai/"

    def read_website(self, url: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-No-Cache": "true",
            "X-With-Links-Summary": "true",
            # "X-With-Images-Summary": "true"
        }

        payload = {
            "url": url,
            "options": "Markdown"
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()

        # Parse the content and links from the API response
        data = response.json().get("data", {})
        content = data.get("content", "")
        links = data.get("links", {})

        return content, links