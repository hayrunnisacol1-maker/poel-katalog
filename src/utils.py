"""
Utility functions for file handling, text normalization, and logging.
"""

import os
import sys
import re
import logging
from typing import Optional

# Ensure project root is in sys.path when running scripts directly from src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.config import INVALID_FILENAME_CHARS, LOG_FORMAT, LOG_DATE_FORMAT
except ModuleNotFoundError:
    from config import INVALID_FILENAME_CHARS, LOG_FORMAT, LOG_DATE_FORMAT

logger = logging.getLogger("CatalogSplitter.Utils")


def sanitize_filename(filename: str, fallback_name: str = "kategori") -> str:
    """
    Sanitizes a string to be used safely as a filename across OS platforms.
    Preserves Turkish characters while stripping invalid characters and control characters.
    
    Args:
        filename: Original string (e.g. category name).
        fallback_name: Default name if sanitized string is empty.
        
    Returns:
        Cleaned, OS-safe filename string.
    """
    if not filename:
        return fallback_name

    # Remove invalid filename characters (\ / : * ? " < > |)
    clean_name = re.sub(INVALID_FILENAME_CHARS, "", filename)

    # Replace newlines and carriage returns with space
    clean_name = re.sub(r'[\r\n\t]+', ' ', clean_name)

    # Trim leading/trailing whitespaces and dots
    clean_name = clean_name.strip(" .")

    # Collapse multiple consecutive spaces
    clean_name = re.sub(r'\s+', ' ', clean_name)

    # Limit filename length to 200 chars for filesystem safety
    if len(clean_name) > 200:
        clean_name = clean_name[:200].rstrip()

    if not clean_name:
        return fallback_name

    return clean_name


def normalize_text(text: str) -> str:
    """
    Normalizes text for consistent comparison (converts Turkish 'I'/'i' properly and collapses space).
    """
    if not text:
        return ""
    
    # Uppercase handling for Turkish character 'i' -> 'İ'
    normalized = text.replace('i', 'İ').upper()
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns the root logger for the application.
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    return logging.getLogger("CatalogSplitter")
