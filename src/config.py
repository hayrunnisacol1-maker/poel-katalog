"""
Config module for Dynamic Catalog Splitter.
Contains regex patterns, search keywords, and default settings.
"""

import re

# Keywords to detect Table of Contents (TOC) / İçindekiler pages
TOC_KEYWORDS = [
    "İÇİNDEKİLER",
    "ICINDEKILER",
    "CONTENTS",
    "TABLE OF CONTENTS",
    "INDEX",
    "İÇERİK",
    "ICERIK"
]

# Regex patterns for matching TOC entry lines
# Examples:
#   POMPALAR .......... 12
#   VANALAR ........... 34
#   FİLTRELER --------- 58
#   AKSESUARLAR         81
#   1. POMPALAR ............... 12
#   1.1 SU POMPALARI .......... 15
TOC_LINE_PATTERNS = [
    # Match: Title followed by dots/dashes/spaces and ending with a page number
    # MUST contain at least one letter (Turkish or English)
    re.compile(
        r'^\s*(?P<title>(?=.*[A-Za-zĞÜŞİÖÇa-zğüşiöç])(?:[0-9\.\s]+)?[^\.\·\-\–\—\_\n\r\t]+?)\s*[\.·\-\–\—\_]{2,}\s*(?P<page>\d+)\s*$',
        re.UNICODE | re.MULTILINE
    ),
    # Secondary pattern: Title followed by dots/spaces and page number
    re.compile(
        r'^\s*(?P<title>(?=.*[A-Za-zĞÜŞİÖÇa-zğüşiöç])[A-ZĞÜŞİÖÇa-zğüşiöç0-9\s\&\-\/,\(\)]{2,})\s*[\.·\-\–\—\_\s]{2,}\s*(?P<page>\d+)\s*$',
        re.UNICODE | re.MULTILINE
    ),
    # Fallback pattern for simple spaces: Category Name 12
    re.compile(
        r'^\s*(?P<title>(?=.*[A-Za-zĞÜŞİÖÇa-zğüşiöç])[A-ZĞÜŞİÖÇa-zğüşiöç0-9\s\&\-\/,\(\)]{3,})\s+(?P<page>\d+)\s*$',
        re.UNICODE | re.MULTILINE
    )
]

# Invalid characters for filenames in various operating systems
INVALID_FILENAME_CHARS = r'[\/\\:\*\?"<>\|]'

# Default maximum number of pages to scan for TOC (usually TOC is in the first 25 pages)
MAX_TOC_SEARCH_PAGES = 25

# Logging format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
