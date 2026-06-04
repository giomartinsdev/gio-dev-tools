import sys
import logging

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)