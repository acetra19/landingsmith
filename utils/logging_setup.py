"""
Centralized logging configuration with Rich formatting.
"""

import logging
import sys

from rich.logging import RichHandler

from config.settings import settings


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_path=False,
            )
        ],
        force=True,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.log_level == "DEBUG" else logging.WARNING
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
