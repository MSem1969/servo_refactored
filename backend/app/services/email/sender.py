"""
Email sender - Servizio invio email con logging e rate limiting.
"""

from typing import Dict, Any, Optional

from .config import email_config
from .providers.gmail import GmailProvider
from .templates import render_template
from .log import log_email_sent, log_email_failed


class EmailSender:
    """
    Servizio invio email con logging automatico.

    Uso:
        sender = EmailSender(db)
        result = sender.send(to, subject, body_html)
        # oppure
        result = sender.send_from_template('ticket_creato', context, ticket_id)
    """

    def __init__(self, db):
        """
        Inizializza sender.

        Args:
            db: Connessione database per config e logging
        """
        self.db = db
        self._provider = None

    @property
    def provider(self):
        """Lazy load provider con config da DB"""
        if self._provider is None:
            config = email_config.get_full_config(self.db, 'smtp')

            # Merge con config IMAP per credenziali condivise
            imap_config = email_config.get_full_config(self.db, 'imap')
            if not config.get('smtp_user') and imap_config.get('imap_user'):
                config['smtp_user'] = imap_config['imap_user']
                config['smtp_password'] = imap_config['imap_password']

            # Per ora solo Gmail, estendibile con factory
            self._provider = GmailProvider(config)

        return self._provider

    def send(self, to: str, subject: str, body_html: str,
             ticket_id: Optional[int] = None,
             email_type: str = 'generic',
             attachments=None) -> Dict[str, Any]:
        """
        Invia email con logging automatico.

        Args:
            to: Destinatario
            subject: Oggetto
            body_html: Corpo HTML
            ticket_id: ID ticket correlato (opzionale)
            email_type: Tipo per logging
            attachments: Lista allegati [{'filename', 'content', 'mime_type'}]

        Returns:
            Dict con 'success', 'log_id', ed eventuale 'error'
        """
        try:
            success = self.provider.send_email(to, subject, body_html, attachments=attachments)

            if success:
                log_id = log_email_sent(
                    self.db,
                    destinatario=to,
                    oggetto=subject,
                    tipo=email_type,
                    ticket_id=ticket_id
                )
                return {'success': True, 'log_id': log_id}
            else:
                log_id = log_email_failed(
                    self.db,
                    destinatario=to,
                    oggetto=subject,
                    tipo=email_type,
                    ticket_id=ticket_id,
                    errore='Invio fallito senza errore specifico'
                )
                return {'success': False, 'log_id': log_id, 'error': 'Invio fallito'}

        except Exception as e:
            log_id = log_email_failed(
                self.db,
                destinatario=to,
                oggetto=subject,
                tipo=email_type,
                ticket_id=ticket_id,
                errore=str(e)
            )
            return {'success': False, 'log_id': log_id, 'error': str(e)}

    def send_from_template(self, template_name: str,
                          context: Dict[str, Any],
                          to: str,
                          ticket_id: Optional[int] = None,
                          attachments=None) -> Dict[str, Any]:
        """
        Invia email usando template predefinito.

        Args:
            template_name: Nome template (da templates.py)
            context: Dict con valori per placeholder
            to: Destinatario
            ticket_id: ID ticket correlato
            attachments: Lista allegati [{'filename', 'content', 'mime_type'}]

        Returns:
            Dict con 'success', 'log_id', ed eventuale 'error'
        """
        try:
            subject, body = render_template(template_name, context)
            return self.send(to, subject, body, ticket_id, template_name, attachments=attachments)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

    def send_test_email(self, to: str) -> Dict[str, Any]:
        """
        Invia email di test.

        Args:
            to: Destinatario

        Returns:
            Dict con risultato
        """
        return self.send_from_template('test', {}, to)

    @staticmethod
    def is_configured(db) -> bool:
        """
        Verifica se il sender e configurato.

        Args:
            db: Connessione database

        Returns:
            True se SMTP configurato
        """
        settings = email_config.get_settings(db, 'smtp')
        credentials = email_config.credentials_configured('smtp')

        # Fallback su credenziali IMAP
        if not credentials:
            credentials = email_config.credentials_configured('imap')

        return settings.get('smtp_enabled', False) and credentials
