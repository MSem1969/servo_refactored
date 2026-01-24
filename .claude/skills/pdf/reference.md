# PDF Processing Advanced Reference

This comprehensive guide covers advanced PDF manipulation tools and techniques across Python and JavaScript environments.

## Python Libraries

### pypdfium2 (Apache/BSD License)
Provides fast PDF rendering through Chromium's PDFium.

**Key Capabilities:**
- Render page to image with adjustable scale and rotation
- Text extraction from individual pages

**Example:**
```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("example.pdf")
page = pdf[0]
bitmap = page.render(scale=2, rotation=0)
pil_image = bitmap.to_pil()
text = page.get_textpage().get_text_range()
```

### pdfplumber
Extract all text with coordinates by accessing character-level data including position values.

**Advanced Table Extraction:**
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]
    # Extract with coordinates
    chars = page.chars
    for char in chars:
        print(f"Char: {char['text']}, x0: {char['x0']}, y0: {char['y0']}")

    # Advanced table extraction
    table = page.extract_table({
        "vertical_strategy": "lines",
        "horizontal_strategy": "text"
    })
```

### reportlab (BSD License)
Create professional documents programmatically.

**Styled Tables:**
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

doc = SimpleDocTemplate("output.pdf", pagesize=letter)
data = [['Name', 'Age'], ['Alice', '30'], ['Bob', '25']]
table = Table(data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
doc.build([table])
```

### pypdf
Handle page manipulation through cropping and batch processing.

**Cropping Pages:**
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.mediabox.lower_left = (50, 50)
    page.mediabox.upper_right = (550, 750)
    writer.add_page(page)

with open("cropped.pdf", "wb") as f:
    writer.write(f)
```

## JavaScript Libraries

### pdf-lib (MIT License)
Manipulates PDFs in any JavaScript environment.

**Capabilities:**
```javascript
import { PDFDocument, rgb } from 'pdf-lib'

// Load existing PDF
const existingPdfBytes = await fetch('document.pdf').then(res => res.arrayBuffer())
const pdfDoc = await PDFDocument.load(existingPdfBytes)

// Add page
const page = pdfDoc.addPage()

// Draw text with styling
page.drawText('Hello World', {
  x: 50,
  y: 500,
  size: 30,
  color: rgb(0, 0, 1)
})

// Render rectangles
page.drawRectangle({
  x: 50,
  y: 100,
  width: 200,
  height: 100,
  borderColor: rgb(1, 0, 0),
  borderWidth: 2
})

// Save
const pdfBytes = await pdfDoc.save()
```

### pdfjs-dist (Apache License, Mozilla)
Renders PDFs in browsers.

**Features:**
```javascript
import * as pdfjsLib from 'pdfjs-dist'

// Load PDF
const loadingTask = pdfjsLib.getDocument('document.pdf')
const pdf = await loadingTask.promise

// Render to canvas
const page = await pdf.getPage(1)
const viewport = page.getViewport({ scale: 1.5 })
const canvas = document.getElementById('pdf-canvas')
const context = canvas.getContext('2d')

await page.render({ canvasContext: context, viewport }).promise

// Extract text with coordinates
const textContent = await page.getTextContent()
```

## Command-Line Tools

### poppler-utils

**Extract text with bounding box coordinates (XML format):**
```bash
pdftotext -bbox-layout document.pdf output.html
```

**Convert to images with specific resolution:**
```bash
pdftoppm -png -r 300 document.pdf output
```

**Extract embedded images:**
```bash
pdfimages -all document.pdf output
```

### qpdf (Apache License)

**Linearization and compression:**
```bash
qpdf --linearize --compress-streams=y input.pdf output.pdf
```

**Add password protection with permissions:**
```bash
qpdf --encrypt user-password owner-password 256 \
  --modify=none --extract=n --print=full \
  input.pdf output.pdf
```

**Repair corrupted PDFs:**
```bash
qpdf --check input.pdf
qpdf --replace-input input.pdf
```

## Performance Strategies

### For Large Files
- Use streaming approaches
- Process page-by-page instead of loading entire document
- Consider memory-mapped file access

### For Text Extraction
Prefer `pdftotext -bbox-layout` for speed and accuracy.

### For Images
`pdfimages` outperforms rendering-based approaches for extracting embedded images.

### For Batch Processing
```python
import os
from pypdf import PdfReader, PdfWriter

def process_pdfs(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if filename.endswith('.pdf'):
            try:
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, filename)

                reader = PdfReader(input_path)
                writer = PdfWriter()

                # Process pages
                for page in reader.pages:
                    writer.add_page(page)

                with open(output_path, 'wb') as f:
                    writer.write(f)

                print(f"Processed: {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
```
