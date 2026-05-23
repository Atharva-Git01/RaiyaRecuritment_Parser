import logging
import sys

def setup_logging(level=logging.INFO):
    """Sets up standard logging for the application."""
    logger = logging.getLogger("rag_validation")
    logger.setLevel(level)
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Initialize default logger
logger = setup_logging()
