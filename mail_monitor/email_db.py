import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Carica variabili dal backend/.env
backend_env = Path(__file__).parent.parent / 'backend' / '.env'
load_dotenv(backend_env, override=True)

# Configurazione PostgreSQL (stessa del backend)
DB_CONFIG = {
    'host': os.getenv('PG_HOST', 'localhost'),
    'port': int(os.getenv('PG_PORT', '5432')),
    'database': os.getenv('PG_DATABASE', 'to_extractor'),
    'user': os.getenv('PG_USER', 'to_extractor_user'),
    'password': os.getenv('PG_PASSWORD', '')
}

def get_db():
    """Connessione diretta al database PostgreSQL."""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    return conn

class EmailDB:

    @staticmethod
    def get_statistiche() -> Dict:
        """Ritorna statistiche sulle email."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM EMAIL_ACQUISIZIONI")
            total = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) as cnt FROM EMAIL_ACQUISIZIONI WHERE stato = 'PROCESSATA'")
            processate = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) as cnt FROM EMAIL_ACQUISIZIONI WHERE stato = 'ERRORE'")
            errori = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) as cnt FROM EMAIL_ACQUISIZIONI WHERE stato = 'DA_PROCESSARE'")
            in_coda = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) as cnt FROM EMAIL_ACQUISIZIONI WHERE stato = 'DUPLICATO'")
            duplicati = cur.fetchone()['cnt']
            conn.close()
            return {
                "TOTALE": total,
                "PROCESSATE": processate,
                "ERRORI": errori,
                "IN_CODA": in_coda,
                "DUPLICATI": duplicati
            }
        except Exception as e:
            print(f"Errore get_statistiche: {e}")
            return {"TOTALE": 0, "PROCESSATE": 0, "ERRORI": 0, "IN_CODA": 0, "DUPLICATI": 0}

    @staticmethod
    def email_gia_processata(message_id: str, attachment_hash: str = None) -> bool:
        """Verifica se un'email/allegato è già stato processato."""
        conn = get_db()
        try:
            cur = conn.cursor()
            if attachment_hash:
                cur.execute(
                    "SELECT 1 FROM EMAIL_ACQUISIZIONI WHERE message_id = %s AND attachment_hash = %s",
                    (message_id, attachment_hash)
                )
            else:
                cur.execute(
                    "SELECT 1 FROM EMAIL_ACQUISIZIONI WHERE message_id = %s",
                    (message_id,)
                )
            result = cur.fetchone()
            conn.close()
            return result is not None
        except:
            return False

    @staticmethod
    def hash_gia_processato(attachment_hash: str) -> bool:
        """Verifica se un allegato con questo hash è già stato processato."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM EMAIL_ACQUISIZIONI WHERE attachment_hash = %s",
                (attachment_hash,)
            )
            result = cur.fetchone()
            conn.close()
            return result is not None
        except:
            return False

    @staticmethod
    def inserisci_email(email_record: Dict) -> int:
        """Inserisce una nuova email nel database. Accetta un dizionario."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO EMAIL_ACQUISIZIONI
                (message_id, gmail_id, subject, sender_email, sender_name,
                 received_date, attachment_filename, attachment_size, attachment_hash, stato)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_email
            """, (
                email_record.get('message_id'),
                email_record.get('gmail_id', ''),
                email_record.get('subject', ''),
                email_record.get('sender_email', ''),
                email_record.get('sender_name', ''),
                email_record.get('received_date', ''),
                email_record.get('attachment_filename', ''),
                email_record.get('attachment_size', 0),
                email_record.get('attachment_hash', ''),
                email_record.get('stato', 'DA_PROCESSARE')
            ))
            id_email = cur.fetchone()['id_email']
            conn.commit()
            conn.close()
            return id_email
        except Exception as e:
            print(f"Errore inserimento email: {e}")
            return -1

    @staticmethod
    def aggiorna_processata(message_id: str, id_acquisizione: int, label: str = None) -> bool:
        """Aggiorna lo stato email a PROCESSATA dopo elaborazione."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE EMAIL_ACQUISIZIONI
                SET stato = 'PROCESSATA',
                    id_acquisizione = %s,
                    label_applicata = %s,
                    data_elaborazione = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE message_id = %s
            """, (id_acquisizione, label, message_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Errore aggiornamento processata: {e}")
            return False

    @staticmethod
    def aggiorna_errore(message_id: str, errore_messaggio: str) -> bool:
        """Aggiorna lo stato email a ERRORE."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE EMAIL_ACQUISIZIONI
                SET stato = 'ERRORE',
                    errore_messaggio = %s,
                    num_retry = COALESCE(num_retry, 0) + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE message_id = %s
            """, (errore_messaggio, message_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Errore aggiornamento errore: {e}")
            return False

    @staticmethod
    def get_last_scan_date() -> Optional[date]:
        """Restituisce la data dell'ultimo scan riuscito da email_config."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT last_scan_date FROM email_config LIMIT 1")
            row = cur.fetchone()
            conn.close()
            if row and row['last_scan_date']:
                return row['last_scan_date']
            return None
        except Exception as e:
            print(f"Errore get_last_scan_date: {e}")
            return None

    @staticmethod
    def update_last_scan_date(scan_date: date) -> bool:
        """Aggiorna la data dell'ultimo scan riuscito in email_config."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE email_config SET last_scan_date = %s, updated_at = CURRENT_TIMESTAMP",
                (scan_date,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Errore update_last_scan_date: {e}")
            return False

    @staticmethod
    def reset_tabella() -> bool:
        """Resetta la tabella EMAIL_ACQUISIZIONI (per debug/test)."""
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM EMAIL_ACQUISIZIONI")
            conn.commit()
            conn.close()
            print("Tabella EMAIL_ACQUISIZIONI resettata.")
            return True
        except Exception as e:
            print(f"Errore reset tabella: {e}")
            return False
