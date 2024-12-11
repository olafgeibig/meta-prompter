from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
import shutil
from pydantic import BaseModel, Field
from .models import ScrapeJobConfig, CleaningConfig, GenerationJobConfig

class Project(BaseModel):
    """Project configuration."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    created: datetime = Field(default_factory=datetime.now)
    path: Path = Field(default=None, description="Project directory path")
    scrape_job: ScrapeJobConfig
    cleaning: CleaningConfig
    generation_jobs: Dict[str, GenerationJobConfig] = Field(default_factory=dict)

    def get_scraped_dir(self) -> Path:
        """Get the scraped content directory path."""
        return self.path / "scraped"

    def get_cleaned_dir(self) -> Path:
        """Get the cleaned content directory path."""
        return self.path / "cleaned"

    def get_staged_dir(self) -> Path:
        """Get the staged content directory path."""
        return self.path / "staged"

    def get_meta_prompts_dir(self) -> Path:
        """Get the meta-prompts directory path."""
        return self.path / "meta_prompts"

    def stage_documents(self, source: str) -> int:
        """
        Stage documents from either scraped or cleaned directory.

        Args:
            source: Either 'scraped' or 'cleaned'

        Returns:
            Tuple of (number of files staged, error message if any)

        Raises:
            ValueError: If source directory doesn't exist or no files found
        """
        source_dir = self.get_scraped_dir() if source == 'scraped' else self.get_cleaned_dir()

        if not source_dir.exists():
            raise ValueError(f"Source directory {source_dir} does not exist")

        if not any(source_dir.iterdir()):
            raise ValueError(f"No documents found in {source_dir}")

        # Create staged directory if it doesn't exist
        self.get_staged_dir().mkdir(exist_ok=True)

        # Clear existing staged files
        for existing in self.get_staged_dir().iterdir():
            if existing.is_file():
                existing.unlink()

        # Copy files to staged directory
        moved_count = 0
        for file in source_dir.iterdir():
            if file.is_file() and file.suffix == '.md':
                target = self.get_staged_dir() / file.name
                shutil.copy2(file, target)
                moved_count += 1

        if moved_count == 0:
            raise ValueError("No markdown files found to stage")

        return moved_count

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
        # Convert HttpUrl objects to strings
        config_dict['scrape_job']['seed_urls'] = [str(url) for url in self.scrape_job.seed_urls]
        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f, sort_keys=False, indent=2)

    @classmethod
    def create(cls, project_name: str) -> 'Project':
        """Create a new project with default configuration.
        
        Args:
            project_name: Name of the project and directory to create
            
        Returns:
            Project: Newly created project instance
            
        Raises:
            ValueError: If project directory already exists
        """
        project_dir = Path(project_name)
        
        # Create project directory
        if project_dir.exists():
            raise ValueError(f"Directory {project_name} already exists")
        
        # Create directory structure
        directories = [
            "scraped",
            "cleaned",
            "staged",
            "meta_prompts"
        ]
        
        project_dir.mkdir()
        for dir_name in directories:
            (project_dir / dir_name).mkdir()
            
        # Create empty database
        (project_dir / "project.db").touch()
        
        project_path = project_dir / "project.yaml"
        
        # Create default project
        project = cls(
            name=project_name,
            description="New MetaPrompter project",
            path=project_dir,
            scrape_job={
                "seed_urls": [],
                "max_pages": 5,
                "spider_options": {
                    "follow_links": True,
                    "restrict_domain": True,
                    "restrict_path": True,
                    "max_depth": 5,
                    "exclusion_patterns": []
                }
            },
            cleaning={
                "prompt": "Clean and format the following content. Remove any navigation elements or other web-specific artifacts. Ensure the content is formatted consistently across different documentation sources.",
                "max_docs": 5,
                "model": "gemini/gemini-1.5-flash",
                "max_tokens": 128000,
                "temperature": 0.1
            }
        )
        
        # Save project file
        project.to_yaml(project_path)
        return project
