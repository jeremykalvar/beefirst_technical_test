import logging
import sys
import time

from pythonjsonlogger import jsonlogger


class UTCJsonFormatter(jsonlogger.JsonFormatter):
    converter = time.gmtime


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handler.setFormatter(UTCJsonFormatter(fmt))
    root.addHandler(handler)

    # logging.getLogger("uvicorn").setLevel(level.upper())
    # logging.getLogger("uvicorn.error").setLevel(level.upper())
    # logging.getLogger("uvicorn.access").setLevel("WARNING")
    # logging.getLogger("httpx").setLevel("WARNING")
