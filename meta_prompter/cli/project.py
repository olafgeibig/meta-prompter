import click
from pathlib import Path
from typing import List

from ..core.project import Project

@click.group()
def project():
    """Project management commands."""
    pass

@project.command()
@click.argument('name')
@click.argument('description')
@click.argument('seed_urls', nargs=-1)
@click.option('--output', '-o', type=click.Path(), default='project.yaml',
              help='Output YAML file path')
def create(name: str, description: str, seed_urls: List[str], output: str):
    """Create a new project with default configuration.
    
    Example:
        meta-prompter project create langchain-tools "LangChain Tools Documentation" \\
            https://python.langchain.com/docs/modules/agents/tools/
    """
    project = Project.create_default(name, description, list(seed_urls))
    output_path = Path(output)
    project.to_yaml(output_path)
    click.echo(f"Created project configuration at {output_path}")

@project.command()
@click.argument('yaml_path', type=click.Path(exists=True))
def validate(yaml_path: str):
    """Validate a project configuration YAML file.
    
    Example:
        meta-prompter project validate project.yaml
    """
    try:
        project = Project.from_yaml(Path(yaml_path))
        click.echo(f"✓ Valid project configuration: {project.name}")
        click.echo(f"  Description: {project.description}")
        click.echo(f"  Created: {project.created}")
        click.echo(f"  Seed URLs: {', '.join(str(url) for url in project.scrape_job.seed_urls)}")
    except Exception as e:
        click.echo(f"✗ Invalid project configuration: {str(e)}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    project()
