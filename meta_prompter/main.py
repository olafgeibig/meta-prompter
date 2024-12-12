from pathlib import Path
import click
import sys
from typing import Optional, NoReturn, Literal, TypeAlias
from dataclasses import dataclass
import logging
from logging import Logger, getLogger

from meta_prompter.core.project import Project
from meta_prompter.scrapers.sequential import SequentialScraper
from meta_prompter.utils.logging import setup_logging
from meta_prompter.arize_phoenix import litellm_instrumentation

# Type aliases
ProjectSource: TypeAlias = Literal['scraped', 'cleaned']
logger: Logger = setup_logging(
    log_level=logging.INFO,
    log_file=None
)
litellm_instrumentation()

@dataclass
class CliError(Exception):
    """Base exception for CLI errors."""
    message: str
    exit_code: int = 1

    def exit(self) -> NoReturn:
        """Exit the program with error message."""
        click.echo(f"Error: {self.message}", err=True)
        sys.exit(self.exit_code)

class ProjectPath(click.Path):
    """Custom path type that loads and validates project files."""
    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> Project:
        try:
            path = super().convert(value, param, ctx)
            if path is None:
                raise ValueError("Path cannot be None")
            # Convert path to string explicitly
            path_str = str(path)
            yaml_path = get_project_path(path_str)
            return Project.from_yaml(yaml_path)
        except Exception as e:
            self.fail(f"Invalid project path: {e}")

