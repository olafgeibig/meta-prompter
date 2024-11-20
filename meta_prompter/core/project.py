from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import shutil
from pydantic import BaseModel, Field, HttpUrl

class SpiderOptions(BaseModel):
    """Spider configuration options."""
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    restrict_domain: bool = Field(default=True, description="Restrict to domain of seed URL")
    restrict_path: bool = Field(default=True, description="Restrict to path of seed URL")
    max_depth: int = Field(default=5, description="How deep to crawl from seed URL")
    exclusion_patterns: List[str] = Field(
        default=[],
        description="URLs matching these patterns will be skipped"
    )

class ScrapeJobConfig(BaseModel):
    """Scraping job configuration."""
    seed_urls: List[HttpUrl] = Field(..., description="Starting URLs for scraping")
    max_pages: int = Field(default=5, description="Maximum number of pages to scrape")
    spider_options: SpiderOptions = Field(default_factory=SpiderOptions)

class CleaningConfig(BaseModel):
    """Cleaning phase configuration."""
    prompt: str = Field(..., description="Prompt template for cleaning documents")
    max_docs: int = Field(default=5, description="Maximum number of documents to clean in one run")
    model: str = Field(default="gemini/gemini-1.5-flash", description="Model to use for cleaning for LiteLLM")
    max_tokens: int = Field(default=128000, description="Maximum tokens for cleaning prompt")
    temperature: float = Field(default=0.1, description="Temperature for cleaning")

class GenerationJobConfig(BaseModel):
    """Generation job configuration."""
    prompt: str = Field(..., description="Prompt template for generation")
    model: str = Field(default="gemini/gemini-1.5-flash", description="Model to use for generation for LiteLLM")
    max_tokens: int = Field(default=128000, description="Maximum tokens for generation prompt")
    temperature: float = Field(default=0.1, description="Temperature for generation")

class Project(BaseModel):
    """Project configuration."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    created: datetime = Field(default_factory=datetime.now)
    path: Path = Field(default=None, description="Project directory path")
    scrape_job: ScrapeJobConfig
    cleaning: CleaningConfig
    generation_jobs: Dict[str, GenerationJobConfig] = Field(default_factory=dict)

    @property
    def scraped_dir(self) -> Path:
        """Get the scraped content directory path."""
        return self.path / "scraped"

    @property
    def cleaned_dir(self) -> Path:
        """Get the cleaned content directory path."""
        return self.path / "cleaned"

    @property
    def staged_dir(self) -> Path:
        """Get the staged content directory path."""
        return self.path / "staged"

    @property
    def meta_prompts_dir(self) -> Path:
        """Get the meta-prompts directory path."""
        return self.path / "meta_prompts"

    def stage_documents(self, source: str) -> Tuple[int, str]:
        """
        Stage documents from either scraped or cleaned directory.

        Args:
            source: Either 'scraped' or 'cleaned'

        Returns:
            Tuple of (number of files staged, error message if any)

        Raises:
            ValueError: If source directory doesn't exist or no files found
        """
        source_dir = self.scraped_dir if source == 'scraped' else self.cleaned_dir

        if not source_dir.exists():
            raise ValueError(f"Source directory {source_dir} does not exist")

        if not any(source_dir.iterdir()):
            raise ValueError(f"No documents found in {source_dir}")

        # Create staged directory if it doesn't exist
        self.staged_dir.mkdir(exist_ok=True)

        # Clear existing staged files
        for existing in self.staged_dir.iterdir():
            if existing.is_file():
                existing.unlink()

        # Copy files to staged directory
        moved_count = 0
        for file in source_dir.iterdir():
            if file.is_file() and file.suffix == '.md':
                target = self.staged_dir / file.name
                shutil.copy2(file, target)
                moved_count += 1

        if moved_count == 0:
            raise ValueError("No markdown files found to stage")

        return moved_count, f"Successfully staged {moved_count} documents from {source} directory"

    def add_generation_job(self, job_name: str, prompt: Optional[str] = None,
                           model: Optional[str] = None, max_tokens: Optional[int] = None,
                           temperature: Optional[float] = None) -> str:
        """
        Add a new generation job configuration.

        Args:
            job_name: Name of the generation job
            prompt: Optional prompt template
            model: Optional model identifier
            max_tokens: Optional maximum tokens
            temperature: Optional temperature setting

        Returns:
            Success message

        Raises:
            ValueError: If job already exists
        """
        if job_name in self.generation_jobs:
            raise ValueError(f"Generation job {job_name} already exists")

        self.generation_jobs[job_name] = GenerationJobConfig(
            prompt=prompt or "Generate documentation from the following content: {content}",
            model=model or "gemini/gemini-1.5-flash",
            max_tokens=max_tokens or 128000,
            temperature=temperature or 0.1
        )

        return f"Created generation job: {job_name}"

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Project":
        """Load project configuration from YAML file."""
        import yaml
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
            # Set project path to yaml file's parent directory
            config_dict['path'] = yaml_path.parent
        return cls(**config_dict)

    def to_yaml(self, yaml_path: Path) -> None:
        """Save project configuration to YAML file."""
        import yaml
        config_dict = self.model_dump(exclude={'path'})
        # Convert datetime to string for YAML serialization
        config_dict['created'] = self.created.isoformat()
        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f, sort_keys=False, indent=2)
