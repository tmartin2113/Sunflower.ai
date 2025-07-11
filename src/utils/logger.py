#!/usr/bin/env python3
"""
Logging configuration for the Sunflower AI application.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(logs_dir: Path) -> logging.Logger:
    """
    Sets up a centralized, rotating file logger.

    Args:
        logs_dir: The directory where log files will be stored.

    Returns:
        A configured instance of logging.Logger.
    """
    # Ensure the logs directory exists
    logs_dir.mkdir(exist_ok=True, parents=True)

    # Define the log file path
    log_file = logs_dir / "sunflower-ai.log"

    # Create a logger instance
    logger = logging.getLogger("SunflowerAI")
    logger.setLevel(logging.INFO)

    # Prevent messages from being propagated to the root logger
    logger.propagate = False

    # If handlers are already configured, do nothing (to prevent duplicates)
    if logger.hasHandlers():
        return logger

    # Configure formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure a rotating file handler
    # Rotates when the log reaches 2MB, keeps 5 backup logs.
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Configure a console handler for printing to stdout as well
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

if __name__ == '__main__':
    # --- Example Usage ---
    # In the real application, the data_root would come from the PartitionDetector
    dummy_logs_dir = Path("./temp_logs")
    
    # Setup logger
    app_logger = setup_logger(dummy_logs_dir)
    
    print(f"Logger configured. Log file is at: {dummy_logs_dir / 'sunflower-ai.log'}")

    # Log some messages
    app_logger.info("Application starting up.")
    app_logger.info("Profile 'TestUser' selected.")
    app_logger.warning("Safety filter triggered for category 'violence'.")
    app_logger.error("Failed to connect to Ollama server.", exc_info=True)
    
    print("Logged several messages. Check the temp_logs directory.")

    # Cleanup
    import shutil
    # To properly close the handlers
    logging.shutdown()
    shutil.rmtree(dummy_logs_dir)
