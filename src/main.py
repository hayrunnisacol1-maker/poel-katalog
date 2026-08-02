"""
CLI Entry Point for Dinamik Katalog Ayırma Otomasyonu.
"""

import sys
import os
import argparse
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.splitter import CatalogSplitter
from src.utils import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Dinamik Katalog Ayırma Otomasyonu - PDF Kataloglarını İçindekiler sayfasına göre otomatik böler."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Bölünecek PDF katalog dosyasının yolu."
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Oluşturulan kategori PDF'lerinin kaydedileceği klasör (Varsayılan: ./output)."
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Manuel sayfa offset değeri (isteğe bağlı). Belirtilmezse otomatik hesaplanır."
    )
    parser.add_argument(
        "--include-prefix",
        action="store_true",
        help="Ayrılan her PDF'in başına ortak kapak ve içindekiler sayfalarını da ekler."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Detaylı (DEBUG) log çıktısını aktifleştir."
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger("CatalogSplitter.Main")

    if not os.path.exists(args.input):
        logger.error(f"Hata: Belirtilen PDF dosyası bulunamadı: {args.input}")
        sys.exit(1)

    try:
        splitter = CatalogSplitter(pdf_path=args.input, output_dir=args.output, include_prefix=args.include_prefix)
        results = splitter.process(manual_offset=args.offset)

        print("\n" + "=" * 80)
        print(" KATALOG AYIRMA İŞLEMİ BAŞARIYLA TAMAMLANDI")
        print("=" * 80)
        print(f"{'Kategori Adı':<25} | {'Basılı Sayfalar':<15} | {'Fiziksel Indeksler':<18} | {'Dosya Adı'}")
        print("-" * 80)

        for info in results:
            printed_range = f"{info.printed_start_page} - {info.printed_end_page}"
            phys_range = f"{info.physical_start_idx} - {info.physical_end_idx}"
            print(f"{info.category_name[:24]:<25} | {printed_range:<15} | {phys_range:<18} | {info.sanitized_filename}")

        print("=" * 80)
        print(f"Toplam {len(results)} kategori PDF'i '{os.path.abspath(args.output)}' klasörüne kaydedildi.\n")

    except Exception as e:
        logger.error(f"Katalog işlenirken bir hata oluştu: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
