"""Logger Loguru con consola + ficheiro rotativo."""
import sys
from pathlib import Path
from loguru import logger
from .config import settings, BASE_DIR

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stderr, level=settings.log_level,
           format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level:<7}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
logger.add(LOGS_DIR / "monterrei_{time:YYYYMMDD}.log",
           rotation="10 MB", retention="30 days", level="DEBUG",
           format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {name}:{function}:{line} - {message}")

__all__ = ["logger", "log"]
log = logger
