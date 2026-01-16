#!/usr/bin/env python3
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

INTERVAL_MINUTES = 60
PAUSE_START_HOUR = 18
PAUSE_END_HOUR = 7

# Path assoluti per evitare problemi di cwd
SCRIPT_DIR = Path(__file__).parent.resolve()
MAIL_MONITOR_SCRIPT = SCRIPT_DIR / 'mail_monitor.py'
VENV_PYTHON = SCRIPT_DIR.parent / 'backend' / 'venv' / 'bin' / 'python'

# Usa il python del venv se esiste, altrimenti quello corrente
PYTHON_PATH = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

print("Mail Monitor Scheduler - Avviato")
print(f"Controllo ogni {INTERVAL_MINUTES} minuti")
print(f"Pausa notturna: {PAUSE_START_HOUR}:00 - {PAUSE_END_HOUR}:30")
print(f"Python: {PYTHON_PATH}")

while True:
    now = datetime.now()
    hour = now.hour

    if hour >= PAUSE_START_HOUR or hour < PAUSE_END_HOUR:
        print(f"{now.strftime('%H:%M')} - Pausa notturna")
        time.sleep(600)
        continue

    print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} - Controllo Mail...")
    try:
        subprocess.run([PYTHON_PATH, str(MAIL_MONITOR_SCRIPT)], check=True)
        print("OK")
    except Exception as e:
        print(f"Errore: {e}")

    print(f"Prossimo controllo tra {INTERVAL_MINUTES} minuti\n")
    time.sleep(INTERVAL_MINUTES * 60)
