import logging
from logging.handlers import RotatingFileHandler

from app.core.config import LOG_DIR, settings


def setup_logging() -> None:
    settings.ensure_dirs()
    log_path = LOG_DIR / "viralclipper.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(stream)
