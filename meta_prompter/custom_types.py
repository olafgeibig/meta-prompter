from typing import List, Optional
from pydantic import BaseModel, Field

class ScraperResponse(BaseModel):
    content: str = Field(..., description="The main textual content extracted from the page.")
    links: Optional[List[str]] = Field(default_factory=list, description="List of URLs extracted from the page, if available.")
    images: Optional[List[str]] = Field(default_factory=list, description="List of image URLs extracted from the page, if available.")
