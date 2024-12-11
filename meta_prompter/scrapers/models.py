from typing import List, Optional
from pydantic import BaseModel, Field

class ScrapeResponse(BaseModel):
    """Response from Jina Reader API."""
    content: str = Field(..., description="The main textual content extracted from the page.")
    links: List[str] = Field(default_factory=list, description="List of URLs extracted from the page.")
    images: List[str] = Field(default_factory=list, description="List of image URLs extracted from the page.")