def get_project_path(project_name: str) -> Path:
    """Get the path to a project's YAML file."""
    project_dir = Path(project_name)
    if project_dir.is_dir():
        return project_dir / "project.yaml"
    return Path(project_name)  # Fallback for backward compatibility

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """MetaPrompter - AI documentation context manager.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()

@cli.command()
@click.argument('project')
@click.option('--description', help='Project description')
@click.option('--max-pages', type=int, help='Maximum pages to scrape', default=5)
@click.option('--max-docs', type=int, help='Maximum documents to clean', default=5)
@click.option('--model', help='Default model for cleaning', default="gemini/gemini-1.5-flash")
@click.option('--max-tokens', type=int, help='Default max tokens for cleaning', default=128000)
@click.option('--temperature', type=float, help='Default temperature for cleaning', default=0.1)
@click.option('--follow-links/--no-follow-links', default=True, help='Whether to follow links during scraping')
@click.option('--restrict-domain/--no-restrict-domain', default=True, help='Whether to restrict scraping to the same domain')
def init(
    project: str,
    description: str | None = None,
    max_pages: int = 5,
    max_docs: int = 5,
    model: str = "gemini/gemini-1.5-flash",
    max_tokens: int = 128000,
    temperature: float = 0.1,
    follow_links: bool = True,
    restrict_domain: bool = True,
) -> None:
    """Create a new project with configuration.
    
    Args:
        project: Name of the project to create
        description: Optional project description
        max_pages: Maximum pages to scrape
        max_docs: Maximum documents to clean
        model: Default model for cleaning
        max_tokens: Default max tokens for cleaning
        temperature: Default temperature for cleaning
        follow_links: Whether to follow links during scraping
        restrict_domain: Whether to restrict scraping to the same domain
    """
    try:
        project_config = Project.create(
            project,
            description=description,
            scrape_job={
                "seed_urls": [],
                "max_pages": max_pages,
                "spider_options": {
                    "follow_links": follow_links,
                    "restrict_domain": restrict_domain,
                    "restrict_path": True,
                    "max_depth": 5,
                    "exclusion_patterns": []
                }
            },
            cleaning={
                "prompt": "Clean and format the following content. Remove any navigation elements or other web-specific artifacts. Ensure the content is formatted consistently across different documentation sources.",
                "max_docs": max_docs,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        )
        logger.info(f"Created new project: {project_config.path}")
        click.echo(f"Created new project: {project_config.path}")
        click.echo("\nEdit project.yaml to configure your workflow")
    except ValueError as e:
        logger.error(f"Failed to create project: {e}")
        CliError(str(e)).exit()
    except Exception as e:
        logger.error(f"Unexpected error creating project: {e}")
        CliError(f"Unexpected error: {str(e)}").exit()

@cli.command()
@click.argument('project', type=ProjectPath())
def status(project: Project):
    """Show project status and configuration."""
    click.echo(f"Project: {project.name}")
    click.echo(f"Description: {project.description}")
    click.echo(f"Created: {project.created}")
    click.echo("\nConfiguration:")
    click.echo("  Scraping:")
    click.echo(f"    Max Pages: {project.scrape_job.max_pages}")
    click.echo(f"    Max Depth: {project.scrape_job.max_depth}")
    if project.scrape_job.seed_urls:
        click.echo("    Seed URLs:")
        for url in project.scrape_job.seed_urls:
            click.echo(f"      - {url}")
    
    click.echo("\n  Cleaning:")
    click.echo(f"    Max Docs: {project.cleaning.max_docs}")
    click.echo(f"    Model: {project.cleaning.model}")
    click.echo(f"    Max Tokens: {project.cleaning.max_tokens}")
    click.echo(f"    Temperature: {project.cleaning.temperature}")
    
    if project.generation_jobs:
        click.echo("\n  Generation Jobs:")
        for name, job in project.generation_jobs.items():
            click.echo(f"    {name}:")
            click.echo(f"      Model: {job.model}")
            click.echo(f"      Max Tokens: {job.max_tokens}")
            click.echo(f"      Temperature: {job.temperature}")

@cli.command()
@click.argument('project', type=ProjectPath())
def scrape(project: Project):
    """Run scrape job with current configuration."""
    if not project.scrape_job.seed_urls:
        click.echo("Error: No seed URLs configured", err=True)
        sys.exit(1)
        
    click.echo(f"Starting scrape job for {project.name}")
    click.echo(f"Max pages: {project.scrape_job.max_pages}")
    
    scraper = SequentialScraper(project)
    scraper.run()
    # project.to_yaml(get_project_path(project.name))
    click.echo("Scraping completed successfully")

@cli.command()
@click.argument('project', type=ProjectPath())
def clean(project: Project):
    """Run cleaning job with current configuration."""
    if not project.scrape_job.seed_urls:
        click.echo("Error: Scraping phase not complete", err=True)
        sys.exit(1)
        
    click.echo(f"Starting cleaning job for {project.name}")
    click.echo(f"Max docs: {project.cleaning.max_docs}")
    # TODO: Implement cleaning logic
    click.echo("Cleaning completed successfully")
    
    project.to_yaml(get_project_path(project.name))

@cli.command()
@click.argument('source', type=click.Choice(['scraped', 'cleaned']))
@click.argument('project', type=ProjectPath())
def stage(project: Project, source: str):
    """Stage documents for generation from either scraped or cleaned directory."""
    try:
        count = project.stage_documents(source)
        click.echo(f"Successfully staged {count} documents from {source} directory")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('project', type=ProjectPath())
@click.argument('job')
@click.option('--topic', help='Generation topic')
@click.option('--model', help='LiteLLM model identifier')
@click.option('--max-tokens', type=int, help='Maximum tokens for generation')
@click.option('--temperature', type=float, help='Temperature for generation')
def create(project: Project, job: str, topic: Optional[str] = None,
          model: Optional[str] = None, max_tokens: Optional[int] = None,
          temperature: Optional[float] = None):
    """Create a new generation job configuration."""
    try:
        message = project.add_generation_job(
            job_name=job,
            topic=topic,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        project.to_yaml(get_project_path(project.name))
        click.echo(message)
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('project', type=ProjectPath())
@click.argument('job')
def generate(project: Project, job: str) -> None:
    """Run a generation job.
    
    Args:
        project: Project to run generation for
        job: Name of the generation job to run
    """
    try:
        if job not in project.generation_jobs:
            raise CliError(f"Generation job '{job}' not found")
            
        job_config = project.generation_jobs[job]
        logger.info(f"Starting generation job '{job}' for {project.name}")
        click.echo(f"Starting generation job '{job}' for {project.name}")
        
        # Get staged documents
        staged_docs = list(project.get_staged_documents())
        if not staged_docs:
            raise CliError("No documents staged for generation")
            
        click.echo(f"Found {len(staged_docs)} staged documents")
        context = project.generate_context(job, staged_docs)

        click.echo("Generation completed successfully")
        project.to_yaml(get_project_path(project.name))
            
    except CliError as e:
        e.exit()
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        CliError(f"Generation failed: {str(e)}").exit()

def main():
    cli()

if __name__ == "__main__":
    main()
