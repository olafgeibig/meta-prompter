from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import shutil
from click import prompt
from pydantic import BaseModel, Field
from .models import ScrapeJobConfig, CleaningConfig, GenerationJobConfig
from meta_prompter.utils.logging import get_logger
import tiktoken
import logging
import litellm
import meta_prompter.utils.file_utils as file_utils

logger = get_logger(name=__name__)

class Project(BaseModel):
    """Project configuration."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    created: datetime = Field(default_factory=datetime.now)
    path: Path = Field(default=None, description="Project directory path")
    scrape_job: ScrapeJobConfig
    cleaning: CleaningConfig
    generation_jobs: Dict[str, GenerationJobConfig] = Field(default_factory=dict, description="Generation job configurations")

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
        Stage documents from either scraped or cleaned directory and remove them from source.

        Args:
            source: Either 'scraped' or 'cleaned'

        Returns:
            Number of files staged and removed from source

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

        # Move files to staged directory
        moved_count = 0
        for file in source_dir.iterdir():
            if file.is_file() and file.suffix == '.md':
                target = self.get_staged_dir() / file.name
                shutil.move(file, target)  
                moved_count += 1

        if moved_count == 0:
            raise ValueError("No markdown files found to stage")

        return moved_count

    def get_staged_documents(self) -> List[Path]:
        """
        Get a list of paths to all staged documents.

        Returns:
            List of Path objects for each staged markdown file
        """
        staged_dir = self.get_staged_dir()
        if not staged_dir.exists():
            return []
        
        return sorted([f for f in staged_dir.iterdir() if f.is_file() and f.suffix == '.md'])

    def add_generation_job(self, job_name: str, topic: Optional[str] = None,
                           model: Optional[str] = None, max_tokens: Optional[int] = None,
                           temperature: Optional[float] = None) -> str:
        """
        Add a new generation job configuration.

        Args:
            job_name: Name of the generation job
            topic: Optional topic for generation
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
            prompt="""
<purpose>
    You are an expert at extracting relevant parts from product documentation to provide the necessary context for an AI coding assistant. Your goal is to identify and compress the relevant documentation related to a given [[topic]] so that the AI assistant can use it to generate correct and efficient code.
</purpose>

<instructions>
    <instruction>Carefully review the [[content]] to find the portions most relevant to the topic.</instruction>
    <instruction>Extract and compress the selected parts, ensuring that important details and factual integrity are maintained.</instruction>
    <instruction>Include only pertinent code snippets that help illustrate the usage for the topic. Remove any irrelevant code or text.</instruction>
    <instruction>Keep the resulting context as concise as possible without losing essential information.</instruction>
</instructions>

<topic>
    {topic}
</topic>

<content>
    {content}
</content>""",
            topic=topic or "CHANGEME",
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
            # Ensure generation_jobs is a dictionary
            if 'generation_jobs' not in config_dict or config_dict['generation_jobs'] is None:
                config_dict['generation_jobs'] = {}
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
    def create(cls, project_name: str, description: str | None = None, scrape_job: dict | None = None, cleaning: dict | None = None) -> 'Project':
        """Create a new project with default configuration.
    
        Args:
            project_name: Name of the project and directory to create
            description: Optional project description
            scrape_job: Optional scrape job configuration
            cleaning: Optional cleaning configuration
            
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
            description=description or "New MetaPrompter project",
            path=project_dir,
            scrape_job=scrape_job or {
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
            cleaning=cleaning or {
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
    
    def get_input_doc(self, staged_files: list[Path]) -> str:
        """
        Concatenate the content of all staged files into a single XML document.

        Args:
            staged_files: List of paths to staged markdown files

        Returns:
            A single XML string containing all files wrapped in <doc> tags with filenames
            as name attributes
        """
        if not staged_files:
            return ""
        
        contents = []
        for file_path in staged_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                contents.append(f'<doc name="{file_path.name}">{content}</doc>')
            except Exception as e:
                raise ValueError(f"Failed to read {file_path.name}: {str(e)}")
        
        return "\n".join(contents)

    def generate_context(self, job, staged_docs: List[Path]) -> str:
        """Run a generation job.
        
        Args:
            staged_docs: List of staged documents to generate from
        """
    
        input_doc = self.get_input_doc(staged_docs)
        file_utils.write_content(self.get_meta_prompts_dir() / f"{job}.xml", input_doc)
        
        # Count tokens using tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")  # Base encoding for Gemini models
        token_count = len(encoding.encode(input_doc))
        
        logger.info(f"Input document size: {len(input_doc)} characters")
        logger.info(f"Token count: {token_count} tokens")
        
        prompt_template = self.generation_jobs[job].prompt
        prompt = prompt_template.format(topic=self.generation_jobs[job].topic, content=input_doc)
    

        # response = litellm.completion(
        #     model=self.generation_jobs[job].model,
        #     messages=[{"content": prompt, "role": "user"}]
        # )

        # if response and response.choices:
        #     answer = response.choices[0].message.content
        #     return answer
        # else:
        #     return "No response from the model"
        return prompt
