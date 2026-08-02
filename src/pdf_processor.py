"""
Module for PDF reading, text extraction, and page range extraction using pypdf.
"""

import os
import logging
from typing import List, Tuple, Optional
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger("CatalogSplitter.PDFProcessor")


class PDFProcessor:
    """
    Handles PDF loading, text extraction per page, and writing selected page ranges into new PDF files.
    """

    def __init__(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        self.pdf_path = pdf_path
        self.reader = PdfReader(pdf_path)

    @property
    def total_pages(self) -> int:
        return len(self.reader.pages)

    def extract_all_text(self) -> List[str]:
        """
        Extracts text content from each page of the PDF.
        Returns a list of strings, indexed by 0-based page number.
        """
        pages_text: List[str] = []
        logger.info(f"Extracting text from {self.total_pages} pages in '{os.path.basename(self.pdf_path)}'...")

        for idx, page in enumerate(self.reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning(f"Error extracting text from page index {idx}: {e}")
                text = ""
            pages_text.append(text)

        return pages_text

    def get_page_labels(self) -> Optional[List[str]]:
        """
        Retrieves page labels if available in PDF metadata.
        """
        try:
            if hasattr(self.reader, 'page_labels') and self.reader.page_labels:
                return [str(lbl) for lbl in self.reader.page_labels]
        except Exception as e:
            logger.debug(f"Could not retrieve page labels: {e}")
        return None

    def create_pdf_from_pages(self, page_indices: List[int], output_path: str) -> bool:
        """
        Creates a new PDF file consisting of the pages specified in page_indices.
        
        Args:
            page_indices: Ordered list of 0-based physical page indices to include.
            output_path: Path where the output PDF should be saved.
            
        Returns:
            True if creation succeeded, False otherwise.
        """
        try:
            # Ensure target directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            writer = PdfWriter()
            added_count = 0

            for idx in page_indices:
                if 0 <= idx < self.total_pages:
                    writer.add_page(self.reader.pages[idx])
                    added_count += 1
                else:
                    logger.warning(f"Page index {idx} out of range (0..{self.total_pages-1}), skipping.")

            if added_count == 0:
                logger.error(f"No valid pages to write for '{output_path}'.")
                return False

            with open(output_path, "wb") as out_file:
                writer.write(out_file)

            logger.info(f"Successfully saved {added_count} pages to '{output_path}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to create PDF at '{output_path}': {e}", exc_info=True)
            return False
