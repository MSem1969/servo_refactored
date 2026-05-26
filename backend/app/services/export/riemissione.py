# =============================================================================
# SERV.O - RIEMISSIONE TRACCIATO
# =============================================================================
# Logica per edit + ritrasmissione di un tracciato gia' inviato all'ERP
# quando questo viene scartato per errori di formato o contenuto.
#
# Flusso:
#  1. read_tracciato_files: carica i file TO_T/TO_D di un'esportazione e
#     calcola il prossimo suffisso ordine per la riemissione.
#  2. crea_riemissione: prende contenuto editato, sostituisce il numero
#     ordine (con suffisso .N forzato), scrive nuovi file, crea una
#     nuova riga in `esportazioni` con is_riemissione=TRUE, marca
#     l'originale SUPERSEDED e sposta i suoi file in archive/.
#  3. ritrasmetti_esportazione: rinomina i file con nuovo timestamp e
#     invia via FTP riusando il sender esistente.
# =============================================================================

import os
import re
import shutil
import time
from datetime import datetime
from typing import Dict, Any, Optional

from ...config import config
from ...database_pg import get_db
from .generator import _apply_export_suffix, _get_export_suffix


ARCHIVE_SUBDIR = "archive"

# Posizioni fisse del numero ordine nel tracciato EDI
TO_T_ORDER_START = 10   # pos 11-40 1-indexed -> slice [10:40]
TO_T_ORDER_END = 40
TO_D_ORDER_START = 0    # pos 1-30 1-indexed  -> slice [0:30]
TO_D_ORDER_END = 30


# =============================================================================
# HELPER FILE I/O
# =============================================================================

def _archive_dir() -> str:
    path = os.path.join(config.OUTPUT_DIR, ARCHIVE_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def _read_file(filename: str) -> str:
    path = os.path.join(config.OUTPUT_DIR, filename)
    if not os.path.exists(path):
        # File spostato in archive? Prova lì
        archived = os.path.join(_archive_dir(), filename)
        if os.path.exists(archived):
            path = archived
        else:
            raise FileNotFoundError(f"File tracciato non trovato: {filename}")
    with open(path, "r", encoding=config.ENCODING, newline="") as f:
        return f.read()


def _write_file(filename: str, content: str) -> str:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.OUTPUT_DIR, filename)
    with open(path, "w", encoding=config.ENCODING, newline="") as f:
        f.write(content)
    return path


def _move_to_archive(filename: str) -> Optional[str]:
    src = os.path.join(config.OUTPUT_DIR, filename)
    if not os.path.exists(src):
        return None
    dest_dir = _archive_dir()
    dest = os.path.join(dest_dir, filename)
    # Evita collisioni: se gia' presente, aggiungi suffisso timestamp
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        dest = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")
    shutil.move(src, dest)
    return dest


def _build_filename(prefix: str) -> str:
    """Costruisce nome file TO_T/TO_D con timestamp anti-collisione."""
    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    return f"{prefix}_{ts}.TXT"


