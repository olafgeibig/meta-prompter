import re
from pathlib import Path

def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Convert title to a valid filename."""
    # Remove invalid characters
    filename = re.sub(r'[^\w\s-]', '', title)
    # Replace whitespace with underscores
    filename = re.sub(r'\s+', '_', filename)
    # Truncate if too long
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename.strip('_') + '.md'

def ensure_directory(directory: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)

def write_content(filepath: Path, content: str) -> None:
    """Write content to file, creating directories if needed."""
    ensure_directory(filepath.parent)
    filepath.write_text(content)
