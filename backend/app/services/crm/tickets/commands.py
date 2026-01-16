"""
Commands tickets - Operazioni di scrittura.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..constants import TicketStatus, is_valid_transition


def create_ticket(db, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """
    Crea nuovo ticket con messaggio iniziale.

    Args:
        db: Connessione database
        data: Dict con campi ticket:
            - categoria (required)
            - oggetto (required)
            - contenuto (required) - messaggio iniziale
            - pagina_origine (optional)
            - pagina_dettaglio (optional)
            - email_notifica (optional)
            - priorita (optional, default 'normale')
        user_id: ID operatore che crea

    Returns:
        Dict con 'success', 'id_ticket', eventuale 'error'
    """
    # Validazione
    required = ['categoria', 'oggetto', 'contenuto']
    for field in required:
        if not data.get(field):
            return {'success': False, 'error': f'Campo richiesto: {field}'}

    try:
        # Inserisci ticket
        query = """
            INSERT INTO crm_tickets
            (id_operatore, categoria, oggetto, pagina_origine,
             pagina_dettaglio, email_notifica, priorita)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_ticket
        """
        params = [
            user_id,
            data['categoria'],
            data['oggetto'],
            data.get('pagina_origine'),
            data.get('pagina_dettaglio'),
            data.get('email_notifica'),
            data.get('priorita', 'normale')
        ]

        result = db.execute(query, params).fetchone()
        ticket_id = result['id_ticket']

        # Inserisci messaggio iniziale
        msg_query = """
            INSERT INTO crm_messaggi
            (id_ticket, id_operatore, contenuto, is_admin_reply)
            VALUES (%s, %s, %s, FALSE)
        """
        db.execute(msg_query, [ticket_id, user_id, data['contenuto']])

        db.commit()

        return {
            'success': True,
            'id_ticket': ticket_id,
            'message': f'Ticket #{ticket_id} creato'
        }

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}


def update_ticket_status(db, ticket_id: int, new_status: str,
                         admin_id: int) -> Dict[str, Any]:
    """
    Aggiorna stato ticket con validazione transizioni.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        new_status: Nuovo stato
        admin_id: ID admin che modifica

    Returns:
        Dict con 'success', 'old_status', 'new_status', eventuale 'error'
    """
    # Verifica stato corrente
    # v8.1: Aggiunto id_operatore per risoluzione email dinamica
    current = db.execute(
        "SELECT stato, oggetto, email_notifica, id_operatore FROM crm_tickets WHERE id_ticket = %s",
        [ticket_id]
    ).fetchone()

    if not current:
        return {'success': False, 'error': 'Ticket non trovato'}

    current_status = current['stato']

    # Stesso stato
    if current_status == new_status:
        return {
            'success': True,
            'old_status': current_status,
            'new_status': new_status,
            'message': 'Stato invariato'
        }

    # Valida transizione
    if not is_valid_transition(current_status, new_status):
        return {
            'success': False,
            'error': f'Transizione non valida: {current_status} -> {new_status}'
        }

    try:
        # Costruisci UPDATE
        query = """
            UPDATE crm_tickets
            SET stato = %s, updated_at = CURRENT_TIMESTAMP
        """
        params = [new_status]

        # Campi aggiuntivi per chiusura
        if new_status == TicketStatus.CHIUSO:
            query += ", closed_at = CURRENT_TIMESTAMP, closed_by = %s"
            params.append(admin_id)
        elif current_status == TicketStatus.CHIUSO:
            # Riapertura: resetta campi chiusura
            query += ", closed_at = NULL, closed_by = NULL"

        query += " WHERE id_ticket = %s"
        params.append(ticket_id)

        db.execute(query, params)
        db.commit()

        return {
            'success': True,
            'old_status': current_status,
            'new_status': new_status,
            'ticket_oggetto': current['oggetto'],
            'email_notifica': current['email_notifica'],
            'id_operatore': current['id_operatore']  # v8.1: per email dinamica
        }

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}


def update_ticket(db, ticket_id: int, data: Dict[str, Any],
                  user_id: int, is_admin: bool = False) -> Dict[str, Any]:
    """
    Aggiorna campi ticket.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        data: Dict con campi da aggiornare (priorita, email_notifica, etc.)
        user_id: ID utente che modifica
        is_admin: Se True, puo modificare qualsiasi ticket

    Returns:
        Dict con 'success', eventuale 'error'
    """
    # Verifica esistenza e permessi
    check_query = "SELECT id_operatore FROM crm_tickets WHERE id_ticket = %s"
    ticket = db.execute(check_query, [ticket_id]).fetchone()

    if not ticket:
        return {'success': False, 'error': 'Ticket non trovato'}

    if not is_admin and ticket['id_operatore'] != user_id:
        return {'success': False, 'error': 'Non autorizzato'}

    # Campi modificabili
    allowed_fields = ['priorita', 'email_notifica']
    if is_admin:
        allowed_fields.extend(['categoria', 'oggetto'])

    # Filtra solo campi permessi
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return {'success': True, 'message': 'Nessun campo da aggiornare'}

    try:
        fields = [f"{k} = %s" for k in updates.keys()]
        fields.append("updated_at = CURRENT_TIMESTAMP")

        values = list(updates.values()) + [ticket_id]

        query = f"UPDATE crm_tickets SET {', '.join(fields)} WHERE id_ticket = %s"
        db.execute(query, values)
        db.commit()

        return {'success': True, 'message': 'Ticket aggiornato'}

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}
