import logging
import sys

# Configure standard logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class Logger:
    @staticmethod
    def info(msg: str):
        logging.info(msg)

    @staticmethod
    def warn(msg: str):
        logging.warning(msg)

    @staticmethod
    def error(msg: str, exc: Exception = None):
        if exc:
            logging.error(f"{msg} - Exception: {exc}", exc_info=True)
        else:
            logging.error(msg)

    @staticmethod
    def debug(msg: str):
        logging.debug(msg)
