from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Page(BaseModel):
    """Represents a scraped webpage."""
    project_id: str = Field(..., description="ID of the project this page belongs to")
    url: str = Field(..., description="Original URL where the page content was scraped from")
    filename: Optional[str] = Field(None, description="Local filename where the page content is stored")
    content_hash: Optional[str] = Field(None, description="Hash of the page content for change detection")
    done: bool = Field(False, description="Flag indicating if the page has been processed")
    created_at: datetime = Field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if not isinstance(other, Page):
            return False
        return self.url == other.url
