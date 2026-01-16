"""
Query messaggi - Operazioni di lettura.
"""

from typing import List, Dict, Any, Optional


def get_messages(db, ticket_id: int,
                 user_id: Optional[int] = None,
                 is_admin: bool = False) -> List[Dict]:
    """
    Lista messaggi di un ticket.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        user_id: ID utente (per verifica permessi)
        is_admin: Se True, puo vedere qualsiasi ticket

    Returns:
        Lista di messaggi ordinati per data
    """
    # Verifica permessi accesso ticket
    if not is_admin and user_id:
        check = db.execute(
            "SELECT 1 FROM crm_tickets WHERE id_ticket = %s AND id_operatore = %s",
            [ticket_id, user_id]
        ).fetchone()
        if not check:
            return []

    query = """
        SELECT m.*,
               o.username as autore_nome,
               o.nome as autore_nome_completo
        FROM crm_messaggi m
        LEFT JOIN operatori o ON m.id_operatore = o.id_operatore
        WHERE m.id_ticket = %s
        ORDER BY m.created_at ASC
    """

    rows = db.execute(query, [ticket_id]).fetchall()
    return [dict(row) for row in rows]


def get_last_message(db, ticket_id: int) -> Optional[Dict]:
    """
    Ultimo messaggio di un ticket.

    Args:
        db: Connessione database
        ticket_id: ID ticket

    Returns:
        Dict messaggio o None
    """
    query = """
        SELECT m.*,
               o.username as autore_nome
        FROM crm_messaggi m
        LEFT JOIN operatori o ON m.id_operatore = o.id_operatore
        WHERE m.id_ticket = %s
        ORDER BY m.created_at DESC
        LIMIT 1
    """
    row = db.execute(query, [ticket_id]).fetchone()
    return dict(row) if row else None


def count_unread_admin_replies(db, ticket_id: int,
                               last_read_at: Optional[str] = None) -> int:
    """
    Conta risposte admin non lette.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        last_read_at: Timestamp ultima lettura utente

    Returns:
        Numero messaggi non letti
    """
    query = """
        SELECT COUNT(*) as count
        FROM crm_messaggi
        WHERE id_ticket = %s AND is_admin_reply = TRUE
    """
    params = [ticket_id]

    if last_read_at:
        query += " AND created_at > %s"
        params.append(last_read_at)

    row = db.execute(query, params).fetchone()
    return row['count'] if row else 0
