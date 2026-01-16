"""
Gestione configurazione email con priorità:
1. Variabili .env (credenziali sensibili)
2. Database email_config (impostazioni modificabili)
3. Default da constants.py
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

# Carica .env dalla root del progetto
_env_loaded = False


def _ensure_env_loaded():
    """Carica variabili da .env se non già fatto"""
    global _env_loaded
    if _env_loaded:
        return

    try:
        from dotenv import load_dotenv
        # Cerca .env nella root del progetto
        env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        _env_loaded = True
    except ImportError:
        # dotenv non installato, usa solo variabili ambiente
        _env_loaded = True


class EmailConfigService:
    """
    Singleton per gestione configurazione email.
    Legge credenziali da .env, impostazioni da database.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ========== CREDENZIALI (.env) ==========

    @staticmethod
    def get_credentials(protocol: str) -> Dict[str, str]:
        """
        Recupera credenziali da .env

        Args:
            protocol: 'imap' o 'smtp'

        Returns:
            Dict con 'user' e 'password'
        """
        _ensure_env_loaded()
        prefix = protocol.upper()
        return {
            'user': os.getenv(f'{prefix}_USER', ''),
            'password': os.getenv(f'{prefix}_PASSWORD', '')
        }

    @staticmethod
    def credentials_configured(protocol: str) -> bool:
        """Verifica se le credenziali sono configurate in .env"""
        creds = EmailConfigService.get_credentials(protocol)
        return bool(creds['user'] and creds['password'])

    # ========== SETTINGS (Database) ==========

    @staticmethod
    def get_settings(db, section: str = 'all') -> Dict[str, Any]:
        """
        Recupera impostazioni da database.

        Args:
            db: Connessione database
            section: 'imap', 'smtp', 'all'

        Returns:
            Dict con configurazione
        """
        try:
            query = "SELECT * FROM email_config WHERE id_config = 1"
            row = db.execute(query).fetchone()

            if not row:
                from .constants import PROVIDERS
                return PROVIDERS.get('gmail', {})

            config = dict(row)

            if section == 'all':
                return config

            # Filtra per sezione
            prefix = f'{section}_'
            return {k: v for k, v in config.items() if k.startswith(prefix)}
        except Exception:
            # Tabella non esiste ancora, ritorna default
            from .constants import PROVIDERS
            return PROVIDERS.get('gmail', {})

    @staticmethod
    def update_settings(db, data: Dict[str, Any], updated_by: int) -> bool:
        """
        Aggiorna impostazioni nel database.
        NON salva password - quelle vanno in .env!

        Args:
            db: Connessione database
            data: Dict con impostazioni da aggiornare
            updated_by: ID operatore

        Returns:
            True se aggiornamento riuscito
        """
        # Rimuovi eventuali campi password (sicurezza)
        safe_data = {k: v for k, v in data.items()
                     if 'password' not in k.lower()}

        if not safe_data:
            return True

        fields = [f"{k} = %s" for k in safe_data.keys()]
        fields.append("updated_at = CURRENT_TIMESTAMP")
        fields.append("updated_by = %s")

        values = list(safe_data.values()) + [updated_by]

        query = f"UPDATE email_config SET {', '.join(fields)} WHERE id_config = 1"
        db.execute(query, values)
        db.commit()
        return True

    # ========== CONFIG COMPLETA ==========

    @classmethod
    def get_full_config(cls, db, protocol: str) -> Dict[str, Any]:
        """
        Merge credenziali .env + settings DB.

        Args:
            db: Connessione database
            protocol: 'imap' o 'smtp'

        Returns:
            Dict con configurazione completa
        """
        credentials = cls.get_credentials(protocol)
        settings = cls.get_settings(db, protocol)

        return {
            **settings,
            f'{protocol}_user': credentials['user'],
            f'{protocol}_password': credentials['password']
        }

    @classmethod
    def get_status(cls, db) -> Dict[str, Any]:
        """
        Ritorna stato configurazione per UI.
        NON include password, solo flag se configurate.
        """
        settings = cls.get_settings(db, 'all')

        return {
            'imap_credentials_configured': cls.credentials_configured('imap'),
            'smtp_credentials_configured': cls.credentials_configured('smtp'),
            'imap_enabled': settings.get('imap_enabled', False),
            'smtp_enabled': settings.get('smtp_enabled', False),
            'imap_host': settings.get('imap_host', 'imap.gmail.com'),
            'imap_port': settings.get('imap_port', 993),
            'smtp_host': settings.get('smtp_host', 'smtp.gmail.com'),
            'smtp_port': settings.get('smtp_port', 587),
            **{k: v for k, v in settings.items()
               if 'password' not in k.lower() and 'user' not in k.lower()}
        }


# Singleton export
email_config = EmailConfigService()
