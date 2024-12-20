import re
from pathlib import Path
from urllib.parse import urlparse, unquote


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Convert title to a valid filename."""
    # Remove invalid characters
    filename = re.sub(r"[^\w\s-]", "", title)
    # Replace whitespace with underscores
    filename = re.sub(r"\s+", "_", filename)
    # Truncate if too long
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename.strip("_") + ".md"


def create_filename_from_url(url: str, max_length: int = 100) -> str:
    """Create a filename from a URL that preserves path structure.

    Args:
        url: The source URL
        max_length: Maximum length for each path segment

    Returns:
        A filename in the format: path-segments-page.md

    Example:
        https://docs.example.com/guide/intro -> guide-intro.md
        https://docs.example.com/api/v1/auth -> api-v1-auth.md
    """
    # Parse the URL and get the path
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/")

    if not path:
        # If no path, use the hostname
        return sanitize_filename(parsed.hostname or "index", max_length)

    # Split path into segments and sanitize each
    segments = [re.sub(r"[^\w\s-]", "", seg) for seg in path.split("/")]
    segments = [re.sub(r"\s+", "_", seg) for seg in segments]
    segments = [seg[:max_length].strip("_") for seg in segments if seg]

    if not segments:
        return "index.md"

    # Join segments with hyphens
    return "-".join(segments) + ".md"


def ensure_directory(directory: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)


def write_content(filepath: Path, content: str) -> None:
    """Write content to file, creating directories if needed."""
    ensure_directory(filepath.parent)
    filepath.write_text(content)
