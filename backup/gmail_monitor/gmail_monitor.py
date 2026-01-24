#!/usr/bin/env python3
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from config import Config
from email_db import EmailDB
from gmail_client import GmailClient
from uploader import PDFUploader
from dotenv import load_dotenv
from pathlib import Path

# Cerca .env nella root del progetto
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Assicura che logs directory esista
Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / 'gmail_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# CACHE IN MEMORIA - Velocizza skip email già esaminate
# ============================================================
_email_cache = set()  # UID delle email già esaminate in questa sessione
_email_no_pdf_cache = set()  # UID delle email senza PDF validi
_cache_max_size = 5000  # Limite dimensione cache


def should_skip_email(uid: int, message_id: str = None) -> tuple:
    """
    Verifica veloce se saltare l'email.
    Ritorna: (skip: bool, motivo: str)
    """
    # 1. Già esaminata in questa sessione senza PDF?
    if uid in _email_no_pdf_cache:
        return True, "no_pdf_cache"

    # 2. Già processata con successo in questa sessione?
    if uid in _email_cache:
        return True, "session_cache"

    # 3. Già nel database? (controllo solo se abbiamo message_id)
    if message_id and EmailDB.email_gia_processata(message_id):
        _email_cache.add(uid)
        return True, "database"

    return False, None


def mark_as_examined(uid: int, has_valid_pdf: bool = False):
    """Marca email come esaminata."""
    # Reset cache se troppo grande
    if len(_email_cache) + len(_email_no_pdf_cache) > _cache_max_size:
        _email_cache.clear()
        _email_no_pdf_cache.clear()
        logger.info("Cache resettata (limite raggiunto)")

    if has_valid_pdf:
        _email_cache.add(uid)
    else:
        _email_no_pdf_cache.add(uid)


def main():
    logger.info("=" * 60)
    logger.info("GMAIL MONITOR - Avvio")
    logger.info("=" * 60)

    # Validazione configurazione
    errors = Config.validate()
    if errors:
        logger.error("Errori configurazione:")
        for err in errors:
            logger.error(f"  - {err}")
        return 1

    # Statistiche iniziali
    stats_inizio = EmailDB.get_statistiche()
    logger.info(f"Email in database: {stats_inizio.get('TOTALE', 0)}")

    # Verifica backend
    uploader = PDFUploader()
    if not uploader.verifica_backend():
        logger.warning("Backend non disponibile - continuo comunque")

    # Connessione Gmail
    gmail = GmailClient()
    if not gmail.connetti():
        logger.error("Impossibile connettersi a Gmail")
        return 1

    try:
        if not gmail.seleziona_cartella():
            logger.error("Impossibile selezionare cartella")
            return 1

        # Cerca email
        uids = gmail.cerca_email_con_pdf()
        logger.info(f"Email da processare: {len(uids)}")

        processate = 0
        errori = 0

        for uid in uids:
            try:
                # Skip veloce da cache (senza accesso a Gmail)
                skip, motivo = should_skip_email(uid)
                if skip and motivo == "no_pdf_cache":
                    continue  # Skip silenzioso, già sappiamo che non ha PDF

                logger.info(f"Processo email UID {uid}...")

                # Scarica email
                email_data = gmail.scarica_email(uid)
                if not email_data:
                    logger.warning(f"Email {uid} senza allegati PDF validi")
                    mark_as_examined(uid, has_valid_pdf=False)
                    continue

                # Verifica database con cache
                skip, motivo = should_skip_email(uid, email_data['message_id'])
                if skip:
                    logger.debug(f"Email {uid} già processata ({motivo}), skip")
                    gmail.marca_come_letta(uid)
                    continue

                # Se ha email_data ma nessun attachment PDF valido
                if not email_data.get('attachments'):
                    logger.warning(f"Email {uid} senza allegati PDF validi")
                    mark_as_examined(uid, has_valid_pdf=False)
                    # Salva nel DB per non riscaricarla
                    EmailDB.inserisci_email({
                        'message_id': email_data.get('message_id', ''),
                        'gmail_id': str(uid),
                        'subject': email_data.get('subject', '')[:200],
                        'sender_email': email_data.get('sender_email', ''),
                        'sender_name': email_data.get('sender_name', ''),
                        'received_date': email_data.get('received_date', ''),
                        'attachment_filename': 'NO_PDF',
                        'attachment_size': 0,
                        'attachment_hash': f'NO_PDF_{uid}',
                        'stato': 'SCARTATO'
                    })
                    gmail.marca_come_letta(uid)
                    continue

                # Processa allegati
                for attachment in email_data['attachments']:
                    try:
                        # Verifica hash duplicato
                        if EmailDB.hash_gia_processato(attachment['hash']):
                            logger.info(
                                f"PDF {attachment['filename']} gia presente - skip")
                            continue

                        # Salva temporaneamente
                        pdf_path = gmail.salva_allegato(
                            attachment, Config.TEMP_DIR)
                        if not pdf_path:
                            continue

                        # Registra in database
                        email_record = {
                            'message_id': email_data['message_id'],
                            'subject': email_data['subject'],
                            'sender_email': email_data['sender_email'],
                            'sender_name': email_data['sender_name'],
                            'received_date': email_data['received_date'],
                            'attachment_filename': attachment['filename'],
                            'attachment_size': attachment['size'],
                            'attachment_hash': attachment['hash']
                        }
                        EmailDB.inserisci_email(email_record)

                        # Upload a backend
                        result = uploader.upload_pdf(pdf_path)

                        if result and result.get('success'):
                            id_acq = result['data'].get('id_acquisizione')
                            EmailDB.aggiorna_processata(
                                email_data['message_id'],
                                id_acq,
                                Config.APPLY_LABEL
                            )
                            logger.info(f"OK - ID acquisizione: {id_acq}")
                            processate += 1
                            mark_as_examined(uid, has_valid_pdf=True)
                        else:
                            EmailDB.aggiorna_errore(
                                email_data['message_id'],
                                "Errore upload backend"
                            )
                            errori += 1

                        # Cleanup
                        if Config.DELETE_TEMP_FILES:
                            pdf_path.unlink(missing_ok=True)

                    except Exception as e:
                        logger.error(f"Errore allegato: {e}")
                        errori += 1

                # Marca email come letta
                gmail.marca_come_letta(uid)

            except Exception as e:
                logger.error(f"Errore email {uid}: {e}")
                errori += 1

        # Riepilogo
        logger.info("=" * 60)
        logger.info(f"RIEPILOGO: {processate} processate, {errori} errori")
        logger.info("=" * 60)

        return 0

    finally:
        gmail.disconnetti()


if __name__ == "__main__":
    sys.exit(main())
