#!/bin/bash

# Test script per verificare installazione PDF skill
# Uso: bash .claude/skills/pdf/test_skill.sh [path_to_test.pdf]

set -e

echo "🔍 Testing PDF Skill Installation..."
echo ""

# Attiva venv
if [ -f "backend/venv/bin/activate" ]; then
    source backend/venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at backend/venv/bin/activate"
    exit 1
fi

# Verifica pacchetti Python
echo ""
echo "📦 Checking Python packages..."
python -c "import pypdf; print('✅ pypdf installed:', pypdf.__version__)"
python -c "import pdfplumber; print('✅ pdfplumber installed:', pdfplumber.__version__)"
python -c "import reportlab; print('✅ reportlab installed:', reportlab.__version__)"
python -c "import pdf2image; print('✅ pdf2image installed')"
python -c "from PIL import Image; print('✅ pillow installed')"
python -c "import pytesseract; print('✅ pytesseract installed:', pytesseract.__version__)"

# Verifica tool di sistema
echo ""
echo "🔧 Checking system tools..."
if command -v pdftotext &> /dev/null; then
    echo "✅ pdftotext available (poppler-utils)"
else
    echo "⚠️  pdftotext not found - install with: sudo apt-get install poppler-utils"
fi

if command -v qpdf &> /dev/null; then
    echo "✅ qpdf available"
else
    echo "⚠️  qpdf not found - install with: sudo apt-get install qpdf"
fi

if command -v tesseract &> /dev/null; then
    TESS_VERSION=$(tesseract --version 2>&1 | head -1)
    echo "✅ tesseract available ($TESS_VERSION)"
    LANGS=$(tesseract --list-langs 2>&1 | grep -E "^(eng|ita)$" | tr '\n' ' ')
    if [ -n "$LANGS" ]; then
        echo "   Languages: $LANGS"
    fi
else
    echo "⚠️  tesseract not found - install with: sudo apt-get install tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng"
fi

# Verifica script
echo ""
echo "📝 Checking scripts..."
SCRIPTS_DIR=".claude/skills/pdf/scripts"
for script in check_fillable_fields.py extract_form_field_info.py convert_pdf_to_images.py \
              fill_fillable_fields.py fill_pdf_form_with_annotations.py \
              create_validation_image.py check_bounding_boxes.py; do
    if [ -f "$SCRIPTS_DIR/$script" ]; then
        echo "✅ $script"
    else
        echo "❌ $script not found"
    fi
done

# Test con PDF se fornito
if [ -n "$1" ]; then
    echo ""
    echo "🧪 Testing with PDF: $1"
    if [ -f "$1" ]; then
        echo ""
        echo "Running check_fillable_fields.py..."
        python $SCRIPTS_DIR/check_fillable_fields.py "$1"
        echo ""
        echo "✅ Test completed successfully!"
    else
        echo "❌ File not found: $1"
        exit 1
    fi
else
    echo ""
    echo "ℹ️  To test with a PDF file, run:"
    echo "   bash .claude/skills/pdf/test_skill.sh path/to/test.pdf"
fi

echo ""
echo "✨ PDF Skill installation check completed!"
