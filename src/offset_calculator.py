"""
Module for calculating the offset between printed page numbers in TOC and physical PDF page indices.
"""

import os
import sys
import re
import logging
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.toc_parser import TOCEntry
    from src.utils import normalize_text
except ModuleNotFoundError:
    from toc_parser import TOCEntry
    from utils import normalize_text

logger = logging.getLogger("CatalogSplitter.OffsetCalculator")


class OffsetCalculator:
    """
    Calculates dynamic offset to convert printed page numbers (1-based) to physical PDF page indices (0-based).
    Formula: physical_page_index = printed_page_number + offset
    """

    def calculate_offset(
        self,
        pages_text: List[str],
        toc_entries: List[TOCEntry],
        toc_page_indices: List[int],
        page_labels: Optional[List[str]] = None
    ) -> int:
        """
        Calculates the integer offset dynamically.
        """
        if not toc_entries:
            logger.warning("No TOC entries available for offset calculation. Defaulting offset to 0.")
            return 0

        first_entry = toc_entries[0]
        norm_first_cat = normalize_text(first_entry.category_name)
        start_search_idx = max(toc_page_indices) + 1 if toc_page_indices else 0

        # Method 1: Search for First Category Name on physical pages after TOC
        for phys_idx in range(start_search_idx, len(pages_text)):
            page_content = pages_text[phys_idx]
            norm_content = normalize_text(page_content)

            if norm_first_cat in norm_content:
                offset = phys_idx - first_entry.printed_page
                logger.info(
                    f"Offset calculated via first category text search ('{first_entry.category_name}' "
                    f"found at phys_page={phys_idx}, printed={first_entry.printed_page}): offset={offset}"
                )
                return offset

        # Method 2: Search physical pages for explicit page numbers matching first entry (e.g., 'Sayfa 12' or '12')
        expected_printed = first_entry.printed_page
        number_patterns = [
            rf'SAYFA\s*{expected_printed}\b',
            rf'PAGE\s*{expected_printed}\b',
            rf'\b{expected_printed}\b'
        ]
        
        for phys_idx in range(start_search_idx, min(len(pages_text), start_search_idx + 40)):
            page_content = pages_text[phys_idx]
            norm_content = normalize_text(page_content)
            
            for pat in number_patterns:
                if re.search(pat, norm_content):
                    offset = phys_idx - expected_printed
                    logger.info(
                        f"Offset calculated via printed number match (phys_page={phys_idx}, "
                        f"printed={expected_printed}): offset={offset}"
                    )
                    return offset

        # Method 3: Check PDF Page Labels Metadata (if non-default)
        if page_labels and len(page_labels) == len(pages_text):
            target_label = str(first_entry.printed_page)
            for phys_idx, label in enumerate(page_labels):
                if str(label).strip() == target_label:
                    offset = phys_idx - first_entry.printed_page
                    logger.info(f"Offset calculated via PDF Page Labels metadata: offset={offset}")
                    return offset

        # Method 4: Fallback heuristic based on TOC page location
        if toc_page_indices:
            last_toc_idx = max(toc_page_indices)
            # Heuristic: First category printed page P1 is mapped to physical index (last_toc_idx + 1)
            # Or if P1 > 1, assume content page 1 starts right after TOC:
            # Phys page index of printed '1' = last_toc_idx + 1
            # Therefore phys page index of printed P1 = (last_toc_idx + 1) + (P1 - 1) = last_toc_idx + P1
            # Offset = Phys - P1 = (last_toc_idx + P1) - P1 = last_toc_idx
            offset = last_toc_idx
            logger.info(f"Offset calculated via TOC position fallback: offset={offset}")
            return offset

        logger.warning("All offset detection methods inconclusive. Defaulting offset to 0.")
        return 0

    def printed_to_physical(self, printed_page: int, offset: int, max_pages: int) -> int:
        """
        Converts a printed page number to a valid 0-based physical page index.
        """
        phys_idx = printed_page + offset
        return max(0, min(phys_idx, max_pages - 1))
