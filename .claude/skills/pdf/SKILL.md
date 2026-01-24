# PDF Processing Skill

## Overview
This skill provides comprehensive PDF manipulation capabilities through Python libraries and command-line tools. The toolkit handles text/table extraction, document creation, merging, splitting, and form processing.

## Core Libraries

**pypdf** manages basic operations like merging documents, splitting pages, extracting metadata, and rotating content. It also supports password protection and watermarking.

**pdfplumber** specializes in text and table extraction with layout preservation, enabling conversion of tabular data into pandas DataFrames and Excel exports.

**reportlab** creates PDFs programmatically, supporting both simple canvas-based drawings and complex multi-page documents using Platypus for structured content.

## Command-Line Tools

- **pdftotext** (poppler-utils): Extracts text with optional layout preservation and page range selection
- **qpdf**: Performs merging, splitting, rotation, and encryption operations
- **pdftk**: Alternative for merging, bursting, and page rotation

## Advanced Capabilities

The skill handles specialized tasks including:
- OCR for scanned documents (pytesseract + pdf2image)
- Image extraction from PDFs
- Watermark application across pages
- Form filling (detailed in separate forms.md guide)

## Key Reference

For Python work, pdfplumber excels at extraction, pypdf handles transformations, and reportlab creates new documents. The documentation cross-references advanced topics in reference.md and form-specific instructions in forms.md.

## Scripts Available

The following scripts are available in the `scripts/` directory:

1. **check_fillable_fields.py** - Check if a PDF has fillable form fields
2. **extract_form_field_info.py** - Extract form field information to JSON
3. **convert_pdf_to_images.py** - Convert PDF pages to PNG images
4. **fill_fillable_fields.py** - Fill fillable form fields from JSON
5. **fill_pdf_form_with_annotations.py** - Fill non-fillable forms with text annotations
6. **create_validation_image.py** - Create validation images with bounding boxes
7. **check_bounding_boxes.py** - Validate bounding boxes for overlap

## Required Python Packages

To use this skill, ensure the following packages are installed:

```bash
pip install pypdf pdfplumber reportlab pdf2image pytesseract pillow
```

For command-line tools:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils qpdf pdftk

# macOS
brew install poppler qpdf pdftk-java
```
