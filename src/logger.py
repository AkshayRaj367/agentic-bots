import logging
import os
from functools import wraps

from flask import request

from src.config import Config


class Logger:
    def __init__(self, filename="imposter_agent.log"):
        config = Config()
        logs_dir = config.get_logs_dir()
        os.makedirs(logs_dir, exist_ok=True)
        self.log_path = os.path.join(logs_dir, filename)
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(self.log_path, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(filename)

    def read_log_file(self) -> str:
        with open(self.log_path, "r") as file:
            return file.read()

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def exception(self, message: str):
        self.logger.exception(message)


def route_logger(logger: Logger):
    """
    Decorator factory that creates a decorator to log route entry and exit points.
    The decorator uses the provided logger to log the information.

    :param logger: The logger instance to use for logging.
    """

    log_enabled = Config().get_logging_rest_api()

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log entry point
            if log_enabled:
                logger.info(f"{request.path} {request.method}")

            # Call the actual route function
            response = func(*args, **kwargs)

            from werkzeug.wrappers import Response

            # Log exit point, including response summary if possible
            try:
                if log_enabled:
                    if isinstance(response, Response) and response.direct_passthrough:
                        logger.debug(f"{request.path} {request.method} - Response: File response")
                    else:
                        response_summary = response.get_data(as_text=True)
                        if 'settings' in request.path:
                            response_summary = "*** Settings are not logged ***"
                        logger.debug(f"{request.path} {request.method} - Response: {response_summary}")
            except Exception as e:
                logger.exception(f"{request.path} {request.method} - {e})")

            return response
        return wrapper
    return decorator
