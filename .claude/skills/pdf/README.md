# PDF Skill for Claude Code

This skill provides comprehensive PDF manipulation capabilities for Claude Code, sourced from the official Anthropic skills repository.

## Installation

### 1. Install Required Python Packages

```bash
cd /home/jobseminara/servo_refactored
source backend/venv/bin/activate
pip install pypdf pdfplumber reportlab pdf2image pytesseract pillow
```

### 2. Install System Dependencies

✅ **Already installed in this project:**

```bash
# Ubuntu/Debian (ALREADY INSTALLED)
✅ poppler-utils (v22.12.0)
✅ qpdf (v11.3.0)
✅ tesseract-ocr (v5.3.0)
✅ tesseract-ocr-ita
✅ tesseract-ocr-eng

# For fresh installation:
sudo apt-get update
sudo apt-get install poppler-utils qpdf tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng

# macOS
brew install poppler qpdf tesseract tesseract-lang
```

### 3. Verify Installation

```bash
python .claude/skills/pdf/scripts/check_fillable_fields.py --help
```

## Usage in Claude Code

Once installed, you can use this skill in Claude Code by referencing it in your prompts:

```
"Use the PDF skill to extract form fields from backend/uploads/example.pdf"
```

## Available Scripts

All scripts are located in `.claude/skills/pdf/scripts/`:

1. **check_fillable_fields.py** - Check if a PDF has fillable form fields
   ```bash
   python scripts/check_fillable_fields.py <input.pdf>
   ```

2. **extract_form_field_info.py** - Extract form field information to JSON
   ```bash
   python scripts/extract_form_field_info.py <input.pdf> <output.json>
   ```

3. **convert_pdf_to_images.py** - Convert PDF pages to PNG images
   ```bash
   python scripts/convert_pdf_to_images.py <input.pdf> <output_directory>
   ```

4. **fill_fillable_fields.py** - Fill fillable form fields from JSON
   ```bash
   python scripts/fill_fillable_fields.py <input.pdf> <field_values.json> <output.pdf>
   ```

5. **fill_pdf_form_with_annotations.py** - Fill non-fillable forms with text annotations
   ```bash
   python scripts/fill_pdf_form_with_annotations.py <input.pdf> <fields.json> <output.pdf>
   ```

6. **create_validation_image.py** - Create validation images with bounding boxes
   ```bash
   python scripts/create_validation_image.py <page_number> <fields.json> <input_image> <output_image>
   ```

7. **check_bounding_boxes.py** - Validate bounding boxes for overlap
   ```bash
   python scripts/check_bounding_boxes.py <fields.json>
   ```

8. **ocr_pdf_to_text.py** - Extract text from scanned PDFs using OCR (NEW)
   ```bash
   python scripts/ocr_pdf_to_text.py <input.pdf> [output.txt] [--lang ita+eng]
   ```

## Documentation

- **SKILL.md** - Main skill documentation and overview
- **forms.md** - Detailed guide for filling PDF forms (fillable and non-fillable)
- **reference.md** - Advanced reference for Python and JavaScript libraries
- **LICENSE.txt** - Anthropic Materials License

## Integration with SERV.O Project

This skill can be used to enhance PDF processing capabilities in the SERV.O pharmaceutical order extraction system:

- Extract additional metadata from vendor PDFs
- Fill out ministerial forms programmatically
- Generate filled PDF documents for administrative purposes
- Validate and process uploaded PDF documents

## Source

This skill is replicated from the official Anthropic skills repository:
https://github.com/anthropics/skills/tree/main/skills/pdf

## License

Use of these materials is governed by the Anthropic Materials License.
See LICENSE.txt for details.
