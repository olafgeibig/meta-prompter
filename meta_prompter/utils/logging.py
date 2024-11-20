import logging
from pathlib import Path
from typing import Optional

def setup_logging(log_level: int = logging.INFO, log_file: Optional[Path] = None) -> None:
    """Configure logging with consistent format."""
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=format_str,
        handlers=[
            logging.StreamHandler()  # Console handler
        ]
    )
    
    # Add file handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setFormatter(logging.Formatter(format_str))
        logging.getLogger().addHandler(file_handler)

    # Set more verbose logging for requests library
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
