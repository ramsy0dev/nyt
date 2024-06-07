import os
import logging

from loguru import logger

JSON_LOGS = True if os.environ.get("JSON_LOGS", "0") == "1" else False

def WORKERS(workers_number) -> int:
    return int(os.environ.get("UVICORN_WORKERS", workers_number))

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
