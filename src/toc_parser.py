"""
Module for detecting and parsing Table of Contents (TOC / İçindekiler) from PDF pages.
"""

import os
import sys
from dataclasses import dataclass
import re
import logging
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.config import TOC_KEYWORDS, TOC_LINE_PATTERNS, MAX_TOC_SEARCH_PAGES
    from src.utils import normalize_text
except ModuleNotFoundError:
    from config import TOC_KEYWORDS, TOC_LINE_PATTERNS, MAX_TOC_SEARCH_PAGES
    from utils import normalize_text

logger = logging.getLogger("CatalogSplitter.TOCParser")


@dataclass
class TOCEntry:
    category_name: str
    printed_page: int
    raw_line: str
    toc_page_index: int


class TOCParser:
    """
    Parses Table of Contents from extracted PDF page text.
    """

    def __init__(self, keywords: Optional[List[str]] = None):
        self.keywords = keywords or TOC_KEYWORDS

    def find_toc_pages(self, pages_text: List[str]) -> List[int]:
        """
        Scans PDF pages to find physical page indices (0-based) containing Table of Contents.
        
        Args:
            pages_text: List of text content for each physical PDF page.
            
        Returns:
            List of page indices where TOC is located.
        """
        toc_indices = []
        max_scan = min(len(pages_text), MAX_TOC_SEARCH_PAGES)

        for idx in range(max_scan):
            text = pages_text[idx]
            if not text or not text.strip():
                continue

            normalized_text = normalize_text(text)
            
            # Check 1: Explicit keyword match in header/top area
            has_keyword = any(kw in normalized_text for kw in self.keywords)

            # Check 2: High density of leader dots or numbers
            dots_count = text.count("...") + text.count("…") + text.count(". . .")
            entry_matches = 0
            for pattern in TOC_LINE_PATTERNS:
                matches = pattern.findall(text)
                entry_matches += len(matches)

            if has_keyword or dots_count >= 3 or entry_matches >= 2:
                logger.info(f"Detected TOC page at physical index {idx} (keyword={has_keyword}, matches={entry_matches})")
                toc_indices.append(idx)

        # Handle contiguous TOC pages (e.g. TOC spans page 2 and page 3)
        if not toc_indices:
            logger.warning("No explicit TOC keyword page found. Falling back to scanning all early pages for entry patterns.")
            for idx in range(max_scan):
                text = pages_text[idx]
                for pattern in TOC_LINE_PATTERNS:
                    if len(pattern.findall(text)) >= 2:
                        toc_indices.append(idx)
                        break

        return toc_indices

    def parse_toc_entries(
        self,
        pages_text: List[str],
        toc_page_indices: List[int],
        pdf_path: Optional[str] = None
    ) -> List[TOCEntry]:
        """
        Extracts structured TOC entries (category name, printed page number) from TOC pages.
        Supports both 2D visual grid layout parsing (via PyMuPDF fitz) and line-by-line pattern parsing.
        
        Args:
            pages_text: List of text content for all PDF pages.
            toc_page_indices: Indices of physical pages identified as containing TOC.
            pdf_path: Optional absolute path to the PDF file for visual layout extraction.
            
        Returns:
            List of TOCEntry sorted by printed_page.
        """
        entries: List[TOCEntry] = []

        # 1. Attempt 2D Visual Grid Parsing if PDF has no dot leaders (is a visual grid TOC)
        if pdf_path and os.path.exists(pdf_path):
            combined_toc_text = " ".join([pages_text[i] for i in toc_page_indices if i < len(pages_text)])
            dots_count = (
                combined_toc_text.count("...") +
                combined_toc_text.count("…") +
                combined_toc_text.count(". . .") +
                combined_toc_text.count("----")
            )
            
            # If no heavy dot-leader lines exist, attempt 2D Visual Grid layout parsing
            if dots_count < 2:
                try:
                    visual_entries = self._parse_visual_toc_entries(pdf_path, toc_page_indices)
                    if visual_entries:
                        logger.info(f"Successfully extracted {len(visual_entries)} entries using 2D Visual Grid Parser.")
                        entries.extend(visual_entries)
                except Exception as e:
                    logger.debug(f"Visual 2D TOC parser skipped or failed: {e}")

        # 2. Fallback to line-by-line regex pattern parsing if 2D parsing yielded no entries
        if not entries:
            for page_idx in toc_page_indices:
                if page_idx >= len(pages_text):
                    continue
                    
                page_text = pages_text[page_idx]
                lines = page_text.splitlines()

                for line in lines:
                    line_str = line.strip()
                    if not line_str:
                        continue

                    # Skip header lines that just say "İÇİNDEKİLER" or "CONTENTS"
                    norm_line = normalize_text(line_str)
                    if norm_line in [normalize_text(kw) for kw in self.keywords]:
                        continue

                    # Try matching line with configured regex patterns
                    matched = False
                    for pattern in TOC_LINE_PATTERNS:
                        match = pattern.search(line_str)
                        if match:
                            try:
                                title_raw = match.group("title").strip()
                                page_num = int(match.group("page"))

                                title = self._clean_title(title_raw)
                                norm_title = normalize_text(title)

                                # Filter out suspicious, footer labels ('Sayfa 3'), or header entries
                                if len(title) >= 2 and page_num > 0:
                                    if norm_title in ['SAYFA', 'PAGE', 'SAYFA NO', 'PAGE NO'] or norm_title in [normalize_text(kw) for kw in self.keywords]:
                                        continue
                                    
                                    entries.append(TOCEntry(
                                        category_name=title,
                                        printed_page=page_num,
                                        raw_line=line_str,
                                        toc_page_index=page_idx
                                    ))
                                    matched = True
                                    break
                            except (ValueError, IndexError):
                                continue
                        if matched:
                            break

        # Remove duplicate entries for the same printed page or category name
        unique_entries: List[TOCEntry] = []
        seen_combos = set()
        seen_pages = set()
        
        for entry in entries:
            combo = (normalize_text(entry.category_name), entry.printed_page)
            if combo not in seen_combos and entry.printed_page not in seen_pages:
                seen_combos.add(combo)
                seen_pages.add(entry.printed_page)
                unique_entries.append(entry)

        # Sort entries strictly by printed_page ascending
        unique_entries.sort(key=lambda e: e.printed_page)

        logger.info(f"Extracted {len(unique_entries)} category entries from TOC.")
        for e in unique_entries:
            logger.debug(f"  Category: '{e.category_name}' -> Printed Page: {e.printed_page}")

        return unique_entries

    def _parse_visual_toc_entries(self, pdf_path: str, toc_page_indices: List[int]) -> List[TOCEntry]:
        """
        Parses visual 2D grid Table of Contents using PyMuPDF (fitz) spatial block matching.
        """
        try:
            import fitz
        except ImportError:
            return []

        entries: List[TOCEntry] = []
        doc = fitz.open(pdf_path)

        for p_idx in toc_page_indices:
            if p_idx < 0 or p_idx >= len(doc):
                continue

            page = doc[p_idx]
            words = page.get_text('words')
            blocks = page.get_text('dict')['blocks']

            # Identify page number words (1 to 3 digits)
            num_words = []
            for w in words:
                text = w[4].strip()
                if text.isdigit() and 1 <= len(text) <= 3 and int(text) > 0:
                    num_words.append((w[0], w[1], w[2], w[3], int(text)))

            # Sort numbers left-to-right, top-to-bottom
            num_words.sort(key=lambda x: (x[1], x[0]))

            # Collect non-numeric title lines with bounding boxes
            title_lines = []
            header_terms = [
                'İÇİNDEKİLER', 'INDEX', 'CONTENTS', 'AUTOMATIC RAIN', 'VALVES, VALVE BOXES',
                'PLASTİK FİLTRE VALVES', 'SPECIAL PRODUCTION', 'SULAMA SİSTEMLERİ'
            ]
            for b in blocks:
                if b.get('type') == 0:
                    for line in b['lines']:
                        line_text = ''.join([s['text'] for s in line['spans']]).strip()
                        if not line_text or not re.search(r'[A-Za-zĞÜŞİÖÇa-zğüşiöç]', line_text):
                            continue
                        norm_line = normalize_text(line_text)
                        if any(kw in norm_line for kw in [normalize_text(h) for h in header_terms]):
                            continue
                        title_lines.append({'bbox': line['bbox'], 'text': line_text})

            # Match each page number with its title block directly above it
            for nx0, ny0, nx1, ny1, num_val in num_words:
                n_center_x = (nx0 + nx1) / 2
                col_lines = []

                for tl in title_lines:
                    tx0, ty0, tx1, ty1 = tl['bbox']
                    # Title line must be vertically above the number (within 120pt)
                    if ty1 <= ny0 + 10 and ty0 >= ny0 - 120:
                        dx = abs((tx0 + tx1)/2 - n_center_x)
                        if dx < 80 or (tx0 <= n_center_x <= tx1):
                            col_lines.append((ty0, tl['text']))

                if col_lines:
                    col_lines.sort(key=lambda x: x[0])
                    raw_title = ' '.join([t[1] for t in col_lines])
                    cleaned = self._clean_title(raw_title)
                    if len(cleaned) >= 2 and not cleaned.isdigit():
                        entries.append(TOCEntry(
                            category_name=cleaned,
                            printed_page=num_val,
                            raw_line=raw_title,
                            toc_page_index=p_idx
                        ))

        doc.close()
        return entries

    @staticmethod
    def _clean_title(title_raw: str) -> str:
        """
        Cleans raw category titles by removing single letter vertical text artifacts,
        English translation subtitles, and extra punctuation.
        """
        if not title_raw:
            return ""

        title = re.sub(r'^[\.\-\_\s]+|[\.\-\_\s]+$', '', title_raw).strip()

        # Filter out standalone single-char vertical artifacts except valid symbols/digits
        words = title.split()
        filtered_words = []
        for w in words:
            w_clean = re.sub(r'[^A-ZĞÜŞİÖÇa-zğüşiöç0-9\/\(\)\-\&]', '', w)
            if not w_clean:
                continue
            if len(w_clean) > 1 or w_clean in ['&', '/'] or w_clean.isdigit():
                filtered_words.append(w_clean)

        title = ' '.join(filtered_words)

        # Remove duplicate consecutive words
        unique_words = []
        for w in title.split():
            if not unique_words or unique_words[-1].upper() != w.upper():
                unique_words.append(w)
        title = ' '.join(unique_words)

        # Remove trailing English translation keywords if Turkish category title is present
        english_keywords = [
            'CONTROLLER', 'VALVE', 'VALVES', 'SPRAYS', 'NOZZLES', 'ELECTROFUSION',
            'SPIGOT', 'FITTINGS', 'SERIES', 'CLAMP', 'SADDLES', 'BALL', 'COUPLING',
            'PLASTIC', 'FILTER', 'BOXES', 'FLUSH', 'BARBED', 'DRIPLINE', 'NUT',
            'RING', 'MINISPRINKLERS', 'DRIPPER', 'SPECIAL', 'PRODUCTION', 'DRIP',
            'TAPE', 'LINE', 'LOCK', 'TYPE', 'WITH', 'AND', 'ON', 'SLIDE'
        ]

        clean_words = []
        for w in title.split():
            if w.upper() in english_keywords and len(clean_words) >= 1:
                break
            clean_words.append(w)

        res = ' '.join(clean_words).strip()
        res = re.sub(r'[\.\·\-\–\—\_]+', ' ', res)
        res = re.sub(r'\s+', ' ', res).strip()
        return res

