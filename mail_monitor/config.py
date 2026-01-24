"""
Configurazione Mail Monitor
Carica impostazioni da variabili d'ambiente o file .env del backend
"""

import os
from pathlib import Path
from typing import List

# Prova a caricare da .env solo se esiste (non in Docker)
try:
    from dotenv import load_dotenv
    backend_env = Path(__file__).parent.parent / 'backend' / '.env'
    if backend_env.exists():
        load_dotenv(backend_env, override=True)
except ImportError:
    pass  # dotenv non disponibile, usa variabili ambiente


class Config:
    """Configurazione Mail Monitor"""

    # ========== MAIL CREDENTIALS ==========
    # Usa SMTP_USER/SMTP_PASSWORD dal backend/.env (unificato)
    MAIL_USER: str = os.getenv('SMTP_USER', '')
    MAIL_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')

    # ========== IMAP SETTINGS ==========
    IMAP_HOST: str = os.getenv('IMAP_HOST', 'imap.gmail.com')
    IMAP_PORT: int = int(os.getenv('IMAP_PORT', '993'))
    IMAP_USE_SSL: bool = os.getenv('IMAP_USE_SSL', 'true').lower() == 'true'
    MAIL_FOLDER: str = os.getenv('MAIL_FOLDER', 'INBOX')
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
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/mail_monitor.log')

    # ========== PATHS ==========
    BASE_DIR: Path = Path(__file__).parent
    TEMP_DIR: Path = BASE_DIR / 'temp'
    LOGS_DIR: Path = BASE_DIR / 'logs'
    DATA_DIR: Path = BASE_DIR / 'data'

    # Path al backend (relativo, funziona ovunque)
    BACKEND_PATH: Path = BASE_DIR.parent / 'backend' / 'app'

    @classmethod
    def validate(cls) -> List[str]:
        """
        Valida la configurazione

        Returns:
            Lista di errori (vuota se tutto OK)
        """
        errors = []

        if not cls.MAIL_USER:
            errors.append("Email non configurata (SMTP_USER in backend/.env)")

        if not cls.MAIL_PASSWORD:
            errors.append("Password non configurata (SMTP_PASSWORD in backend/.env)")

        if cls.MAIL_USER and '@' not in cls.MAIL_USER:
            errors.append("Email non valida")

        if cls.MAIL_PASSWORD and len(cls.MAIL_PASSWORD.replace(' ', '')) != 16:
            errors.append(
                "App Password deve essere 16 caratteri (senza spazi)")

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
        print("📧 Configurazione Mail Monitor")
        print("=" * 50)
        print(f"Email: {cls.MAIL_USER or '(non configurato)'}")
        print(f"Password: {'*' * 16 if cls.MAIL_PASSWORD else '(non configurata)'}")
        print(f"IMAP: {cls.IMAP_HOST}:{cls.IMAP_PORT} (SSL: {cls.IMAP_USE_SSL})")
        print(f"Cartella: {cls.MAIL_FOLDER}")
        print(f"Solo non lette: {cls.UNREAD_ONLY}")
        print(f"Keywords oggetto: {', '.join(cls.SUBJECT_KEYWORDS)}")
        print(
            f"Whitelist mittenti: {', '.join(cls.SENDER_WHITELIST) if cls.SENDER_WHITELIST else 'Nessuna (tutti)'}")
        print(f"Backend URL: {cls.BACKEND_URL}")
        print(f"Marca come letta: {cls.MARK_AS_READ}")
        print(f"Applica label: {cls.APPLY_LABEL}")
        print(f"Max email per run: {cls.MAX_EMAILS_PER_RUN}")
        print("=" * 50)


# Crea le directory all'import
Config.create_directories()


# Test configurazione
if __name__ == "__main__":
    errors = Config.validate()
    if errors:
        print("Errori configurazione:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("Configurazione valida!")
        Config.print_config()
