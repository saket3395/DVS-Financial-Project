import logging
from logging.handlers import RotatingFileHandler

from config import LOG_DIR


def setup_logger():
    logger = logging.getLogger("screener")
    if logger.handlers:
        return logger
    logger.setLevel(logging.ERROR)
    h = RotatingFileHandler(LOG_DIR / "errors.log", maxBytes=1_000_000, backupCount=3)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)
    return logger
