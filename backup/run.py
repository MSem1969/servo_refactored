#!/usr/bin/env python3
"""
TO_EXTRACTOR v6.2 - Launcher
Avvia Backend, Frontend e Gmail Monitor insieme.
"""
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
GMAIL_MONITOR_DIR = BASE_DIR / "gmail_monitor"
VENV_DIR = BACKEND_DIR / "venv"


def get_python():
    """Ritorna il path del Python nel virtual environment."""
    if sys.platform == "win32":
        p = VENV_DIR / "Scripts" / "python.exe"
    else:
        p = VENV_DIR / "bin" / "python"
    return str(p) if p.exists() else sys.executable


def main():
    print("\n" + "=" * 60)
    print("   🚀 TO_EXTRACTOR v6.2")
    print("=" * 60)
    print("   Backend:       http://127.0.0.1:8001")
    print("   Frontend:      http://localhost:5173")
    print("   Gmail Monitor: Attivo (sincronizzazione schedulata)")
    print("=" * 60 + "\n")

    processes = []

    try:
        # 1. Avvio Backend
        print("🔧 Avvio Backend...")
        backend = subprocess.Popen(
            [get_python(), "-m", "uvicorn", "app.main:app", "--reload",
             "--port", "8001", "--host", "127.0.0.1"],
            cwd=str(BACKEND_DIR)
        )
        processes.append(("Backend", backend))
        time.sleep(3)

        # 2. Avvio Frontend
        print("🎨 Avvio Frontend...")
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR)
        )
        processes.append(("Frontend", frontend))
        time.sleep(2)

        # 3. Avvio Gmail Monitor (scheduler)
        print("📧 Avvio Gmail Monitor...")
        gmail_monitor_script = GMAIL_MONITOR_DIR / "scheduler.py"
        if gmail_monitor_script.exists():
            gmail_monitor = subprocess.Popen(
                [get_python(), str(gmail_monitor_script)],
                cwd=str(GMAIL_MONITOR_DIR)
            )
            processes.append(("Gmail Monitor", gmail_monitor))
            print("   ✅ Gmail Monitor avviato (scheduler attivo)")
        else:
            # Fallback a gmail_monitor.py se scheduler.py non esiste
            gmail_monitor_fallback = GMAIL_MONITOR_DIR / "gmail_monitor.py"
            if gmail_monitor_fallback.exists():
                gmail_monitor = subprocess.Popen(
                    [get_python(), str(gmail_monitor_fallback)],
                    cwd=str(GMAIL_MONITOR_DIR)
                )
                processes.append(("Gmail Monitor", gmail_monitor))
                print("   ✅ Gmail Monitor avviato")
            else:
                print("   ⚠️ Gmail Monitor non trovato")

        print("\n" + "=" * 60)
        print("✅ Sistema avviato! Apri: http://localhost:5173")
        print("   Premi Ctrl+C per arrestare tutti i servizi")
        print("=" * 60 + "\n")

        # Loop principale - monitora i processi
        while True:
            time.sleep(5)
            # Verifica che i processi siano ancora attivi
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️ {name} terminato inaspettatamente (exit code: {proc.returncode})")

    except KeyboardInterrupt:
        print("\n🛑 Arresto di tutti i servizi...")
        for name, proc in processes:
            try:
                print(f"   Arresto {name}...")
                proc.terminate()
                proc.wait(timeout=5)
            except Exception as e:
                print(f"   ⚠️ Errore arresto {name}: {e}")
                try:
                    proc.kill()
                except:
                    pass
        print("✅ Tutti i servizi arrestati.")


if __name__ == "__main__":
    main()
