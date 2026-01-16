"""
Commands messaggi - Operazioni di scrittura.
"""

from typing import Dict, Any


def add_message(db, ticket_id: int, user_id: int,
                contenuto: str, is_admin: bool = False) -> Dict[str, Any]:
    """
    Aggiunge messaggio a un ticket.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        user_id: ID autore messaggio
        contenuto: Testo messaggio
        is_admin: Se True, marca come risposta admin

    Returns:
        Dict con 'success', 'id_messaggio', eventuale 'error'
    """
    if not contenuto or not contenuto.strip():
        return {'success': False, 'error': 'Contenuto messaggio richiesto'}

    # Verifica esistenza ticket
    ticket = db.execute(
        "SELECT id_ticket, id_operatore, email_notifica, oggetto FROM crm_tickets WHERE id_ticket = %s",
        [ticket_id]
    ).fetchone()

    if not ticket:
        return {'success': False, 'error': 'Ticket non trovato'}

    try:
        # Inserisci messaggio
        query = """
            INSERT INTO crm_messaggi
            (id_ticket, id_operatore, contenuto, is_admin_reply)
            VALUES (%s, %s, %s, %s)
            RETURNING id_messaggio
        """
        result = db.execute(query, [
            ticket_id, user_id, contenuto.strip(), is_admin
        ]).fetchone()

        # Aggiorna timestamp ticket
        db.execute(
            "UPDATE crm_tickets SET updated_at = CURRENT_TIMESTAMP WHERE id_ticket = %s",
            [ticket_id]
        )

        db.commit()

        return {
            'success': True,
            'id_messaggio': result['id_messaggio'],
            'ticket_id': ticket_id,
            'ticket_owner_id': ticket['id_operatore'],
            'id_operatore': ticket['id_operatore'],  # v8.1: per email dinamica dal profilo
            'email_notifica': ticket['email_notifica'],
            'ticket_oggetto': ticket['oggetto'],
            'is_admin_reply': is_admin
        }

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}


def delete_message(db, message_id: int, user_id: int,
                   is_admin: bool = False) -> Dict[str, Any]:
    """
    Elimina messaggio (solo admin o autore).

    Args:
        db: Connessione database
        message_id: ID messaggio
        user_id: ID utente che richiede eliminazione
        is_admin: Se True, puo eliminare qualsiasi messaggio

    Returns:
        Dict con 'success', eventuale 'error'
    """
    # Verifica permessi
    check_query = "SELECT id_operatore FROM crm_messaggi WHERE id_messaggio = %s"
    message = db.execute(check_query, [message_id]).fetchone()

    if not message:
        return {'success': False, 'error': 'Messaggio non trovato'}

    if not is_admin and message['id_operatore'] != user_id:
        return {'success': False, 'error': 'Non autorizzato'}

    try:
        db.execute("DELETE FROM crm_messaggi WHERE id_messaggio = %s", [message_id])
        db.commit()
        return {'success': True, 'message': 'Messaggio eliminato'}

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}
