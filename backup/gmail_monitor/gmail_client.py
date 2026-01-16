import imaplib
import email
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import imapclient
import pyzmail
from config import Config

logger = logging.getLogger(__name__)


class GmailClient:
    def __init__(self):
        self.email_address = Config.GMAIL_EMAIL
        self.app_password = Config.GMAIL_APP_PASSWORD
        self.client = None

    def connetti(self):
        try:
            logger.info(f"Connessione Gmail: {self.email_address}")
            self.client = imapclient.IMAPClient(
                'imap.gmail.com', port=993, ssl=True)
            self.client.login(self.email_address, self.app_password)
            logger.info("Connessione Gmail OK")
            return True
        except Exception as e:
            logger.error(f"Errore connessione: {e}")
            return False

    def disconnetti(self):
        if self.client:
            try:
                self.client.logout()
            except:
                pass

    def seleziona_cartella(self, folder=None):
        folder = folder or Config.GMAIL_LABEL
        try:
            self.client.select_folder(folder)
            logger.info(f"Cartella selezionata: {folder}")
            return True
        except Exception as e:
            logger.error(f"Errore selezione cartella: {e}")
            return False

    def cerca_email_con_pdf(self):
        if not self.client:
            return []
        try:
            criteria = ['UNSEEN'] if Config.UNREAD_ONLY else ['ALL']
            uids = self.client.search(criteria)
            logger.info(f"Trovate {len(uids)} email")

            # INVERTI ORDINE: prendi le piu RECENTI (UID alti)
            uids_sorted = sorted(uids, reverse=True)

            return uids_sorted[:Config.MAX_EMAILS_PER_RUN]
        except Exception as e:
            logger.error(f"Errore ricerca: {e}")
            return []

    def scarica_email(self, uid):
        """
        Scarica email e estrae PDF ricorsivamente da:
        1. Allegati PDF diretti
        2. Email inoltrate/annidate (.eml) a qualsiasi profondita
        """
        try:
            messages = self.client.fetch([uid], ['RFC822'])
            if uid not in messages:
                return None

            raw_email = messages[uid][b'RFC822']
            msg = pyzmail.PyzMessage.factory(raw_email)

            email_data = {
                'uid': uid,
                'message_id': msg.get_decoded_header('message-id', ''),
                'subject': msg.get_decoded_header('subject', ''),
                'sender_email': self._extract_email(msg.get_address('from')),
                'sender_name': self._extract_name(msg.get_address('from')),
                'received_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'attachments': []
            }

            # Estrai PDF ricorsivamente
            self._extract_pdfs_recursive(
                msg, email_data['attachments'], depth=0)

            return email_data  # Ritorna sempre, anche senza PDF
        except Exception as e:
            logger.error(f"Errore download email {uid}: {e}")
            return None

    def _extract_pdfs_recursive(self, msg, attachments_list, depth=0, max_depth=3):
        """
        Estrae PDF ricorsivamente da email annidate.
        depth: livello corrente di nesting
        max_depth: massima profondita per evitare loop infiniti (ridotto da 10 a 3)
        """
        if depth > max_depth:
            logger.warning(
                f"Raggiunta profondita massima {max_depth}, stop ricorsione")
            return

        try:
            for part in msg.mailparts:
                filename = part.filename
                if not filename:
                    continue

                filename_lower = filename.lower()

                # Caso 1: PDF diretto
                if filename_lower.endswith('.pdf'):
                    content = part.get_payload()
                    if content and len(content) > 0:
                        pdf_hash = hashlib.sha256(content).hexdigest()

                        # Evita duplicati
                        if not any(att['hash'] == pdf_hash for att in attachments_list):
                            attachments_list.append({
                                'filename': filename,
                                'content': content,
                                'size': len(content),
                                'hash': pdf_hash
                            })
                            logger.info(
                                f"PDF trovato (depth {depth}): {filename}")

                # Caso 2: Email annidata (.eml) - PARSING RICORSIVO
                elif filename_lower.endswith('.eml') or part.type == 'message/rfc822':
                    content = part.get_payload()
                    if content:
                        logger.info(
                            f"Email annidata (depth {depth}): {filename}, parsing...")
                        try:
                            inner_msg = pyzmail.PyzMessage.factory(content)
                            # RICORSIONE!
                            self._extract_pdfs_recursive(
                                inner_msg, attachments_list, depth + 1, max_depth)
                        except Exception as e:
                            logger.warning(
                                f"Errore parsing email depth {depth}: {e}")
        except Exception as e:
            logger.error(f"Errore estrazione PDF depth {depth}: {e}")

    def salva_allegato(self, attachment, temp_dir):
        try:
            filename = f"{attachment['hash'][:8]}_{attachment['filename']}"
            filepath = temp_dir / filename
            with open(filepath, 'wb') as f:
                f.write(attachment['content'])
            logger.info(f"PDF salvato: {filepath.name}")
            return filepath
        except Exception as e:
            logger.error(f"Errore salvataggio: {e}")
            return None

    def marca_come_letta(self, uid):
        if not Config.MARK_AS_READ or not self.client:
            return False
        try:
            self.client.add_flags([uid], [imapclient.SEEN])
            return True
        except:
            return False

    def _extract_email(self, address_tuple):
        if address_tuple and len(address_tuple) > 1:
            return address_tuple[1] or ''
        return ''

    def _extract_name(self, address_tuple):
        if address_tuple and len(address_tuple) > 0:
            return address_tuple[0] or ''
        return ''


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    print("Test GmailClient...")
    client = GmailClient()
    if client.connetti():
        print("OK connessione")
        client.disconnetti()
        sys.exit(0)
    else:
        print("ERRORE")
        sys.exit(1)