def _normalize_crlf(text: str) -> str:
    """Normalizza terminatori riga a CRLF."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", "\r\n")


# =============================================================================
# READ + PREVIEW
# =============================================================================

def read_tracciato_files(id_esportazione: int) -> Dict[str, Any]:
    """
    Carica i file TO_T/TO_D di un'esportazione e prepara i metadati
    necessari per l'editor di riemissione.
    """
    db = get_db()
    row = db.execute("""
        SELECT e.id_esportazione, e.nome_file_to_t, e.nome_file_to_d,
               e.stato_ftp, e.is_riemissione, e.riemessa_da_id,
               ed.id_testata, ot.numero_ordine_vendor
        FROM esportazioni e
        LEFT JOIN esportazioni_dettaglio ed ON ed.id_esportazione = e.id_esportazione
        LEFT JOIN ordini_testata ot ON ot.id_testata = ed.id_testata
        WHERE e.id_esportazione = %s
    """, (id_esportazione,)).fetchone()

    if not row:
        raise ValueError(f"Esportazione {id_esportazione} non trovata")

    row = dict(row)
    to_t_content = _read_file(row["nome_file_to_t"]) if row["nome_file_to_t"] else ""
    to_d_content = _read_file(row["nome_file_to_d"]) if row["nome_file_to_d"] else ""

    # Suffisso prossimo (riemissione) - count include tutte le esportazioni (anche SUPERSEDED)
    numero_db = row["numero_ordine_vendor"] or ""
    suffisso_prossimo = None
    nuovo_numero_atteso = None
    if row["id_testata"]:
        count = _get_export_suffix(db, row["id_testata"])
        suffisso_prossimo = count
        nuovo_numero_atteso = f"{numero_db}.{count}"

    return {
        "id_esportazione": row["id_esportazione"],
        "nome_file_to_t": row["nome_file_to_t"],
        "nome_file_to_d": row["nome_file_to_d"],
        "stato_ftp": row["stato_ftp"],
        "is_riemissione": row["is_riemissione"],
        "riemessa_da_id": row["riemessa_da_id"],
        "id_testata": row["id_testata"],
        "numero_ordine_db": numero_db,
        "suffisso_prossimo": suffisso_prossimo,
        "nuovo_numero_atteso": nuovo_numero_atteso,
        "to_t": to_t_content,
        "to_d": to_d_content,
    }


# =============================================================================
# SOSTITUZIONE NUMERO ORDINE
# =============================================================================

def _replace_order_number_to_t(content: str, new_number: str) -> str:
    """Sostituisce il numero ordine nel TO_T (pos 11-40, riga unica)."""
    content = _normalize_crlf(content)
    lines = content.split("\r\n")
    if not lines or not lines[0]:
        raise ValueError("TO_T vuoto o malformato")
    line = lines[0]
    if len(line) < TO_T_ORDER_END:
        raise ValueError(f"Riga TO_T troppo corta: {len(line)} < {TO_T_ORDER_END}")
    new_field = new_number.ljust(TO_T_ORDER_END - TO_T_ORDER_START)[:TO_T_ORDER_END - TO_T_ORDER_START]
    lines[0] = line[:TO_T_ORDER_START] + new_field + line[TO_T_ORDER_END:]
    return "\r\n".join(lines)


def _replace_order_number_to_d(content: str, new_number: str) -> str:
    """Sostituisce il numero ordine nel TO_D (pos 1-30, su ogni riga non vuota)."""
    content = _normalize_crlf(content)
    lines = content.split("\r\n")
    new_field = new_number.ljust(TO_D_ORDER_END - TO_D_ORDER_START)[:TO_D_ORDER_END - TO_D_ORDER_START]
    out = []
    for line in lines:
        if not line:
            out.append(line)
            continue
        if len(line) < TO_D_ORDER_END:
            raise ValueError(f"Riga TO_D troppo corta: {len(line)} < {TO_D_ORDER_END}")
        out.append(new_field + line[TO_D_ORDER_END:])
    return "\r\n".join(out)


# =============================================================================
# CREAZIONE RIEMISSIONE
# =============================================================================

def crea_riemissione(
    id_esportazione: int,
    to_t_content: str,
    to_d_content: str,
    note: Optional[str] = None,
    operatore_username: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crea una nuova esportazione (riemissione) a partire dal contenuto
    editato di TO_T/TO_D di un'esportazione esistente.

    Operazioni:
      - Calcola nuovo numero ordine con suffisso .N forzato
      - Sostituisce numero ordine nel testo editato
      - Scrive nuovi file con nuovo timestamp
      - Inserisce esportazione is_riemissione=TRUE, stato_ftp=PENDING
      - Inserisce riga su esportazioni_dettaglio (stesso id_testata)
      - Marca originale stato_ftp=SUPERSEDED, data_riemissione=NOW
      - Sposta file originali in archive/
    """
    if not to_t_content or not to_d_content:
        raise ValueError("Contenuto TO_T o TO_D vuoto")

    db = get_db()

    # 1. Carica esportazione originale + ordine collegato
    orig = db.execute("""
        SELECT e.id_esportazione, e.nome_file_to_t, e.nome_file_to_d,
               e.stato_ftp,
               ed.id_testata, ot.numero_ordine_vendor
        FROM esportazioni e
        LEFT JOIN esportazioni_dettaglio ed ON ed.id_esportazione = e.id_esportazione
        LEFT JOIN ordini_testata ot ON ot.id_testata = ed.id_testata
        WHERE e.id_esportazione = %s
    """, (id_esportazione,)).fetchone()

    if not orig:
        raise ValueError(f"Esportazione {id_esportazione} non trovata")
    orig = dict(orig)

    if orig["stato_ftp"] == "SUPERSEDED":
        raise ValueError("Esportazione gia' sostituita da una riemissione precedente")

    id_testata = orig["id_testata"]
    if not id_testata:
        raise ValueError("Impossibile riemettere: esportazione senza ordine associato")

    numero_db = orig["numero_ordine_vendor"] or ""
    if not numero_db:
        raise ValueError("Numero ordine vendor mancante sull'ordine")

    # 2. Calcola nuovo numero ordine (force=True per riemissione)
    nuovo_numero = _apply_export_suffix(numero_db, db, id_testata, force=True)

    # 3. Applica sostituzione numero ordine al contenuto editato
    to_t_final = _replace_order_number_to_t(to_t_content, nuovo_numero)
    to_d_final = _replace_order_number_to_d(to_d_content, nuovo_numero)

    # 4. Scrivi nuovi file
    new_to_t_name = _build_filename("TO_T")
    new_to_d_name = _build_filename("TO_D")
    # Anti-collisione (estremamente raro: stesso secondo)
    while os.path.exists(os.path.join(config.OUTPUT_DIR, new_to_t_name)) or \
          os.path.exists(os.path.join(config.OUTPUT_DIR, new_to_d_name)):
        time.sleep(1)
        new_to_t_name = _build_filename("TO_T")
        new_to_d_name = _build_filename("TO_D")

    _write_file(new_to_t_name, to_t_final)
    _write_file(new_to_d_name, to_d_final)

    # 5. Inserisci nuova esportazione + dettaglio + aggiorna originale (transazione)
    try:
        new_id = db.execute("""
            INSERT INTO esportazioni (
                nome_file_to_t, nome_file_to_d,
                num_testate, num_dettagli,
                stato, stato_ftp,
                is_riemissione, riemessa_da_id,
                note, note_riemissione,
                data_generazione
            ) VALUES (
                %s, %s, 1, %s, 'GENERATO', 'PENDING',
                TRUE, %s, %s, %s, CURRENT_TIMESTAMP
            )
            RETURNING id_esportazione
        """, (
            new_to_t_name,
            new_to_d_name,
            len([l for l in to_d_final.split("\r\n") if l]),
            id_esportazione,
            f"Riemissione di esportazione #{id_esportazione}",
            note,
        )).fetchone()[0]

        db.execute("""
            INSERT INTO esportazioni_dettaglio (id_esportazione, id_testata, data_evasione)
            VALUES (%s, %s, CURRENT_DATE)
        """, (new_id, id_testata))

        db.execute("""
            UPDATE esportazioni
            SET stato_ftp = 'SUPERSEDED',
                data_riemissione = CURRENT_TIMESTAMP
            WHERE id_esportazione = %s
        """, (id_esportazione,))

        # Audit su ftp_log
        db.execute("""
            INSERT INTO ftp_log (id_esportazione, azione, esito, messaggio, created_at)
            VALUES (%s, 'RIEMISSIONE', 'SUCCESS', %s, CURRENT_TIMESTAMP)
        """, (
            id_esportazione,
            f"Riemessa come #{new_id} (numero ordine: {nuovo_numero})"
            + (f" - operatore: {operatore_username}" if operatore_username else ""),
        ))

        db.commit()
    except Exception:
        db.rollback()
        # Rimuovi i file appena scritti per non lasciare sporcizia
        for f in (new_to_t_name, new_to_d_name):
            try:
                os.remove(os.path.join(config.OUTPUT_DIR, f))
            except OSError:
                pass
        raise

    # 6. Sposta file originali in archive (post-commit: se fallisce, non rolllback DB)
    archived_t = _move_to_archive(orig["nome_file_to_t"]) if orig["nome_file_to_t"] else None
    archived_d = _move_to_archive(orig["nome_file_to_d"]) if orig["nome_file_to_d"] else None

    return {
        "id_esportazione_riemessa": new_id,
        "id_esportazione_originale": id_esportazione,
        "nuovo_numero_ordine": nuovo_numero,
        "file_to_t": new_to_t_name,
        "file_to_d": new_to_d_name,
        "archive": {
            "to_t": archived_t,
            "to_d": archived_d,
        },
    }


