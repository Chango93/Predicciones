"""
Logging configuration for Liga MX prediction system
"""
import logging
import sys
from pathlib import Path

def setup_logger(name: str = "predicciones", level: str = "INFO") -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Console handler (colorized if possible)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Optional: File handler
    # Uncomment to enable logging to file
    # log_dir = Path("logs")
    # log_dir.mkdir(exist_ok=True)
    # file_handler = logging.FileHandler(log_dir / "predicciones.log")
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)
    
    return logger
