# =============================================================================
# TO_EXTRACTOR v6.2 - GMAIL ROUTER
# =============================================================================
# Endpoint per gestione integrazione Gmail Monitor
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

router = APIRouter(prefix="/gmail", tags=["Gmail Monitor"])

# Path al modulo gmail_monitor
GMAIL_MONITOR_PATH = Path(__file__).parent.parent.parent.parent / "gmail_monitor"


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
    "emails_errors": 0
}


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status")
async def gmail_status() -> Dict[str, Any]:
    """
    Ritorna lo stato del Gmail Monitor.

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
    config_status = _get_gmail_config()

    return {
        "success": True,
        "sync_status": {
            "is_running": _sync_status["is_running"],
            "last_sync": _sync_status["last_sync"],
            "last_result": _sync_status["last_result"]
        },
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
async def gmail_sync_manual(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Avvia sincronizzazione manuale delle email Gmail.

    La sincronizzazione viene eseguita in background.
    Usa GET /gmail/status per controllare lo stato.
    """
    global _sync_status

    if _sync_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Sincronizzazione già in corso. Attendere il completamento."
        )

    # Verifica configurazione
    config = _get_gmail_config()
    if not config.get("configured"):
        raise HTTPException(
            status_code=400,
            detail="Gmail non configurato. Configurare le credenziali nel file .env"
        )

    # Avvia in background
    _sync_status["is_running"] = True
    _sync_status["last_sync"] = datetime.now().isoformat()

    background_tasks.add_task(_run_gmail_sync)

    log_operation('GMAIL_SYNC', 'EMAIL_ACQUISIZIONI', 0, 'Sincronizzazione manuale avviata')

    return {
        "success": True,
        "message": "Sincronizzazione avviata in background",
        "started_at": _sync_status["last_sync"]
    }


@router.get("/emails")
async def gmail_emails(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    stato: Optional[str] = Query(None, description="Filtra per stato"),
    search: Optional[str] = Query(None, description="Cerca in subject/sender")
) -> Dict[str, Any]:
    """
    Lista delle email scaricate da Gmail.

    Args:
        limit: Numero massimo di risultati
        offset: Offset per paginazione
        stato: Filtro stato (PROCESSATA, ERRORE, DA_PROCESSARE, DUPLICATO)
        search: Ricerca in subject o sender_email
    """
    db = get_db()

    # Query base
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
            a.stato as stato_acquisizione
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
async def gmail_email_detail(id_email: int) -> Dict[str, Any]:
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
async def gmail_email_retry(id_email: int, background_tasks: BackgroundTasks) -> Dict[str, Any]:
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

    log_operation('GMAIL_RETRY', 'EMAIL_ACQUISIZIONI', id_email,
                 f"Retry email: {email['subject']}")

    return {
        "success": True,
        "message": "Email rimessa in coda per elaborazione"
    }


@router.get("/stats")
async def gmail_stats() -> Dict[str, Any]:
    """
    Statistiche dettagliate Gmail Monitor.
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

def _get_gmail_config() -> Dict[str, Any]:
    """
    Legge la configurazione Gmail (senza esporre password).
    """
    try:
        # Prova a importare la config dal modulo gmail_monitor
        sys.path.insert(0, str(GMAIL_MONITOR_PATH))
        from config import Config

        errors = Config.validate()

        return {
            "configured": len(errors) == 0,
            "email": Config.GMAIL_EMAIL or "(non configurato)",
            "label": Config.GMAIL_LABEL,
            "unread_only": Config.UNREAD_ONLY,
            "mark_as_read": Config.MARK_AS_READ,
            "max_emails_per_run": Config.MAX_EMAILS_PER_RUN,
            "backend_url": Config.BACKEND_URL,
            "errors": errors if errors else None
        }
    except Exception as e:
        return {
            "configured": False,
            "error": str(e)
        }
    finally:
        # Rimuovi dal path
        if str(GMAIL_MONITOR_PATH) in sys.path:
            sys.path.remove(str(GMAIL_MONITOR_PATH))


def _run_gmail_sync():
    """
    Esegue la sincronizzazione Gmail in background.
    """
    global _sync_status

    try:
        # Esegui gmail_monitor.py come subprocess
        result = subprocess.run(
            [sys.executable, str(GMAIL_MONITOR_PATH / "gmail_monitor.py")],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minuti timeout
            cwd=str(GMAIL_MONITOR_PATH)
        )

        _sync_status["last_result"] = {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",  # Ultimi 2000 char
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "completed_at": datetime.now().isoformat()
        }

        # Conta email processate dal log
        if "RIEPILOGO:" in result.stdout:
            import re
            match = re.search(r'(\d+) processate, (\d+) errori', result.stdout)
            if match:
                _sync_status["emails_processed"] = int(match.group(1))
                _sync_status["emails_errors"] = int(match.group(2))

    except subprocess.TimeoutExpired:
        _sync_status["last_result"] = {
            "success": False,
            "error": "Timeout: sincronizzazione interrotta dopo 5 minuti",
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        _sync_status["last_result"] = {
            "success": False,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }
    finally:
        _sync_status["is_running"] = False
