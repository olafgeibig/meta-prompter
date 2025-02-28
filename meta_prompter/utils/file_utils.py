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


def create_safe_filename(path: str, max_length: int = 100) -> str:
    """Create a filename from a path string that is safe for all filesystems.
    
    Args:
        path: The path string to convert to a safe filename
        max_length: Maximum length for the filename
        
    Returns:
        A safe filename without extension
    """
    if not path:
        return "index"
        
    # Remove leading/trailing slashes and decode URL encoding
    clean_path = unquote(path.strip("/"))
    
    # Remove file extensions
    clean_path = re.sub(r'\.\w+$', '', clean_path)
    
    # Replace slashes and other separators with underscores
    clean_path = re.sub(r'[/\\]', '_', clean_path)
    
    # Remove invalid filename characters
    clean_path = re.sub(r'[<>:"|?*]', '', clean_path)
    
    # Replace whitespace with underscores
    clean_path = re.sub(r'\s+', '_', clean_path)
    
    # Replace multiple underscores with a single one
    clean_path = re.sub(r'_+', '_', clean_path)
    
    # Truncate if too long
    if len(clean_path) > max_length:
        clean_path = clean_path[:max_length]
        
    # Remove leading/trailing underscores
    clean_path = clean_path.strip('_')
    
    if not clean_path:
        return "index"
        
    return clean_path


def create_filename_from_url(url: str, max_length: int = 100) -> str:
    """Create a filename from a URL that preserves path structure.

    Args:
        url: The source URL
        max_length: Maximum length for each path segment

    Returns:
        A filename in the format: path-segments-page.md

    Example:
        https://docs.example.com/guide/intro.html -> guide-intro.md
        https://docs.example.com/api/v1/auth.html -> api-v1-auth.md
    """
    # Parse the URL and get the path
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/")

    if not path:
        # If no path, use the hostname
        return sanitize_filename(parsed.hostname or "index", max_length)

    # Split path into segments and clean each one
    segments = path.split("/")
    
    # Process each segment
    clean_segments = []
    for seg in segments:
        # Remove file extensions (.html, .htm)
        seg = re.sub(r'\.html?$', '', seg)
        # Remove other invalid characters
        seg = re.sub(r"[^\w\s-]", "", seg)
        # Replace whitespace with underscores
        seg = re.sub(r"\s+", "_", seg)
        # Truncate if too long
        seg = seg[:max_length].strip("_")
        if seg:
            clean_segments.append(seg)

    if not clean_segments:
        return "index.md"

    # Join segments with hyphens
    return "-".join(clean_segments) + ".md"


def ensure_directory(directory: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)


def write_content(filepath: Path, content: str) -> None:
    """Write content to file, creating directories if needed."""
    ensure_directory(filepath.parent)
    filepath.write_text(content)
