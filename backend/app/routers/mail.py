# =============================================================================
# SERV.O v6.2 - MAIL ROUTER
# =============================================================================
# Endpoint per gestione integrazione Mail Monitor
# =============================================================================

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from ..database_pg import get_db, log_operation
from ..services.scheduler import get_scheduler_status

router = APIRouter(prefix="/mail", tags=["Mail Monitor"])

# Path al modulo mail_monitor (in Docker: /mail_monitor, in locale: ../mail_monitor)
MAIL_MONITOR_PATH = Path("/mail_monitor") if Path("/mail_monitor").exists() else Path(__file__).parent.parent.parent.parent / "mail_monitor"


# =============================================================================
# MODELS
# =============================================================================

class SyncResult(BaseModel):
    success: bool
    message: str
    emails_processed: int = 0
    emails_errors: int = 0
    started_at: str = None
    completed_at: str = None


# =============================================================================
# VARIABILE GLOBALE PER STATO SYNC
# =============================================================================

_sync_status = {
    "is_running": False,
    "last_sync": None,
    "last_result": None,
    "emails_processed": 0,
    "emails_errors": 0,
    "progress_messages": [],  # v11.0: Log progressivo
    "current_phase": None,    # v11.0: Fase corrente
    "emails_found": 0         # v11.0: Email trovate da processare
}


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status")
async def mail_status() -> Dict[str, Any]:
    """
    Ritorna lo stato del Mail Monitor.

    Include:
    - Stato configurazione (email, cartella, ecc.)
    - Statistiche email scaricate
    - Stato ultima sincronizzazione
    """
    db = get_db()

    # Statistiche email
    stats = db.execute("""
        SELECT
            COUNT(*) as totale,
            SUM(CASE WHEN stato = 'PROCESSATA' THEN 1 ELSE 0 END) as processate,
            SUM(CASE WHEN stato = 'ERRORE' THEN 1 ELSE 0 END) as errori,
            SUM(CASE WHEN stato = 'DA_PROCESSARE' THEN 1 ELSE 0 END) as in_coda,
            SUM(CASE WHEN stato = 'DUPLICATO' THEN 1 ELSE 0 END) as duplicati
        FROM EMAIL_ACQUISIZIONI
    """).fetchone()

    # Ultima email
    ultima_email = db.execute("""
        SELECT subject, sender_email, received_date, attachment_filename, stato
        FROM EMAIL_ACQUISIZIONI
        ORDER BY created_at DESC
        LIMIT 1
    """).fetchone()

    # Leggi configurazione (senza password)
    config_status = _get_mail_config()

    # Stato scheduler
    scheduler_status = get_scheduler_status()

    return {
        "success": True,
        "sync_status": {
            "is_running": _sync_status["is_running"],
            "last_sync": _sync_status["last_sync"],
            "last_result": _sync_status["last_result"],
            # v11.0: Progress info
            "progress_messages": _sync_status.get("progress_messages", [])[-10:],  # Ultimi 10 messaggi
            "current_phase": _sync_status.get("current_phase"),
            "emails_found": _sync_status.get("emails_found", 0),
            "emails_processed": _sync_status.get("emails_processed", 0),
            "emails_errors": _sync_status.get("emails_errors", 0)
        },
        "scheduler": scheduler_status,
        "config": config_status,
        "statistics": {
            "totale": stats["totale"] if stats else 0,
            "processate": stats["processate"] if stats else 0,
            "errori": stats["errori"] if stats else 0,
            "in_coda": stats["in_coda"] if stats else 0,
            "duplicati": stats["duplicati"] if stats else 0
        },
        "ultima_email": dict(ultima_email) if ultima_email else None
    }


