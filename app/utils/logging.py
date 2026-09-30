"""Logging configuration with privacy guards."""

import logging
import sys
from app.utils.config import settings

def setup_logger(name: str = "meeting_intelligence") -> logging.Logger:
    """Configure and return an application logger with privacy guards."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    return logger


logger = setup_logger()


def redact_text_for_log(text: str, max_chars: int = 40) -> str:
    """Redact or abbreviate transcript snippets for privacy-compliant logging."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... [REDACTED {len(text) - max_chars} CHARS]"
