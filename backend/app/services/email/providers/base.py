"""
Base class per provider email - Estensibile per nuovi provider.

Per aggiungere un nuovo provider (es. Outlook, SendGrid):
1. Creare nuovo file in providers/
2. Estendere BaseEmailProvider
3. Implementare tutti i metodi astratti
4. Registrare in providers/__init__.py
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseEmailProvider(ABC):
    """
    Abstract base class per provider email.
    Definisce l'interfaccia comune per IMAP e SMTP.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza provider con configurazione.

        Args:
            config: Dict con credenziali e impostazioni
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        Valida configurazione provider-specific.
        Solleva ValueError se configurazione invalida.
        """
        pass

    # ========== IMAP (Ricezione) ==========

    @abstractmethod
    def connect_imap(self) -> Any:
        """
        Stabilisce connessione IMAP.

        Returns:
            Oggetto connessione IMAP
        """
        pass

    @abstractmethod
    def fetch_emails(self, folder: str = 'INBOX',
                     unread_only: bool = True,
                     max_emails: int = 50) -> List[Dict]:
        """
        Recupera email dalla casella.

        Args:
            folder: Cartella da leggere
            unread_only: Solo non lette
            max_emails: Numero massimo email

        Returns:
            Lista di dict con email
        """
        pass

    @abstractmethod
    def mark_as_read(self, email_uid: str) -> bool:
        """
        Marca email come letta.

        Args:
            email_uid: UID dell'email

        Returns:
            True se operazione riuscita
        """
        pass

    # ========== SMTP (Invio) ==========

    @abstractmethod
    def connect_smtp(self) -> Any:
        """
        Stabilisce connessione SMTP.

        Returns:
            Oggetto connessione SMTP
        """
        pass

    @abstractmethod
    def send_email(self, to: str, subject: str,
                   body_html: str, body_text: Optional[str] = None) -> bool:
        """
        Invia email.

        Args:
            to: Destinatario
            subject: Oggetto
            body_html: Corpo HTML
            body_text: Corpo testo (opzionale)

        Returns:
            True se invio riuscito
        """
        pass

    # ========== TEST ==========

    @abstractmethod
    def test_imap_connection(self) -> Dict[str, Any]:
        """
        Test connessione IMAP.

        Returns:
            Dict con 'success' e 'message' o 'error'
        """
        pass

    @abstractmethod
    def test_smtp_connection(self) -> Dict[str, Any]:
        """
        Test connessione SMTP.

        Returns:
            Dict con 'success' e 'message' o 'error'
        """
        pass
