# ✅ PDF Skill - Installazione Completata

## Riepilogo Installazione

La skill PDF ufficiale di Anthropic è stata replicata con successo nel progetto SERV.O.

### 📁 Struttura Creata

```
.claude/skills/pdf/
├── SKILL.md                              # Documentazione principale
├── forms.md                              # Guida compilazione form PDF
├── reference.md                          # Riferimento avanzato librerie
├── README.md                             # Istruzioni utilizzo
├── LICENSE.txt                           # Licenza Anthropic
├── skill.json                            # Metadata skill
├── test_skill.sh                         # Script test installazione
└── scripts/                              # 7 script Python utility
    ├── check_fillable_fields.py
    ├── extract_form_field_info.py
    ├── convert_pdf_to_images.py
    ├── fill_fillable_fields.py
    ├── fill_pdf_form_with_annotations.py
    ├── create_validation_image.py
    └── check_bounding_boxes.py
```

### ✅ Pacchetti Python Installati (nel venv backend)

- ✅ `pypdf` (v6.6.0) - Operazioni base PDF
- ✅ `pdfplumber` (v0.10.3) - Estrazione testo/tabelle con coordinate
- ✅ `reportlab` (v4.4.9) - Creazione PDF programmatica
- ✅ `pdf2image` (v1.17.0) - Conversione PDF → PNG
- ✅ `pillow` - Manipolazione immagini
- ✅ `pytesseract` (v0.3.13) - Wrapper Python per Tesseract OCR

### ✅ Dipendenze Sistema Installate

Tutte le dipendenze sistema sono state installate con successo:

- ✅ `poppler-utils` (v22.12.0) → `pdftotext`, `pdftoppm`, `pdfimages` (estrazione veloce)
- ✅ `qpdf` (v11.3.0) → merge/split, cifratura, riparazione PDF
- ✅ `tesseract-ocr` (v5.3.0) → OCR su PDF scansionati
- ✅ `tesseract-ocr-ita` → Lingua italiana
- ✅ `tesseract-ocr-eng` → Lingua inglese

## 🧪 Test Eseguito con Successo

```bash
$ bash .claude/skills/pdf/test_skill.sh "backend/uploads/T.O. ACRAF - GALERMO SAS.pdf"

✅ Virtual environment activated
✅ pypdf installed: 6.6.0
✅ pdfplumber installed: 0.10.3
✅ reportlab installed: 4.4.9
✅ pdf2image installed
✅ pillow installed
✅ All scripts present
✅ Test completed successfully!
```

Il PDF di test ACRAF (vendor DOC_GENERICI) è stato analizzato correttamente:
- **Risultato**: "This PDF does not have fillable form fields"
- **Implicazione**: Per compilare questo tipo di PDF, usare il workflow con annotazioni

## 📖 Come Usare la Skill

### Metodo 1: Script Python Diretti

```bash
# Attiva sempre il venv prima
source backend/venv/bin/activate

# Verifica se PDF ha campi compilabili
python .claude/skills/pdf/scripts/check_fillable_fields.py input.pdf

# Estrai metadati campi form
python .claude/skills/pdf/scripts/extract_form_field_info.py input.pdf output.json

# Converti PDF in immagini
python .claude/skills/pdf/scripts/convert_pdf_to_images.py input.pdf output_dir/

# Compila form PDF
python .claude/skills/pdf/scripts/fill_fillable_fields.py input.pdf values.json output.pdf
```

### Metodo 2: Richiedere a Claude Code

Quando lavori con Claude Code, puoi chiedere:

```
"Use the PDF skill to extract form fields from backend/uploads/ordine_123.pdf"

"Convert the PDF at data/tracciato.pdf to images for visual analysis"

"Check if the uploaded PDF has fillable form fields"
```

Claude Code caricherà automaticamente la skill dalla directory `.claude/skills/pdf/`.

## 🎯 Integrazione con SERV.O

### Possibili Applicazioni Immediate

1. **Analisi Layout PDF Vendor**
   ```python
   # Estrarre coordinate esatte di testo/tabelle
   import pdfplumber
   with pdfplumber.open("vendor_pdf.pdf") as pdf:
       chars = pdf.pages[0].chars
       for char in chars:
           print(f"{char['text']} at ({char['x0']}, {char['y0']})")
   ```

2. **Generazione Tracciati PDF**
   ```python
   # Creare tracciati TO_T/TO_D in formato PDF
   from reportlab.lib.pagesizes import A4
   from reportlab.pdfgen import canvas

   c = canvas.Canvas("tracciato_TO_T.pdf", pagesize=A4)
   c.drawString(100, 750, "HAL_FARVI")
   c.drawString(200, 750, "271717338")
   c.save()
   ```

3. **Estrazione Testo Avanzata**
   ```python
   # Per debugging nuovi vendor
   from pypdf import PdfReader
   reader = PdfReader("unknown_vendor.pdf")
   for page in reader.pages:
       print(page.extract_text())
   ```

4. **Preview Upload**
   ```python
   # Generare thumbnails per UI
   from pdf2image import convert_from_path
   images = convert_from_path("ordine.pdf", dpi=100)
   images[0].save("preview.png")
   ```

## 📚 Documentazione Disponibile

| File | Contenuto |
|------|-----------|
| `SKILL.md` | Overview generale e librerie core |
| `forms.md` | Workflow compilazione form (fillable/non-fillable) |
| `reference.md` | Riferimento Python/JS librerie avanzate |
| `README.md` | Istruzioni installazione e uso script |
| `DOCS/PDF_SKILL_SETUP.md` | Guida completa con esempi SERV.O |

## 🚀 Quick Start

### Test rapido della skill

```bash
# 1. Verifica installazione
bash .claude/skills/pdf/test_skill.sh

# 2. Test con PDF di esempio
bash .claude/skills/pdf/test_skill.sh "backend/uploads/YOUR_PDF.pdf"

# 3. Prova estrazione testo
source backend/venv/bin/activate
python -c "
from pypdf import PdfReader
reader = PdfReader('backend/uploads/YOUR_PDF.pdf')
print(reader.pages[0].extract_text()[:200])
"
```

### Verifica skill riconosciuta da Claude Code

```bash
# Lista skill installate
ls -la .claude/skills/

# Output atteso:
# drwxr-xr-x pdf/
```

## 🔗 Risorse Ufficiali

- **Skill originale**: [anthropics/skills/pdf](https://github.com/anthropics/skills/tree/main/skills/pdf)
- **pypdf docs**: https://pypdf.readthedocs.io/
- **pdfplumber**: https://github.com/jsvine/pdfplumber
- **reportlab**: https://www.reportlab.com/docs/

## 📝 Prossimi Passi Consigliati

1. **Installa tool di sistema** (opzionale ma utile):
   ```bash
   sudo apt-get install poppler-utils qpdf tesseract-ocr
   ```

2. **Esplora esempi** in `forms.md` e `reference.md`

3. **Integra in workflow SERV.O**:
   - Aggiungi validazione PDF upload
   - Genera preview thumbnails
   - Estrai metadati vendor per debugging

4. **Testa altri script**:
   ```bash
   # Converti ordine in immagini
   python scripts/convert_pdf_to_images.py backend/uploads/ordine.pdf output/
   ```

## ✨ Completato!

La skill PDF è ora completamente operativa e pronta all'uso nel progetto SERV.O.

**Ultima verifica**: 2026-01-24 16:15 UTC
**Versione skill**: 1.0.0 (replica ufficiale Anthropic)
**Ambiente**: Python 3.11.2 + venv backend