# =============================================================================
# RITRASMISSIONE FTP
# =============================================================================

def _rename_with_new_timestamp(old_name: str, prefix: str) -> str:
    """Rinomina un file su disco con nuovo timestamp; ritorna il nuovo nome."""
    if not old_name:
        return old_name
    src = os.path.join(config.OUTPUT_DIR, old_name)
    if not os.path.exists(src):
        # File potrebbe non essere stato ancora prodotto (caso anomalo)
        return old_name
    new_name = _build_filename(prefix)
    while os.path.exists(os.path.join(config.OUTPUT_DIR, new_name)):
        time.sleep(1)
        new_name = _build_filename(prefix)
    shutil.move(src, os.path.join(config.OUTPUT_DIR, new_name))
    return new_name


def ritrasmetti_esportazione(
    id_esportazione: int,
    operatore_username: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rinomina i file dell'esportazione con nuovo timestamp e li invia via FTP.
    Riusa il sender esistente.
    """
    from ..ftp.sender import FTPSender, get_ftp_client_from_config

    db = get_db()
    exp = db.execute("""
        SELECT id_esportazione, nome_file_to_t, nome_file_to_d, stato_ftp
        FROM esportazioni WHERE id_esportazione = %s
    """, (id_esportazione,)).fetchone()

    if not exp:
        raise ValueError(f"Esportazione {id_esportazione} non trovata")
    exp = dict(exp)

    if exp["stato_ftp"] in ("SENT", "SKIPPED", "ALERT_SENT", "SUPERSEDED"):
        raise ValueError(
            f"Stato {exp['stato_ftp']}: ritrasmissione non consentita"
        )

    # Rinomina file con nuovo timestamp
    new_t = _rename_with_new_timestamp(exp["nome_file_to_t"], "TO_T")
    new_d = _rename_with_new_timestamp(exp["nome_file_to_d"], "TO_D")

    db.execute("""
        UPDATE esportazioni
        SET nome_file_to_t = %s, nome_file_to_d = %s,
            stato_ftp = 'PENDING',
            ultimo_errore_ftp = NULL
        WHERE id_esportazione = %s
    """, (new_t, new_d, id_esportazione))
    db.commit()

    db.execute("""
        INSERT INTO ftp_log (id_esportazione, azione, esito, file_name, messaggio, created_at)
        VALUES (%s, 'RITRASMISSIONE', 'SUCCESS', %s, %s, CURRENT_TIMESTAMP)
    """, (
        id_esportazione,
        new_t,
        f"File rinominati per ritrasmissione (TO_T={new_t}, TO_D={new_d})"
        + (f" - operatore: {operatore_username}" if operatore_username else ""),
    ))
    db.commit()

    # Invia via FTP riusando il sender esistente
    sender = FTPSender()
    ftp_client = get_ftp_client_from_config()
    with ftp_client:
        result = sender.send_export(id_esportazione, ftp_client)

    return {
        "id_esportazione": id_esportazione,
        "file_to_t": new_t,
        "file_to_d": new_d,
        "ftp_result": result,
    }
