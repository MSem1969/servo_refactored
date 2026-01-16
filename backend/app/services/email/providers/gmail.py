"""
Gmail provider - Implementazione IMAP/SMTP per Gmail.

Richiede App Password per autenticazione.
Generare da: https://myaccount.google.com/apppasswords
"""

import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

from .base import BaseEmailProvider
from ..constants import IMAP_TIMEOUT, SMTP_TIMEOUT


class GmailProvider(BaseEmailProvider):
    """Provider per Gmail (IMAP + SMTP)"""

    def _validate_config(self) -> None:
        """Valida presenza credenziali"""
        # Verifica credenziali IMAP o SMTP
        has_imap = self.config.get('imap_user') and self.config.get('imap_password')
        has_smtp = self.config.get('smtp_user') and self.config.get('smtp_password')

        if not has_imap and not has_smtp:
            raise ValueError(
                "Credenziali mancanti. Configurare IMAP_USER/IMAP_PASSWORD "
                "o SMTP_USER/SMTP_PASSWORD nel file .env"
            )

    # ========== IMAP ==========

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connessione IMAP SSL"""
        host = self.config.get('imap_host', 'imap.gmail.com')
        port = int(self.config.get('imap_port', 993))

        mail = imaplib.IMAP4_SSL(host, port)
        mail.socket().settimeout(IMAP_TIMEOUT)

        mail.login(
            self.config.get('imap_user', ''),
            self.config.get('imap_password', '')
        )
        return mail

    def fetch_emails(self, folder: str = 'INBOX',
                     unread_only: bool = True,
                     max_emails: int = 50) -> List[Dict]:
        """Recupera email dalla casella"""
        mail = self.connect_imap()
        try:
            mail.select(folder)

            criteria = 'UNSEEN' if unread_only else 'ALL'
            status, messages = mail.search(None, criteria)

            if not messages[0]:
                return []

            email_ids = messages[0].split()[-max_emails:]
            emails = []

            for eid in email_ids:
                status, msg_data = mail.fetch(eid, '(RFC822)')
                if status == 'OK' and msg_data[0]:
                    emails.append({
                        'uid': eid.decode(),
                        'raw': msg_data[0][1]
                    })

            return emails
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    def mark_as_read(self, email_uid: str) -> bool:
        """Marca email come letta"""
        mail = self.connect_imap()
        try:
            mail.select('INBOX')
            mail.store(email_uid.encode(), '+FLAGS', '\\Seen')
            return True
        except Exception:
            return False
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    # ========== SMTP ==========

    def connect_smtp(self) -> smtplib.SMTP:
        """Connessione SMTP con TLS"""
        host = self.config.get('smtp_host', 'smtp.gmail.com')
        port = int(self.config.get('smtp_port', 587))

        server = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT)

        if self.config.get('smtp_use_tls', True):
            server.starttls()

        # Usa credenziali SMTP, fallback su IMAP
        user = self.config.get('smtp_user') or self.config.get('imap_user', '')
        password = self.config.get('smtp_password') or self.config.get('imap_password', '')

        server.login(user, password)
        return server

    def send_email(self, to: str, subject: str,
                   body_html: str, body_text: Optional[str] = None) -> bool:
        """Invia email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject

        # Mittente
        sender_name = self.config.get('smtp_sender_name', 'SERV.O')
        sender_email = (self.config.get('smtp_sender_email') or
                       self.config.get('smtp_user') or
                       self.config.get('imap_user', ''))
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to

        # Corpo
        if body_text:
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        server = self.connect_smtp()
        try:
            server.send_message(msg)
            return True
        finally:
            try:
                server.quit()
            except Exception:
                pass

    # ========== TEST ==========

    def test_imap_connection(self) -> Dict[str, Any]:
        """Test connessione IMAP"""
        try:
            mail = self.connect_imap()
            mail.select('INBOX')
            status, messages = mail.search(None, 'UNSEEN')
            unread = len(messages[0].split()) if messages[0] else 0
            mail.logout()
            return {
                'success': True,
                'message': f'Connessione IMAP OK - {unread} email non lette'
            }
        except imaplib.IMAP4.error as e:
            return {'success': False, 'error': f'Errore IMAP: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_smtp_connection(self) -> Dict[str, Any]:
        """Test connessione SMTP"""
        try:
            server = self.connect_smtp()
            server.quit()
            return {'success': True, 'message': 'Connessione SMTP OK'}
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'error': 'Autenticazione fallita. Verificare credenziali e App Password.'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
