import os

from loguru import logger

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

def setup_logger():
    """
    Configure and initialize the global logger.
    - Creates a logs directory if not exists.
    - Adds both file and console handlers.
    - Enables daily rotation and retention.
    """
    # Create log directory if missing
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Remove default logger configuration to avoid duplicates
    logger.remove()

    # File handler (rotates daily, keeps 7 days)
    logger.add(
        LOG_FILE,
        rotation="1 day",            # Create new file every day
        retention="7 days",           # Keep logs for 7 days
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

    # Console handler with colored output
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
    )

    logger.info("📋 Logger initialized successfully.")
    return logger
