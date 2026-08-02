"""
Unit and Integration Tests for Dynamic Catalog Splitter.
"""

import unittest
import os
import shutil
import tempfile
from pypdf import PdfReader

from src.utils import sanitize_filename, normalize_text
from src.toc_parser import TOCParser, TOCEntry
from src.offset_calculator import OffsetCalculator
from src.pdf_processor import PDFProcessor
from src.splitter import CatalogSplitter
from tests.create_sample_catalog import build_sample_catalog


class TestUtils(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("POMPALAR"), "POMPALAR")
        self.assertEqual(sanitize_filename("Vana / Filtre * Sürgülü?"), "Vana Filtre Sürgülü")
        self.assertEqual(sanitize_filename("   "), "kategori")
        self.assertEqual(sanitize_filename("FİLTRELER & AKSESUARLAR"), "FİLTRELER & AKSESUARLAR")

    def test_normalize_text(self):
        self.assertEqual(normalize_text("içindekiler"), "İÇİNDEKİLER")
        self.assertEqual(normalize_text("Pompalar  ve   Vanalar"), "POMPALAR VE VANALAR")


class TestTOCParser(unittest.TestCase):
    def setUp(self):
        self.parser = TOCParser()

    def test_find_toc_pages(self):
        pages_text = [
            "KAPAK SAYFASI",
            "TANITIM SAYFASI",
            "İÇİNDEKİLER\nPOMPALAR ........ 12\nVANALAR ......... 34",
            "İÇERİK DEVAMI\nFİLTRELER ....... 58"
        ]
        indices = self.parser.find_toc_pages(pages_text)
        self.assertIn(2, indices)
        self.assertIn(3, indices)

    def test_parse_toc_entries(self):
        pages_text = [
            "",
            "",
            "İÇİNDEKİLER\nPOMPALAR ............................ 12\nVANALAR ............................. 34\nFİLTRELER ........................... 58\n"
        ]
        entries = self.parser.parse_toc_entries(pages_text, [2])
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].category_name, "POMPALAR")
        self.assertEqual(entries[0].printed_page, 12)
        self.assertEqual(entries[1].category_name, "VANALAR")
        self.assertEqual(entries[1].printed_page, 34)
        self.assertEqual(entries[2].category_name, "FİLTRELER")
        self.assertEqual(entries[2].printed_page, 58)

    def test_ignore_pure_digit_clusters(self):
        pages_text = [
            "",
            "",
            "İÇİNDEKİLER\n06 08 10\n30 42 52 69\nSOLENOİD VANA ........ 8\n"
        ]
        entries = self.parser.parse_toc_entries(pages_text, [2])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].category_name, "SOLENOİD VANA")
        self.assertEqual(entries[0].printed_page, 8)

    def test_clean_title(self):
        raw = "CUP / BT C U B P T M PİLLİ SULAMA A A KONTROL ÜNİTESİ"
        cleaned = TOCParser._clean_title(raw)
        self.assertEqual(cleaned, "CUP / BT PİLLİ SULAMA KONTROL ÜNİTESİ")


class TestOffsetCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = OffsetCalculator()

    def test_calculate_offset_via_text_search(self):
        pages_text = [
            "KAPAK",
            "TANITIM",
            "İÇİNDEKİLER\nPOMPALAR .... 12",
            "ÖN SAYFA 1",
            "POMPALAR KATEGORİSİ SAYFA 12" # Index 4, Printed page 12 -> Offset = 4 - 12 = -8
        ]
        toc_entries = [TOCEntry(category_name="POMPALAR", printed_page=12, raw_line="", toc_page_index=2)]
        offset = self.calc.calculate_offset(pages_text, toc_entries, [2])
        self.assertEqual(offset, -8)


class TestCatalogSplitterIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.catalog_path = os.path.join(cls.temp_dir, "sample_catalog.pdf")
        cls.output_dir = os.path.join(cls.temp_dir, "output")
        build_sample_catalog(cls.catalog_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_splitter_end_to_end_with_prefix(self):
        splitter = CatalogSplitter(self.catalog_path, self.output_dir, include_prefix=True)
        results = splitter.process()

        self.assertEqual(len(results), 4)

        # Check created files exist
        pompalar_file = os.path.join(self.output_dir, "01. POMPALAR.pdf")
        vanalar_file = os.path.join(self.output_dir, "02. VANALAR.pdf")
        self.assertTrue(os.path.exists(pompalar_file))
        self.assertTrue(os.path.exists(vanalar_file))

        # Verify page count of POMPALAR.pdf with prefix (Prefix 14 pages + 22 category pages = 36)
        reader = PdfReader(pompalar_file)
        self.assertEqual(len(reader.pages), 36)

        # Check prefix contents in generated PDF (Page 0 must be Cover)
        first_page_text = reader.pages[0].extract_text()
        self.assertIn("KAPAK", first_page_text)

        # Check TOC page in prefix (Page 2 must be TOC)
        toc_page_text = reader.pages[2].extract_text()
        self.assertIn("TABLE OF CONTENTS", toc_page_text)

    def test_splitter_end_to_end_without_prefix(self):
        output_dir_no_prefix = os.path.join(self.temp_dir, "output_no_prefix")
        splitter = CatalogSplitter(self.catalog_path, output_dir_no_prefix, include_prefix=False)
        results = splitter.process()

        self.assertEqual(len(results), 4)
        pompalar_file = os.path.join(output_dir_no_prefix, "01. POMPALAR.pdf")
        reader = PdfReader(pompalar_file)
        self.assertEqual(len(reader.pages), 22)


if __name__ == "__main__":
    unittest.main()