@router.post("/sync")
async def mail_sync_manual(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Avvia sincronizzazione manuale delle email.

    La sincronizzazione viene eseguita in background.
    Usa GET /mail/status per controllare lo stato.
    """
    global _sync_status

    if _sync_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Sincronizzazione già in corso. Attendere il completamento."
        )

    # Verifica configurazione
    config = _get_mail_config()
    if not config.get("configured"):
        raise HTTPException(
            status_code=400,
            detail="Mail non configurato. Configurare SMTP_USER e SMTP_PASSWORD nel file backend/.env"
        )

    # Avvia in background
    _sync_status["is_running"] = True
    _sync_status["last_sync"] = datetime.now().isoformat()

    background_tasks.add_task(_run_mail_sync)

    log_operation('MAIL_SYNC', 'EMAIL_ACQUISIZIONI', 0, 'Sincronizzazione manuale avviata')

    return {
        "success": True,
        "message": "Sincronizzazione avviata in background",
        "started_at": _sync_status["last_sync"]
    }


@router.get("/emails")
async def mail_emails(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    stato: Optional[str] = Query(None, description="Filtra per stato"),
    search: Optional[str] = Query(None, description="Cerca in subject/sender")
) -> Dict[str, Any]:
    """
    Lista delle email scaricate.

    Args:
        limit: Numero massimo di risultati
        offset: Offset per paginazione
        stato: Filtro stato (PROCESSATA, ERRORE, DA_PROCESSARE, DUPLICATO)
        search: Ricerca in subject o sender_email
    """
    db = get_db()

    # Query base - v11.0: aggiunto num_ordini, num_righe per uniformità con upload manuale
    query = """
        SELECT
            e.id_email,
            e.message_id,
            e.subject,
            e.sender_email,
            e.sender_name,
            e.received_date,
            e.attachment_filename,
            e.attachment_size,
            e.stato,
            e.data_elaborazione,
            e.errore_messaggio,
            e.id_acquisizione,
            e.created_at,
            v.codice_vendor AS vendor,
            a.stato as stato_acquisizione,
            a.num_ordini,
            a.num_righe
        FROM EMAIL_ACQUISIZIONI e
        LEFT JOIN ACQUISIZIONI a ON e.id_acquisizione = a.id_acquisizione
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        WHERE 1=1
    """
    params = []

    if stato:
        query += " AND e.stato = ?"
        params.append(stato)

    if search:
        query += " AND (e.subject LIKE ? OR e.sender_email LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    # Count totale - costruiamo una query separata
    count_query = """
        SELECT COUNT(*)
        FROM EMAIL_ACQUISIZIONI e
        LEFT JOIN ACQUISIZIONI a ON e.id_acquisizione = a.id_acquisizione
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        WHERE 1=1
    """

    if stato:
        count_query += " AND e.stato = ?"
    if search:
        count_query += " AND (e.subject LIKE ? OR e.sender_email LIKE ?)"

    result = db.execute(count_query, params).fetchone()
    total = result[0] if result else 0

    # Query con paginazione
    query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "emails": [dict(row) for row in rows]
    }


@router.get("/emails/{id_email}")
async def mail_email_detail(id_email: int) -> Dict[str, Any]:
    """
    Dettaglio singola email.
    """
    db = get_db()

    email = db.execute("""
        SELECT
            e.*,
            v.codice_vendor AS vendor,
            a.stato as stato_acquisizione,
            a.num_ordini,
            a.num_righe
        FROM EMAIL_ACQUISIZIONI e
        LEFT JOIN ACQUISIZIONI a ON e.id_acquisizione = a.id_acquisizione
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        WHERE e.id_email = ?
    """, (id_email,)).fetchone()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    return {
        "success": True,
        "email": dict(email)
    }


@router.post("/emails/{id_email}/retry")
async def mail_email_retry(id_email: int, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Ritenta elaborazione di una email in errore.
    """
    db = get_db()

    email = db.execute("""
        SELECT * FROM EMAIL_ACQUISIZIONI WHERE id_email = ?
    """, (id_email,)).fetchone()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    if email["stato"] not in ("ERRORE", "DA_PROCESSARE"):
        raise HTTPException(
            status_code=400,
            detail=f"Email non può essere rielaborata (stato: {email['stato']})"
        )

    # Reset stato
    db.execute("""
        UPDATE EMAIL_ACQUISIZIONI
        SET stato = 'DA_PROCESSARE',
            num_retry = num_retry + 1,
            errore_messaggio = NULL,
            updated_at = datetime('now')
        WHERE id_email = ?
    """, (id_email,))
    db.commit()

    log_operation('MAIL_RETRY', 'EMAIL_ACQUISIZIONI', id_email,
                 f"Retry email: {email['subject']}")

    return {
        "success": True,
        "message": "Email rimessa in coda per elaborazione"
    }


@router.get("/stats")
async def mail_stats() -> Dict[str, Any]:
    """
    Statistiche dettagliate Mail Monitor.
    """
    db = get_db()

    # Per stato
    per_stato = db.execute("""
        SELECT stato, COUNT(*) as count
        FROM EMAIL_ACQUISIZIONI
        GROUP BY stato
    """).fetchall()

    # Per giorno (ultimi 7 giorni)
    per_giorno = db.execute("""
        SELECT
            date(received_date) as giorno,
            COUNT(*) as count,
            SUM(CASE WHEN stato = 'PROCESSATA' THEN 1 ELSE 0 END) as processate,
            SUM(CASE WHEN stato = 'ERRORE' THEN 1 ELSE 0 END) as errori
        FROM EMAIL_ACQUISIZIONI
        WHERE received_date >= date('now', '-7 days')
        GROUP BY date(received_date)
        ORDER BY giorno DESC
    """).fetchall()

    # Per sender
    per_sender = db.execute("""
        SELECT sender_email, COUNT(*) as count
        FROM EMAIL_ACQUISIZIONI
        GROUP BY sender_email
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    # Per vendor (tramite acquisizioni)
    per_vendor = db.execute("""
        SELECT
            COALESCE(v.codice_vendor, 'N/D') as vendor,
            COUNT(*) as count
        FROM EMAIL_ACQUISIZIONI e
        LEFT JOIN ACQUISIZIONI a ON e.id_acquisizione = a.id_acquisizione
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        GROUP BY v.codice_vendor
        ORDER BY count DESC
    """).fetchall()

    return {
        "success": True,
        "per_stato": {row["stato"]: row["count"] for row in per_stato},
        "per_giorno": [dict(row) for row in per_giorno],
        "per_sender": [dict(row) for row in per_sender],
        "per_vendor": [dict(row) for row in per_vendor]
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_mail_config() -> Dict[str, Any]:
    """
    Legge la configurazione Mail (senza esporre password).
    Verifica direttamente le variabili d'ambiente.
    """
    # Leggi variabili d'ambiente direttamente
    mail_user = os.getenv('SMTP_USER', '') or os.getenv('IMAP_USER', '')
    mail_password = os.getenv('SMTP_PASSWORD', '') or os.getenv('IMAP_PASSWORD', '')

    errors = []

    if not mail_user:
        errors.append("Email non configurata (SMTP_USER o IMAP_USER)")

    if not mail_password:
        errors.append("Password non configurata (SMTP_PASSWORD o IMAP_PASSWORD)")

    if mail_user and '@' not in mail_user:
        errors.append("Email non valida")

    # Verifica App Password (16 caratteri senza spazi)
    if mail_password and len(mail_password.replace(' ', '')) != 16:
        errors.append("App Password deve essere 16 caratteri (senza spazi)")

    return {
        "configured": len(errors) == 0,
        "email": mail_user or "(non configurato)",
        "folder": os.getenv('MAIL_FOLDER', 'INBOX'),
        "unread_only": os.getenv('UNREAD_ONLY', 'true').lower() == 'true',
        "mark_as_read": os.getenv('MARK_AS_READ', 'true').lower() == 'true',
        "max_emails_per_run": int(os.getenv('MAX_EMAILS_PER_RUN', '50')),
        "backend_url": os.getenv('BACKEND_URL', 'http://localhost:8000'),
        "errors": errors if errors else None
    }


def _run_mail_sync():
    """
    Esegue la sincronizzazione Mail in background.
    v11.0: Streaming output per progress real-time.
    """
    global _sync_status
    import re

    # Reset progress
    _sync_status["progress_messages"] = []
    _sync_status["current_phase"] = "Connessione al server mail..."
    _sync_status["emails_found"] = 0
    _sync_status["emails_processed"] = 0
    _sync_status["emails_errors"] = 0

    def add_progress(msg):
        """Aggiunge messaggio di progresso con timestamp."""
        _sync_status["progress_messages"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": msg
        })
        # Mantieni solo ultimi 50 messaggi
        if len(_sync_status["progress_messages"]) > 50:
            _sync_status["progress_messages"] = _sync_status["progress_messages"][-50:]

    add_progress("Avvio sincronizzazione mail...")

    try:
        # Esegui mail_monitor.py con streaming output
        process = subprocess.Popen(
            [sys.executable, str(MAIL_MONITOR_PATH / "mail_monitor.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(MAIL_MONITOR_PATH),
            bufsize=1  # Line buffered
        )

        stdout_lines = []
        start_time = datetime.now()

        # Leggi output line-by-line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break

            line = line.strip()
            stdout_lines.append(line)

            # Parse progress da output
            if "Email da processare:" in line:
                match = re.search(r'Email da processare: (\d+)', line)
                if match:
                    count = int(match.group(1))
                    _sync_status["emails_found"] = count
                    _sync_status["current_phase"] = f"Trovate {count} email da processare"
                    add_progress(f"Trovate {count} email da processare")

            elif "Processo email UID" in line:
                _sync_status["current_phase"] = "Elaborazione email..."
                # Non loggiamo ogni UID per non riempire il log

            elif line.startswith("OK -"):
                _sync_status["emails_processed"] += 1
                # Estrai ID acquisizione se presente
                match = re.search(r'ID acquisizione: (\d+)', line)
                if match:
                    add_progress(f"Email elaborata (ID: {match.group(1)})")

            elif "senza allegati PDF" in line.lower() or "già processata" in line.lower():
                # Email skippate - non contiamo come errore
                pass

            elif "Errore" in line or "ERROR" in line:
                _sync_status["emails_errors"] += 1
                add_progress(f"Errore: {line[:100]}")

            elif "RIEPILOGO:" in line:
                _sync_status["current_phase"] = "Completato"
                match = re.search(r'(\d+) processate, (\d+) errori', line)
                if match:
                    _sync_status["emails_processed"] = int(match.group(1))
                    _sync_status["emails_errors"] = int(match.group(2))
                add_progress(line)

            # Timeout check
            if (datetime.now() - start_time).seconds > 300:
                process.kill()
                raise subprocess.TimeoutExpired(cmd="mail_monitor.py", timeout=300)

        process.wait()

        _sync_status["last_result"] = {
            "success": process.returncode == 0,
            "return_code": process.returncode,
            "stdout": "\n".join(stdout_lines[-50:]),  # Ultime 50 righe
            "completed_at": datetime.now().isoformat(),
            "emails_processed": _sync_status["emails_processed"],
            "emails_errors": _sync_status["emails_errors"]
        }

        add_progress(f"Sincronizzazione completata: {_sync_status['emails_processed']} email elaborate")

    except subprocess.TimeoutExpired:
        _sync_status["last_result"] = {
            "success": False,
            "error": "Timeout: sincronizzazione interrotta dopo 5 minuti",
            "completed_at": datetime.now().isoformat()
        }
        add_progress("Timeout - sincronizzazione interrotta")
    except Exception as e:
        _sync_status["last_result"] = {
            "success": False,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }
        add_progress(f"Errore: {str(e)}")
    finally:
        _sync_status["is_running"] = False
        _sync_status["current_phase"] = None
