"""
Email logging utilities - Traccia tutti gli invii per audit.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .constants import EmailStatus


def log_email_sent(db, destinatario: str, oggetto: str,
                   tipo: str, ticket_id: Optional[int] = None) -> int:
    """
    Registra email inviata con successo.

    Args:
        db: Connessione database
        destinatario: Email destinatario
        oggetto: Oggetto email
        tipo: Tipo email (da EmailType)
        ticket_id: ID ticket correlato (opzionale)

    Returns:
        ID log creato
    """
    query = """
        INSERT INTO email_log
        (id_ticket, destinatario, oggetto, tipo, stato_invio, sent_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING id_log
    """
    result = db.execute(query, [
        ticket_id, destinatario, oggetto, tipo, EmailStatus.SENT
    ]).fetchone()
    db.commit()
    return result['id_log']


def log_email_failed(db, destinatario: str, oggetto: str,
                     tipo: str, errore: str,
                     ticket_id: Optional[int] = None) -> int:
    """
    Registra email fallita.

    Args:
        db: Connessione database
        destinatario: Email destinatario
        oggetto: Oggetto email
        tipo: Tipo email
        errore: Messaggio errore
        ticket_id: ID ticket correlato (opzionale)

    Returns:
        ID log creato
    """
    query = """
        INSERT INTO email_log
        (id_ticket, destinatario, oggetto, tipo, stato_invio, errore)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id_log
    """
    result = db.execute(query, [
        ticket_id, destinatario, oggetto, tipo, EmailStatus.FAILED, errore
    ]).fetchone()
    db.commit()
    return result['id_log']


def get_email_log(db, filters: Optional[Dict[str, Any]] = None,
                  limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Recupera log email con filtri.

    Args:
        db: Connessione database
        filters: Dict con filtri (stato_invio, tipo, ticket_id)
        limit: Numero massimo risultati
        offset: Offset per paginazione

    Returns:
        Lista di log email
    """
    query = """
        SELECT l.*, t.oggetto as ticket_oggetto
        FROM email_log l
        LEFT JOIN crm_tickets t ON l.id_ticket = t.id_ticket
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get('stato_invio'):
            query += " AND l.stato_invio = %s"
            params.append(filters['stato_invio'])
        if filters.get('tipo'):
            query += " AND l.tipo = %s"
            params.append(filters['tipo'])
        if filters.get('ticket_id'):
            query += " AND l.id_ticket = %s"
            params.append(filters['ticket_id'])
        if filters.get('destinatario'):
            query += " AND l.destinatario ILIKE %s"
            params.append(f"%{filters['destinatario']}%")

    query += " ORDER BY l.created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def mark_for_retry(db, log_id: int) -> bool:
    """
    Marca email per retry.

    Args:
        db: Connessione database
        log_id: ID log da ritentare

    Returns:
        True se operazione riuscita
    """
    query = """
        UPDATE email_log
        SET stato_invio = %s, errore = NULL
        WHERE id_log = %s AND stato_invio = %s
    """
    result = db.execute(query, [EmailStatus.RETRY, log_id, EmailStatus.FAILED])
    db.commit()
    return result.rowcount > 0


def update_log_status(db, log_id: int, status: str,
                      errore: Optional[str] = None) -> bool:
    """
    Aggiorna stato log email.

    Args:
        db: Connessione database
        log_id: ID log
        status: Nuovo stato
        errore: Messaggio errore (opzionale)

    Returns:
        True se operazione riuscita
    """
    if status == EmailStatus.SENT:
        query = """
            UPDATE email_log
            SET stato_invio = %s, sent_at = CURRENT_TIMESTAMP, errore = NULL
            WHERE id_log = %s
        """
        params = [status, log_id]
    else:
        query = """
            UPDATE email_log
            SET stato_invio = %s, errore = %s
            WHERE id_log = %s
        """
        params = [status, errore, log_id]

    result = db.execute(query, params)
    db.commit()
    return result.rowcount > 0


def get_pending_emails(db, limit: int = 10) -> List[Dict]:
    """
    Recupera email in attesa di invio o retry.

    Args:
        db: Connessione database
        limit: Numero massimo

    Returns:
        Lista email da processare
    """
    query = """
        SELECT * FROM email_log
        WHERE stato_invio IN (%s, %s)
        ORDER BY created_at ASC
        LIMIT %s
    """
    rows = db.execute(query, [
        EmailStatus.PENDING, EmailStatus.RETRY, limit
    ]).fetchall()
    return [dict(row) for row in rows]
