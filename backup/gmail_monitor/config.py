"""
Configurazione Gmail Monitor
Carica impostazioni da file .env
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Carica variabili da .env del backend (condiviso)
backend_env = Path(__file__).parent.parent / 'backend' / '.env'
load_dotenv(backend_env, override=True)

# Carica anche .env locale (se esiste) per override
local_env = Path(__file__).parent / '.env'
if local_env.exists():
    load_dotenv(local_env, override=True)


class Config:
    """Configurazione Gmail Monitor"""

    # ========== GMAIL CREDENTIALS ==========
    GMAIL_EMAIL: str = os.getenv('GMAIL_EMAIL', '')
    GMAIL_APP_PASSWORD: str = os.getenv('GMAIL_APP_PASSWORD', '')

    # ========== GMAIL SETTINGS ==========
    GMAIL_LABEL: str = os.getenv('GMAIL_LABEL', 'INBOX')
    UNREAD_ONLY: bool = os.getenv('UNREAD_ONLY', 'true').lower() == 'true'

    # Filtri email
    SUBJECT_KEYWORDS: List[str] = [
        kw.strip()
        for kw in os.getenv('SUBJECT_KEYWORDS', 'Transfer Order,TO ,Ordine').split(',')
    ]

    SENDER_WHITELIST: List[str] = [
        sender.strip()
        for sender in os.getenv('SENDER_WHITELIST', '').split(',')
        if sender.strip()
    ]

    # ========== BACKEND API ==========
    BACKEND_URL: str = os.getenv('BACKEND_URL', 'http://localhost:8000')
    UPLOAD_ENDPOINT: str = '/api/v1/upload'
    UPLOAD_TIMEOUT: int = int(os.getenv('UPLOAD_TIMEOUT', '120'))

    # ========== COMPORTAMENTO ==========
    MARK_AS_READ: bool = os.getenv('MARK_AS_READ', 'true').lower() == 'true'
    APPLY_LABEL: str = os.getenv('APPLY_LABEL', 'Processed')
    DELETE_TEMP_FILES: bool = os.getenv(
        'DELETE_TEMP_FILES', 'true').lower() == 'true'

    # ========== LIMITI ==========
    MAX_EMAILS_PER_RUN: int = int(os.getenv('MAX_EMAILS_PER_RUN', '50'))
    MAX_ATTACHMENT_SIZE_MB: int = int(
        os.getenv('MAX_ATTACHMENT_SIZE_MB', '50'))
    MIN_ATTACHMENT_SIZE_KB: int = int(
        os.getenv('MIN_ATTACHMENT_SIZE_KB', '10'))

    # ========== RETRY ==========
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY_SECONDS: int = int(os.getenv('RETRY_DELAY_SECONDS', '60'))

    # ========== LOGGING ==========
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/gmail_monitor.log')

    # ========== PATHS ==========
    BASE_DIR: Path = Path(__file__).parent
    TEMP_DIR: Path = BASE_DIR / 'temp'
    LOGS_DIR: Path = BASE_DIR / 'logs'
    DATA_DIR: Path = BASE_DIR / 'data'

    # Path al database principale
    DB_PATH: Path = Path(
        '/home/jobseminara/extractor/backend/extractor_to.db')

    # Path al backend
    BACKEND_PATH: Path = Path(
        '/home/jobseminara/extractor/backend/app')

    @classmethod
    def validate(cls) -> List[str]:
        """
        Valida la configurazione

        Returns:
            Lista di errori (vuota se tutto OK)
        """
        errors = []

        if not cls.GMAIL_EMAIL:
            errors.append("GMAIL_EMAIL non configurato")

        if not cls.GMAIL_APP_PASSWORD:
            errors.append("GMAIL_APP_PASSWORD non configurato")

        if '@' not in cls.GMAIL_EMAIL:
            errors.append("GMAIL_EMAIL non valido")

        if len(cls.GMAIL_APP_PASSWORD.replace(' ', '')) != 16:
            errors.append(
                "GMAIL_APP_PASSWORD deve essere 16 caratteri (senza spazi)")

        if not cls.DB_PATH.exists():
            errors.append(f"Database non trovato: {cls.DB_PATH}")

        return errors

    @classmethod
    def create_directories(cls):
        """Crea le directory necessarie se non esistono"""
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def print_config(cls):
        """Stampa la configurazione (mascherando password)"""
        print("📧 Configurazione Gmail Monitor")
        print("=" * 50)
        print(f"Email: {cls.GMAIL_EMAIL}")
        print(f"Password: {'*' * 16} (configurata)")
        print(f"Label: {cls.GMAIL_LABEL}")
        print(f"Solo non lette: {cls.UNREAD_ONLY}")
        print(f"Keywords oggetto: {', '.join(cls.SUBJECT_KEYWORDS)}")
        print(
            f"Whitelist mittenti: {', '.join(cls.SENDER_WHITELIST) if cls.SENDER_WHITELIST else 'Nessuna (tutti)'}")
        print(f"Backend URL: {cls.BACKEND_URL}")
        print(f"Marca come letta: {cls.MARK_AS_READ}")
        print(f"Applica label: {cls.APPLY_LABEL}")
        print(f"Max email per run: {cls.MAX_EMAILS_PER_RUN}")
        print(f"Database: {cls.DB_PATH}")
        print("=" * 50)


# Crea le directory all'import
Config.create_directories()


# Test configurazione
if __name__ == "__main__":
    errors = Config.validate()
    if errors:
        print("❌ Errori configurazione:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Configurazione valida!")
        Config.print_config()
