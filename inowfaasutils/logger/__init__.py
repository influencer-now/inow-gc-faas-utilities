from logging import Logger

import logging
import sys
import json
import os


class CloudLoggingFormatter(logging.Formatter):
    """Produces messages compatible with google cloud logging"""

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        return json.dumps(
            {
                "message": s,
                "severity": record.levelname,
                "timestamp": {"seconds": int(record.created), "nanos": 0},
            }
        )


def get_logger(name: str = None) -> Logger:
    """Gets a logger instance with Google Cloud logging format.

    Args:
        name (str): name of logger, displayed on its log. If none name is
        input, look up for APP_NAME env variable (only if it is populated).

    Returns:
        Logger: python standard logger
    """
    logger_name = name
    if name is None:
        logger_name = os.environ.get("APP_NAME", None)
    logger = logging.getLogger(logger_name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = CloudLoggingFormatter(fmt="[%(name)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    return logger
