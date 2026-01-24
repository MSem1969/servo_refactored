#!/usr/bin/env python3
"""
SERV.O v10.4 - Launcher
Avvia Backend e Frontend insieme.
Compatibile con: Linux, macOS, Windows, GitHub Codespaces
"""
import os
import subprocess
import sys
import time
import shutil
from pathlib import Path

# =============================================================================
# CONFIGURAZIONE
# =============================================================================

BASE_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
VENV_DIR = BACKEND_DIR / "venv"

# Porte
BACKEND_PORT = 8000
FRONTEND_PORT = 5174

# Detect ambiente
IS_CODESPACES = os.getenv("CODESPACES") == "true"
CODESPACE_NAME = os.getenv("CODESPACE_NAME", "")
GITHUB_DOMAIN = os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_python():
    """Ritorna il path del Python nel virtual environment."""
    if sys.platform == "win32":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"
    return str(venv_python) if venv_python.exists() else sys.executable


def get_host():
    """Ritorna l'host su cui fare binding."""
    # Codespaces richiede 0.0.0.0 per il port forwarding
    return "0.0.0.0" if IS_CODESPACES else "127.0.0.1"


def get_frontend_url():
    """Ritorna l'URL del frontend."""
    if IS_CODESPACES:
        return f"https://{CODESPACE_NAME}-{FRONTEND_PORT}.{GITHUB_DOMAIN}"
    return f"http://localhost:{FRONTEND_PORT}"


def get_backend_url():
    """Ritorna l'URL del backend."""
    if IS_CODESPACES:
        return f"https://{CODESPACE_NAME}-{BACKEND_PORT}.{GITHUB_DOMAIN}"
    return f"http://localhost:{BACKEND_PORT}"


def check_dependencies():
    """Verifica che le dipendenze siano installate."""
    errors = []

    # Check Python venv
    python_path = get_python()
    if not Path(python_path).exists() and python_path != sys.executable:
        errors.append(f"Virtual environment non trovato: {VENV_DIR}")
        errors.append("  Esegui: cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt")

    # Check npm
    if not shutil.which("npm"):
        errors.append("npm non trovato. Installa Node.js: https://nodejs.org/")

    # Check node_modules
    if not (FRONTEND_DIR / "node_modules").exists():
        errors.append(f"node_modules non trovato in {FRONTEND_DIR}")
        errors.append("  Esegui: cd frontend && npm install")

    # Check backend .env
    if not (BACKEND_DIR / ".env").exists():
        errors.append(f"File .env non trovato in {BACKEND_DIR}")
        errors.append("  Copia .env.example in .env e configura le credenziali")

    return errors


def print_banner():
    """Stampa il banner iniziale."""
    env_label = "CODESPACES" if IS_CODESPACES else "LOCAL"

    print("\n" + "=" * 65)
    print(f"   SERV.O v10.4 - Pharmaceutical Order Extractor [{env_label}]")
    print("=" * 65)
    print(f"   Backend API:  {get_backend_url()}")
    print(f"   Frontend UI:  {get_frontend_url()}")
    print(f"   API Docs:     {get_backend_url()}/docs")
    print("=" * 65)

    if IS_CODESPACES:
        print("   NOTE: Le porte verranno inoltrate automaticamente da Codespaces")
        print("         Clicca sui link 'PORTS' nel pannello inferiore per aprire")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Check dipendenze
    errors = check_dependencies()
    if errors:
        print("\n❌ ERRORI DI CONFIGURAZIONE:\n")
        for err in errors:
            print(f"   {err}")
        print()
        sys.exit(1)

    print_banner()

    processes = []
    host = get_host()

    try:
        # 1. Avvio Backend (FastAPI + Uvicorn)
        print("🔧 Avvio Backend FastAPI...")
        backend_cmd = [
            get_python(), "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--port", str(BACKEND_PORT),
            "--host", host
        ]
        backend = subprocess.Popen(
            backend_cmd,
            cwd=str(BACKEND_DIR),
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        processes.append(("Backend", backend))
        print(f"   ✅ Backend avviato su {host}:{BACKEND_PORT}")
        time.sleep(3)  # Attendi inizializzazione

        # 2. Avvio Frontend (Vite)
        print("🎨 Avvio Frontend Vite...")
        frontend_cmd = ["npm", "run", "dev"]
        if IS_CODESPACES:
            # In Codespaces, passa l'host del backend per il proxy
            frontend_env = {
                **os.environ,
                "VITE_API_HOST": host,
                "VITE_API_PORT": str(BACKEND_PORT)
            }
        else:
            frontend_env = os.environ.copy()

        frontend = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_DIR),
            env=frontend_env
        )
        processes.append(("Frontend", frontend))
        print(f"   ✅ Frontend avviato su porta {FRONTEND_PORT}")
        time.sleep(2)

        # Messaggio finale
        print("\n" + "=" * 65)
        print(f"✅ Sistema avviato!")
        print(f"   Apri: {get_frontend_url()}")
        print("   Premi Ctrl+C per arrestare tutti i servizi")
        print("=" * 65 + "\n")

        # Loop principale - monitora processi
        while True:
            time.sleep(5)
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️  {name} terminato (exit code: {proc.returncode})")

    except KeyboardInterrupt:
        print("\n\n🛑 Arresto servizi...")
        for name, proc in processes:
            try:
                print(f"   Arresto {name}...")
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                print(f"   ⚠️  Errore arresto {name}: {e}")
        print("✅ Tutti i servizi arrestati.\n")


if __name__ == "__main__":
    main()
