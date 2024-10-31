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

        return self._parse_response(response.json())

    def _parse_response(self, response: Dict[str, Any]) -> str:
        content = response["data"]["content"]
        
        # Add links summary if available
        if "links" in response["data"]:
            content += "\n\n## Links\n"
            for name, link in response["data"]["links"].items():
                content += f"- [{name}]({link})\n"

        # Add images summary if available
        if "images" in response["data"]:
            content += "\n\n## Images\n"
            for name, image_url in response["data"]["images"].items():
                content += f"- [{name}]({image_url})\n"

        return content