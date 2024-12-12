import logging
from pathlib import Path
from typing import Optional

def setup_logging(log_level: int = logging.INFO, log_file: Optional[Path] = None) -> logging.Logger:
    """Configure logging with consistent format.
    
    Args:
        log_level: Logging level to use
        log_file: Optional path to log file
        
    Returns:
        logging.Logger: Configured logger instance
    """
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create and configure logger
    logger = logging.getLogger('meta_prompter')
    logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(format_str))
    logger.addHandler(console_handler)
    
    # Add file handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(file_handler)
    
    # Set more verbose logging for requests library
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return logger