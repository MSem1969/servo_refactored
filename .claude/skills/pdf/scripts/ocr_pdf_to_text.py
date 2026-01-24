#!/usr/bin/env python3
"""
OCR PDF to Text Extractor

Estrae testo da PDF scansionati (senza testo ricercabile) usando Tesseract OCR.
Utile per ordini vendor scansionati o documenti in formato immagine.

Usage:
    python ocr_pdf_to_text.py <input.pdf> [output.txt] [--lang ita]
"""

import sys
import os
from pathlib import Path

try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install with: pip install pdf2image pytesseract pillow")
    sys.exit(1)


def extract_text_from_pdf_ocr(pdf_path: str, language: str = 'ita+eng', dpi: int = 300) -> str:
    """
    Estrae testo da PDF usando OCR.

    Args:
        pdf_path: Path al file PDF
        language: Lingua/e per Tesseract (es: 'ita', 'eng', 'ita+eng')
        dpi: Risoluzione per conversione (più alto = migliore qualità ma più lento)

    Returns:
        Testo estratto
    """
    print(f"📄 Converting PDF to images (DPI: {dpi})...")
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
    except Exception as e:
        print(f"❌ Error converting PDF to images: {e}")
        print("Note: Ensure poppler-utils is installed (sudo apt-get install poppler-utils)")
        sys.exit(1)

    print(f"✅ Converted {len(images)} page(s)")

    full_text = []
    for i, image in enumerate(images, start=1):
        print(f"🔍 Processing page {i}/{len(images)} with OCR (lang: {language})...")
        try:
            # Estrai testo usando Tesseract
            text = pytesseract.image_to_string(image, lang=language)
            full_text.append(f"--- PAGE {i} ---\n{text}\n")
        except Exception as e:
            print(f"⚠️  Error processing page {i}: {e}")
            full_text.append(f"--- PAGE {i} ---\n[OCR ERROR: {e}]\n")

    return "\n".join(full_text)


def main():
    if len(sys.argv) < 2:
        print("Usage: ocr_pdf_to_text.py <input.pdf> [output.txt] [--lang LANG]")
        print("\nExamples:")
        print("  python ocr_pdf_to_text.py ordine.pdf")
        print("  python ocr_pdf_to_text.py ordine.pdf extracted.txt")
        print("  python ocr_pdf_to_text.py ordine.pdf output.txt --lang ita")
        print("  python ocr_pdf_to_text.py ordine.pdf output.txt --lang eng")
        print("  python ocr_pdf_to_text.py ordine.pdf output.txt --lang ita+eng")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None

    # Parse language option
    language = 'ita+eng'  # Default: italiano + inglese
    if '--lang' in sys.argv:
        lang_idx = sys.argv.index('--lang')
        if lang_idx + 1 < len(sys.argv):
            language = sys.argv[lang_idx + 1]

    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    print(f"🚀 Starting OCR extraction...")
    print(f"   Input: {pdf_path}")
    print(f"   Language: {language}")

    # Estrai testo
    text = extract_text_from_pdf_ocr(pdf_path, language=language)

    # Salva o stampa
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n✅ Text extracted to: {output_path}")
        print(f"   Total characters: {len(text)}")
    else:
        print("\n" + "="*80)
        print("EXTRACTED TEXT:")
        print("="*80)
        print(text)
        print("="*80)
        print(f"Total characters: {len(text)}")


if __name__ == "__main__":
    main()
