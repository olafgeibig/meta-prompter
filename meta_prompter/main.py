from pathlib import Path
import click
import sys

from meta_prompter.core.project import Project
from meta_prompter.scrapers.parallel import ParallelScraper
from meta_prompter.utils.logging import setup_logging

# Configure logging
setup_logging(log_file=Path("logs/metaprompter.log"))

class ProjectPath(click.Path):
    """Custom path type that loads and validates project files."""
    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)
        if path is None:
            return None
        try:
            project = Project.from_yaml(Path(path))
            return project
        except Exception as e:
            self.fail(f'Failed to load project: {str(e)}', param, ctx)

def get_project_path(project_name: str) -> Path:
    """Get the path to a project's YAML file."""
    return Path(f"{project_name}.yaml")

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
    project_path = get_project_path(project)
    if project_path.exists():
        click.echo(f"Error: Project {project} already exists", err=True)
        sys.exit(1)
        
    # Create default project
    project = Project(
        name=project,
        description="New MetaPrompter project",
        scrape_job={
            "seed_urls": [],
            "max_pages": 10,
            "output_dir": "scrape_output"
        },
        cleaning={
            "prompt": "Clean and format the following content: {content}",
            "max_docs": 5,
            "output_dir": "clean_output"
        }
    )
    
    # Save project file
    project.to_yaml(project_path)
    click.echo(f"Created new project: {project_path}")
    click.echo("Edit the project file to configure your workflow")

@cli.command()
@click.argument('project', type=ProjectPath())
def status(project: Project):
    """Display project status and validate configuration."""
    click.echo(f"Project: {project.name}")
    click.echo(f"Description: {project.description}")
    click.echo("\nValidating configuration...")
    
    issues = project.validate_status()
    if issues:
        click.echo("\nConfiguration issues found:", err=True)
        for issue in issues:
            click.echo(f"- {issue}", err=True)
        sys.exit(1)
    else:
        click.echo("Configuration is valid")
        
    # Show phase status
    click.echo("\nPhase Status:")
    click.echo(f"Current Phase: {project.status.current_phase}")
    click.echo(f"Scraping: {'Complete' if project.status.scrape_complete else 'Pending'}")
    click.echo(f"Cleaning: {'Complete' if project.status.clean_complete else 'Pending'}")
    if project.status.staged_docs:
        click.echo(f"Staged Documents: {len(project.status.staged_docs)}")

@cli.command()
@click.argument('project', type=ProjectPath())
def scrape(project: Project):
    """Run scrape job with current configuration."""
    if not project.scrape_job.seed_urls:
        click.echo("Error: No seed URLs configured", err=True)
        sys.exit(1)
        
    click.echo(f"Starting scrape job for {project.name}")
    click.echo(f"Max pages: {project.scrape_job.max_pages}")
    
    scraper = ParallelScraper(
        max_workers=3,
        output_dir=Path(project.scrape_job.output_dir)
    )
    
    try:
        scraper.scrape(project.scrape_job)
        project.status.scrape_complete = True
        project.to_yaml(get_project_path(project.name))
        click.echo("Scraping completed successfully")
    except Exception as e:
        click.echo(f"Scraping failed: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('project', type=ProjectPath())
def clean(project: Project):
    """Run cleaning job with current configuration."""
    if not project.status.scrape_complete and not project.cleaning.skip_cleaning:
        click.echo("Error: Scraping phase not complete", err=True)
        sys.exit(1)
        
    click.echo(f"Starting cleaning job for {project.name}")
    click.echo(f"Max docs: {project.cleaning.max_docs}")
    # TODO: Implement cleaning logic
    click.echo("Cleaning completed successfully")
    
    project.status.clean_complete = True
    project.to_yaml(get_project_path(project.name))

@cli.command()
@click.argument('project', type=ProjectPath())
def stage(project: Project):
    """Stage documents for generation phase."""
    if not project.status.scrape_complete:
        click.echo("Error: Scraping phase not complete", err=True)
        sys.exit(1)
    if not project.status.clean_complete and not project.cleaning.skip_cleaning:
        click.echo("Error: Cleaning phase not complete", err=True)
        sys.exit(1)
        
    # TODO: Implement staging logic
    click.echo("Documents staged for generation")

@cli.command()
@click.argument('project', type=ProjectPath())
@click.argument('job')
def create(project: Project, job: str):
    """Create a new generation job."""
    if job in project.generation_jobs:
        click.echo(f"Error: Generation job {job} already exists", err=True)
        sys.exit(1)
        
    project.generation_jobs[job] = {
        "prompt": "Generate content based on: {content}",
        "model": "gpt-4",
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    project.to_yaml(get_project_path(project.name))
    click.echo(f"Created generation job: {job}")
    click.echo("Edit the project file to configure the generation prompt")

@cli.command()
@click.argument('project', type=ProjectPath())
@click.argument('job')
def generate(project: Project, job: str):
    """Run a generation job."""
    if job not in project.generation_jobs:
        click.echo(f"Error: Generation job {job} not found", err=True)
        sys.exit(1)
    if not project.status.staged_docs:
        click.echo("Error: No documents staged for generation", err=True)
        sys.exit(1)
        
    click.echo(f"Starting generation job: {job}")
    # TODO: Implement generation logic
    click.echo("Generation completed successfully")

def main():
    cli()

if __name__ == "__main__":
    main()
