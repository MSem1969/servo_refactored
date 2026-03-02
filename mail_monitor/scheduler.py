#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

INTERVAL_MINUTES = int(os.getenv('MAIL_CHECK_INTERVAL', '60'))
PAUSE_START_HOUR = int(os.getenv('MAIL_PAUSE_START', '18'))
PAUSE_END_HOUR = int(os.getenv('MAIL_PAUSE_END', '7'))

# Path assoluti per evitare problemi di cwd
SCRIPT_DIR = Path(__file__).parent.resolve()
MAIL_MONITOR_SCRIPT = SCRIPT_DIR / 'mail_monitor.py'
VENV_PYTHON = SCRIPT_DIR.parent / 'backend' / 'venv' / 'bin' / 'python'

# In Docker usa sys.executable, in locale cerca il venv del backend
PYTHON_PATH = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

print("Mail Monitor Scheduler - Avviato", flush=True)
print(f"Controllo ogni {INTERVAL_MINUTES} minuti", flush=True)
print(f"Pausa notturna: {PAUSE_START_HOUR}:00 - {PAUSE_END_HOUR}:30", flush=True)
print(f"Python: {PYTHON_PATH}", flush=True)

while True:
    now = datetime.now()
    hour = now.hour

    if hour >= PAUSE_START_HOUR or hour < PAUSE_END_HOUR:
        print(f"{now.strftime('%H:%M')} - Pausa notturna", flush=True)
        time.sleep(600)
        continue

    print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} - Controllo Mail...", flush=True)
    try:
        subprocess.run([PYTHON_PATH, str(MAIL_MONITOR_SCRIPT)], check=True)
        print("OK", flush=True)
    except Exception as e:
        print(f"Errore: {e}", flush=True)

    print(f"Prossimo controllo tra {INTERVAL_MINUTES} minuti\n", flush=True)
    time.sleep(INTERVAL_MINUTES * 60)
