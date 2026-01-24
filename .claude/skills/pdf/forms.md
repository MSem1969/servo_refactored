# PDF Form Filling Guide

This document outlines two workflows for completing PDF forms depending on whether they contain fillable form fields.

## Fillable Forms Workflow

For PDFs with fillable fields, the process involves:

### Step 1: Detection
Run `python scripts/check_fillable_fields.py <file.pdf>` to confirm fillable fields exist.

### Step 2: Field Extraction
Execute `python scripts/extract_form_field_info.py <input.pdf> <output.json>` to generate a JSON file documenting field properties (IDs, locations, types).

### Step 3: Conversion
Convert the PDF to PNG images using `python scripts/convert_pdf_to_images.py <input.pdf> <output_directory>`.

### Step 4: Data Mapping
Create `field_values.json` matching field IDs with their corresponding values. Example:

```json
[
  {
    "field_id": "name",
    "page": 1,
    "value": "John Doe"
  },
  {
    "field_id": "agree_checkbox",
    "page": 2,
    "value": "Yes"
  }
]
```

### Step 5: Population
Run `python scripts/fill_fillable_fields.py <input.pdf> <field_values.json> <output.pdf>` to generate the completed PDF.

Field types supported include text inputs, checkboxes, radio groups, and dropdown selections.

## Non-Fillable Forms Workflow

For PDFs lacking form fields, a four-step annotation approach applies:

### Step 1: Identify Entry Areas
Convert to images and visually identify all data entry areas, establishing distinct bounding boxes for labels and text entry zones that don't overlap.

### Step 2: Create fields.json
Create `fields.json` documenting:
- Page dimensions
- Field descriptions
- Precise bounding box coordinates for labels and entry areas

Example structure:
```json
{
  "pages": [
    {
      "page_number": 1,
      "image_width": 1000,
      "image_height": 1400
    }
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Full Name",
      "label_bounding_box": [50, 100, 200, 130],
      "entry_bounding_box": [210, 100, 500, 130],
      "entry_text": {
        "text": "John Doe",
        "font": "Arial",
        "font_size": 12,
        "font_color": "000000"
      }
    }
  ]
}
```

Then generate validation images showing red rectangles for input areas and blue rectangles for labels:
```bash
python scripts/create_validation_image.py <page_number> <fields.json> <input_image> <output_image>
```

### Step 3: Validate Bounding Boxes
Use automated checks and manual image inspection to ensure rectangles target only appropriate areas:
```bash
python scripts/check_bounding_boxes.py <fields.json>
```

This validates:
- No overlapping bounding boxes
- Entry box heights accommodate text content

### Step 4: Fill the Form
Execute `python scripts/fill_pdf_form_with_annotations.py <input.pdf> <fields.json> <output.pdf>` to add text annotations at specified locations.

## Important Notes

- Complete steps sequentially
- Validate visual accuracy before finalizing forms
- Bounding boxes use coordinates: [left, top, right, bottom]
- Colors in validation images: RED = entry area, BLUE = label area
