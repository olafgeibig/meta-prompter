from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, HttpUrl

class SpiderOptions(BaseModel):
    """Spider configuration options."""
    follow_links: bool = Field(default=True, description="Whether to follow links found in pages")
    restrict_domain: bool = Field(default=True, description="Restrict to domain of seed URL")
    restrict_path: bool = Field(default=True, description="Restrict to path of seed URL")
    max_depth: int = Field(default=3, description="How deep to crawl from seed URL")
    exclusion_patterns: List[str] = Field(
        default=["*/api/*", "*/changelog/*", "*/legacy/*"],
        description="URLs matching these patterns will be skipped"
    )

class ScrapeJobConfig(BaseModel):
    """Scraping job configuration."""
    seed_urls: List[HttpUrl] = Field(..., description="Starting URLs for scraping")
    max_pages: int = Field(default=100, description="Maximum number of pages to scrape")
    spider_options: SpiderOptions = Field(default_factory=SpiderOptions)
    output_dir: str = Field(default="scrape_output", description="Directory to store scraped content")

class CleaningConfig(BaseModel):
    """Cleaning phase configuration."""
    prompt: str = Field(..., description="Prompt template for cleaning documents")
    max_docs: int = Field(default=10, description="Maximum number of documents to clean in one run")
    output_dir: str = Field(default="clean_output", description="Directory to store cleaned content")
    skip_cleaning: bool = Field(default=False, description="Skip cleaning phase if content is already clean")

class GenerationJobConfig(BaseModel):
    """Generation job configuration."""
    prompt: str = Field(..., description="Prompt template for generation")
    model: str = Field(default="gpt-4", description="Model to use for generation")
    max_tokens: int = Field(default=2000, description="Maximum tokens for generation output")
    temperature: float = Field(default=0.7, description="Temperature for generation")

class CostControl(BaseModel):
    """Cost control settings."""
    token_counting: bool = Field(default=True, description="Enable token counting before LLM operations")
    prompt_threshold: int = Field(default=1000, description="Prompt user if operation exceeds this token count")
    max_total_tokens: Optional[int] = Field(default=None, description="Maximum total tokens for the project")

class ProjectStatus(BaseModel):
    """Project status tracking."""
    current_phase: str = Field(default="init", description="Current project phase")
    scrape_complete: bool = Field(default=False, description="Whether scraping is complete")
    clean_complete: bool = Field(default=False, description="Whether cleaning is complete")
    staged_docs: List[str] = Field(default_factory=list, description="List of staged document paths")

class Project(BaseModel):
    """Project configuration."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    created: datetime = Field(default_factory=datetime.now)
    scrape_job: ScrapeJobConfig
    cleaning: CleaningConfig
    generation_jobs: Dict[str, GenerationJobConfig] = Field(default_factory=dict)
    cost_control: CostControl = Field(default_factory=CostControl)
    status: ProjectStatus = Field(default_factory=ProjectStatus)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Project":
        """Load project configuration from YAML file."""
        import yaml
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)

    def to_yaml(self, yaml_path: Path) -> None:
        """Save project configuration to YAML file."""
        import yaml
        config_dict = self.model_dump()
        # Convert datetime to string for YAML serialization
        config_dict['created'] = self.created.isoformat()
        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f, sort_keys=False, indent=2)

    def validate_status(self) -> List[str]:
        """Validate project configuration and return list of issues if any."""
        issues = []
        
        # Basic validation
        if not self.name:
            issues.append("Project name is required")
            
        # Scraping validation
        if not self.scrape_job.seed_urls:
            issues.append("At least one seed URL is required")
        if self.scrape_job.max_pages < 1:
            issues.append("max_pages must be positive")
            
        # Cleaning validation
        if not self.cleaning.prompt:
            issues.append("Cleaning prompt is required")
        if self.cleaning.max_docs < 1:
            issues.append("max_docs must be positive")
            
        # Generation validation
        for job_name, gen_job in self.generation_jobs.items():
            if not gen_job.prompt:
                issues.append(f"Generation job '{job_name}' missing prompt")
            if gen_job.max_tokens < 1:
                issues.append(f"Generation job '{job_name}' max_tokens must be positive")
                
        return issues

    def stage_docs(self, doc_paths: List[str]) -> None:
        """Stage documents for generation phase."""
        self.status.staged_docs.extend(doc_paths)
