from pathlib import Path
import click
import sys
import logging
from typing import Optional

from meta_prompter.core.project import Project
from meta_prompter.scrapers.sequential import SequentialScraper
from meta_prompter.utils.logging import setup_logging

# Configure logging
setup_logging(log_level=logging.INFO)

class ProjectPath(click.Path):
    """Custom path type that loads and validates project files."""
    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)
        if path is None:
            return None
        try:
            yaml_path = get_project_path(path)
            project = Project.from_yaml(yaml_path)
            return project
        except Exception as e:
            self.fail(f'Failed to load project: {str(e)}', param, ctx)

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
def init(project: str):
    """Create a new project with default configuration."""
    try:
        project_config = Project.create(project)
        click.echo(f"Created new project: {project_config.path}")
        click.echo("\nEdit project.yaml to configure your workflow")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

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
    click.echo(f"    Max Depth: {project.scrape_job.spider_options.max_depth}")
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
@click.argument('project', type=ProjectPath())
@click.argument('source', type=click.Choice(['scraped', 'cleaned']))
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
@click.option('--prompt', help='Generation prompt template')
@click.option('--model', help='LiteLLM model identifier')
@click.option('--max-tokens', type=int, help='Maximum tokens for generation')
@click.option('--temperature', type=float, help='Temperature for generation')
def create(project: Project, job: str, prompt: Optional[str] = None, 
          model: Optional[str] = None, max_tokens: Optional[int] = None,
          temperature: Optional[float] = None):
    """Create a new generation job configuration."""
    try:
        message = project.add_generation_job(
            job_name=job,
            prompt=prompt,
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
def generate(project: Project, job: str):
    """Run a generation job."""
    if job not in project.generation_jobs:
        click.echo(f"Error: Generation job {job} not found", err=True)
        sys.exit(1)
        
    click.echo(f"Starting generation job: {job}")
    # TODO: Implement generation logic
    click.echo("Generation completed successfully")

def main():
    cli()

if __name__ == "__main__":
    main()
