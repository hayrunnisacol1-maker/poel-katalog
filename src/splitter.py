"""
CatalogSplitter main orchestration module.
Coordinates PDF reading, TOC finding, entry parsing, offset calculation, and PDF splitting.
"""

from src import offset_calculator
from src import offset_calculator
import os
import sys
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.pdf_processor import PDFProcessor
    from src.toc_parser import TOCParser, TOCEntry
    from src.offset_calculator import OffsetCalculator
    from src.utils import sanitize_filename, setup_logging
except ModuleNotFoundError:
    from pdf_processor import PDFProcessor
    from toc_parser import TOCParser, TOCEntry
    from offset_calculator import OffsetCalculator
    from utils import sanitize_filename, setup_logging

logger = logging.getLogger("CatalogSplitter.Splitter")


@dataclass
class CategoryPDFInfo:
    category_name: str
    sanitized_filename: str
    output_path: str
    printed_start_page: int
    printed_end_page: int
    physical_start_idx: int
    physical_end_idx: int
    prefix_page_indices: List[int]
    total_output_pages: int


class CatalogSplitter:
    """
    Main controller for dynamic catalog splitting.
    """

    def __init__(self, pdf_path: str, output_dir: str, include_prefix: bool = False):
        self.pdf_path = os.path.abspath(pdf_path)
        self.output_dir = os.path.abspath(output_dir)
        self.include_prefix = include_prefix
        self.processor = PDFProcessor(self.pdf_path)
        self.toc_parser = TOCParser()
        self.offset_calculator = OffsetCalculator()

    def process(
        self,
        manual_offset: Optional[int] = None,
        include_prefix: Optional[bool] = None
    ) -> List[CategoryPDFInfo]:
        """
        Executes the catalog splitting pipeline.
        
        Args:
            manual_offset: Optional explicit page offset to override auto-calculation.
            include_prefix: Optional override for including cover/TOC pages in category PDFs.
            
        Returns:
            List of CategoryPDFInfo objects summarizing created PDFs.
        """
        if include_prefix is None:
            include_prefix = self.include_prefix

        logger.info(f"Starting catalog splitting for '{self.pdf_path}'...")
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Extract text from all pages
        pages_text = self.processor.extract_all_text()
        total_pages = len(pages_text)
        if total_pages == 0:
            raise ValueError("PDF file has no pages.")

        # 2. Find TOC pages
        toc_page_indices = self.toc_parser.find_toc_pages(pages_text)
        if not toc_page_indices:
            logger.warning("No TOC page automatically detected. Assuming page index 0 is TOC.")
            toc_page_indices = [0]

        logger.info(f"TOC page indices: {toc_page_indices}")

        # 3. Parse TOC entries (passing self.pdf_path for 2D visual layout support)
        toc_entries = self.toc_parser.parse_toc_entries(
            pages_text, toc_page_indices, pdf_path=self.pdf_path
        )
        if not toc_entries:
            raise ValueError("Could not extract any valid category entries from Table of Contents.")

        # 4. Calculate dynamic page offset
        if manual_offset is not None:
            offset = manual_offset
            logger.info(f"Using manual offset: {offset}")
        else:
            page_labels = self.processor.get_page_labels()
            offset = self.offset_calculator.calculate_offset(
                pages_text, toc_entries, toc_page_indices, page_labels
            )
        offset+=2
        logger.info(f"Final Page Offset: {offset} (Physical Index = Printed Page + {offset})")

        # 5. Determine prefix pages (Cover, Intro, Corporate, TOC up to first category start)
        first_cat_phys_start = self.offset_calculator.printed_to_physical(
            toc_entries[0].printed_page, offset, total_pages
        )
        
        prefix_end_idx = max(0, first_cat_phys_start - 1)
        if prefix_end_idx < max(toc_page_indices):
            prefix_end_idx = max(toc_page_indices)

        prefix_indices = list(range(0, prefix_end_idx + 1))
        logger.info(f"Common Front/Prefix Page Indices (Cover/Intro/TOC): {prefix_indices}")

        # 6. Calculate page ranges for each category and build PDFs
        created_pdfs: List[CategoryPDFInfo] = []
        used_filenames: Dict[str, int] = {}

        for i, entry in enumerate(toc_entries):
            cat_name = entry.category_name
            printed_start = entry.printed_page

            if i + 1 < len(toc_entries):
                printed_end = toc_entries[i + 1].printed_page - 1
            else:
                max_printed = (total_pages - 1) - offset
                printed_end = max(printed_start, max_printed)
            
            if printed_end < printed_start:
                printed_end = printed_start
            
            phys_start = self.offset_calculator.printed_to_physical(printed_start, offset, total_pages)
            phys_end = self.offset_calculator.printed_to_physical(printed_end, offset, total_pages)

            cat_page_indices = list(range(phys_start, phys_end + 1))

            if include_prefix:
                combined_indices = list(prefix_indices)
                for p_idx in cat_page_indices:
                    if p_idx not in combined_indices:
                        combined_indices.append(p_idx)
            else:
                combined_indices = cat_page_indices

            clean_cat = sanitize_filename(cat_name, fallback_name=f"kategori_{i+1}")
            base_filename = f"{i+1:02d}. {clean_cat}"
            if base_filename in used_filenames:
                used_filenames[base_filename] += 1
                filename = f"{base_filename}_{used_filenames[base_filename]}.pdf"
            else:
                used_filenames[base_filename] = 1
                filename = f"{base_filename}.pdf"

            output_path = os.path.join(self.output_dir, filename)

            success = self.processor.create_pdf_from_pages(combined_indices, output_path)
            if success:
                info = CategoryPDFInfo(
                    category_name=cat_name,
                    sanitized_filename=filename,
                    output_path=output_path,
                    printed_start_page=printed_start,
                    printed_end_page=printed_end,
                    physical_start_idx=phys_start,
                    physical_end_idx=phys_end,
                    prefix_page_indices=prefix_indices if include_prefix else [],
                    total_output_pages=len(combined_indices)
                )
                created_pdfs.append(info)
                logger.info(
                    f"Created '{filename}' | Printed: {printed_start}-{printed_end} | "
                    f"Phys: {phys_start}-{phys_end} | Total Pages: {len(combined_indices)}"
                )

        logger.info(f"Catalog splitting complete. Generated {len(created_pdfs)} category PDFs.")
        return created_pdfs

