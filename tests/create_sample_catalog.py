"""
Script to generate a synthetic sample catalog PDF for testing the CatalogSplitter.
"""

import os
from pypdf import PdfWriter, PageObject
from pypdf.generic import NameObject, DictionaryObject, EncodedStreamObject, create_string_object


def create_minimal_pdf_with_pages(pages_data, output_path):
    """
    Creates a valid PDF file where each page contains text provided in pages_data.
    """
    writer = PdfWriter()

    for text_lines in pages_data:
        page = PageObject.create_blank_page(width=612, height=792)
        
        pdf_text_ops = ["BT", "/F1 12 Tf", "50 750 Td", "14 TL"]
        for line in text_lines:
            escaped_line = line.replace("(", "\\(").replace(")", "\\)")
            pdf_text_ops.append(f"({escaped_line}) Tj")
            pdf_text_ops.append("T*")
        pdf_text_ops.append("ET")

        content_stream_bytes = "\n".join(pdf_text_ops).encode("latin1", errors="replace")

        # Create Font dictionary
        font_dict = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding")
        })
        font_ref = writer._add_object(font_dict)

        # Create Resources dictionary
        resources_dict = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): font_ref
            })
        })
        page[NameObject("/Resources")] = resources_dict

        # Create Stream Object
        stream_obj = EncodedStreamObject()
        stream_obj._data = content_stream_bytes
        stream_ref = writer._add_object(stream_obj)
        page[NameObject("/Contents")] = stream_ref

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Created sample PDF with {len(pages_data)} pages at '{output_path}'.")


def build_sample_catalog(output_path="./data/sample_catalog.pdf"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    pages = []

    # Physical Page 0 (Kapak)
    pages.append([
        "POELSAN KATALOG 2026",
        "KAPAK SAYFASI",
        "Hosgeldiniz"
    ])

    # Physical Page 1 (Tanıtım)
    pages.append([
        "KURUMSAL VE TANITIM",
        "Poelsan Boru ve Vana Sistemleri Sanayi",
        "Kalite ve Guven"
    ])

    # Physical Page 2 (İçindekiler)
    pages.append([
        "ICINDEKILER / TABLE OF CONTENTS",
        "",
        "POMPALAR ....................................... 12",
        "VANALAR ........................................ 34",
        "FILTRELER ...................................... 58",
        "AKSESUARLAR .................................... 81",
        "",
        "Sayfa 3"
    ])

    # Physical Pages 3..13 (Printed Pages 1..11 - Intro pages)
    for p in range(3, 14):
        printed_num = p - 2
        pages.append([
            "POELSAN KATALOG - GENEL BILGILER",
            "On Bilgiler ve Dokumantasyon",
            f"Sayfa {printed_num}"
        ])

    # Physical Pages 14..35 (POMPALAR: Printed 12..33)
    for p in range(14, 36):
        printed_num = p - 2
        pages.append([
            "POMPALAR KATEGORISI",
            f"Model P-{printed_num} Yuksek Basinc Pompa",
            f"Teknik Detaylar ve Ozellikler",
            f"Sayfa {printed_num}"
        ])

    # Physical Pages 36..59 (VANALAR: Printed 34..57)
    for p in range(36, 60):
        printed_num = p - 2
        pages.append([
            "VANALAR KATEGORISI",
            f"Model V-{printed_num} Kelebek Vana",
            f"Basinc Sinifi PN16",
            f"Sayfa {printed_num}"
        ])

    # Physical Pages 60..82 (FİLTRELER: Printed 58..80)
    for p in range(60, 83):
        printed_num = p - 2
        pages.append([
            "FILTRELER KATEGORISI",
            f"Model F-{printed_num} Disk Filtre",
            f"Sayfa {printed_num}"
        ])

    # Physical Pages 83..99 (AKSESUARLAR: Printed 81..97)
    for p in range(83, 100):
        printed_num = p - 2
        pages.append([
            "AKSESUARLAR KATEGORISI",
            f"Model A-{printed_num} Baglanti Elemani",
            f"Sayfa {printed_num}"
        ])

    create_minimal_pdf_with_pages(pages, output_path)
    return output_path


if __name__ == "__main__":
    build_sample_catalog()
