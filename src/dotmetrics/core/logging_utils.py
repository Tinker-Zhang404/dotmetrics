from __future__ import annotations

import logging
from datetime import datetime

from .runtime_paths import logs_dir


LOGGER_NAME = "dotmetrics"



def setup_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stream_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_handler.setFormatter(formatter)

    try:
        file_handler = logging.FileHandler(logs_dir() / f"dotmetrics_{timestamp}.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass
    logger.addHandler(stream_handler)
    return logger


logger = setup_logging()
