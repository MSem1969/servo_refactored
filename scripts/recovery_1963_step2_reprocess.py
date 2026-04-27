"""
RECOVERY ACQUISIZIONE 1963 - STEP 2: RI-ELABORAZIONE PDF
=========================================================
Esegui in PRODUZIONE dopo aver lanciato Step 1 (cleanup SQL).

USO:
    1. Apri terminale Python nel container backend (Coolify -> Backend -> Terminal)
    2. Lancia:    python /app/scripts/recovery_1963_step2_reprocess.py
       oppure:    cd /app && python -c "exec(open('scripts/recovery_1963_step2_reprocess.py').read())"

Cosa fa:
- Legge il path del PDF dalla tabella _recovery_1963_pdf (creata da Step 1).
- Chiama process_pdf() che ri-elabora il PDF da zero col fix gia' deployato.
- Crea una NUOVA acquisizione (id auto, es. 1964) con tutti i 34 ordini estratti.
- Stampa il nuovo id_acquisizione: NOTALO, ti servira' per Step 3.

Cosa attendere:
- Status: OK
- Ordini estratti: 34
- Righe: ~783
"""
import os
import sys

# Assicura che siamo nella root del backend
if not os.path.exists('app'):
    os.chdir('/app')

from app.services.pdf_processor import process_pdf
from app.database_pg import get_db

db = get_db()

# Recupera info PDF dal backup creato in Step 1
backup = db.execute(
    "SELECT nome_file_originale, percorso_storage FROM _recovery_1963_pdf"
).fetchone()

if not backup:
    print("ERRORE: tabella _recovery_1963_pdf vuota o inesistente.")
    print("       Hai eseguito Step 1 prima di Step 2?")
    sys.exit(1)

# Risolvi path PDF (può essere assoluto in /app/uploads o relativo)
candidates = [
    backup['percorso_storage'],
    os.path.join('/app', backup['percorso_storage']),
    os.path.join('uploads', os.path.basename(backup['percorso_storage'])),
    os.path.join('/app/uploads', os.path.basename(backup['percorso_storage'])),
]
pdf_path = next((p for p in candidates if p and os.path.exists(p)), None)

if not pdf_path:
    print("ERRORE: PDF non trovato. Path provati:")
    for c in candidates:
        print(f"  - {c}")
    sys.exit(1)

print(f"PDF trovato: {pdf_path}")
print(f"Filename:    {backup['nome_file_originale']}")
print()

with open(pdf_path, 'rb') as f:
    content = f.read()

print(f"Dimensione: {len(content)} bytes")
print()
print("Invio a process_pdf()...")
print("-" * 60)

result = process_pdf(backup['nome_file_originale'], content)

print("-" * 60)
print()
print("=== RISULTATO ===")
print(f"Status:               {result.get('status')}")
print(f"id_acquisizione NEW:  {result.get('id_acquisizione')}")
print(f"Ordini estratti:      {result.get('ordini')}")
print(f"Righe totali:         {result.get('righe')}")

if result.get('anomalie'):
    print(f"Anomalie segnalate:   {len(result['anomalie'])}")

print()
if result.get('status') == 'OK' and result.get('ordini') == 34:
    print("[OK] Step 2 completato. ANNOTA il valore 'id_acquisizione NEW' qui sopra.")
    print("     Ti servira' per lo Step 3 (restore stati).")
else:
    print("[ATTENZIONE] Risultato inatteso. Verifica prima di procedere a Step 3.")
