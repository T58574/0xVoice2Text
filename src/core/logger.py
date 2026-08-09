import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Log Directory in user profile ~/.0xvoice2text/logs and local data directory
USER_HOME_LOG_DIR = os.path.expanduser("~/.0xvoice2text/logs")
os.makedirs(USER_HOME_LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(USER_HOME_LOG_DIR, "app.log")

def setup_logger(name="0xVoice2Text") -> logging.Logger:
    """
    Sets up a thread-safe rotating file logger with console output.
    Rotates logs when they reach 5 MB, keeping up to 5 backup archives.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Rotating File Handler (5 MB per file, max 5 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=5 * 1024 * 1024, # 5 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[Logger] Failed to create RotatingFileHandler: {e}")

    # 2. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"=== Logging initialized. Log file: {LOG_FILE_PATH} ===")
    return logger

logger = setup_logger()

def get_log_file_path() -> str:
    return LOG_FILE_PATH
