"""
Notifiche CRM - Invio email automatiche per eventi ticket.
"""

from typing import Dict, Any, Optional, List

from ..email import EmailSender
from ..email.constants import EmailType


def get_admin_emails(db) -> List[str]:
    """
    Recupera lista email admin per notifiche da email_config.

    Returns:
        Lista di email admin (o lista vuota se non configurate)
    """
    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT admin_notifica_email
            FROM email_config
            WHERE id_config = 1
        """)
        row = cursor.fetchone()
        cursor.close()

        if row and row[0]:
            # Parse email separate da virgola
            emails = [e.strip() for e in row[0].split(',') if e.strip()]
            return emails
        return []
    except Exception:
        return []


def get_user_email_from_profile(db, id_operatore: int) -> Optional[str]:
    """
    v8.1: Recupera email corrente dal profilo utente.

    Args:
        db: Connessione database
        id_operatore: ID utente

    Returns:
        Email utente o None se non trovata/configurata
    """
    if not id_operatore:
        return None

    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT email
            FROM operatori
            WHERE id_operatore = %s AND attivo = TRUE
        """, (id_operatore,))
        row = cursor.fetchone()
        cursor.close()

        if row and row[0]:
            return row[0].strip()
        return None
    except Exception:
        return None


def resolve_notification_email(db, ticket_data: Dict[str, Any]) -> Optional[str]:
    """
    v8.1: Risolve email destinatario notifica in modo dinamico.

    Priorita:
    1. Email corrente dal profilo utente (se id_operatore presente)
    2. Fallback su email_notifica salvata nel ticket (per ticket anonimi)

    Args:
        db: Connessione database
        ticket_data: Dict con dati ticket (deve avere id_operatore o email_notifica)

    Returns:
        Email destinatario o None
    """
    # 1. Prova a recuperare email dal profilo utente
    id_operatore = ticket_data.get('id_operatore')
    if id_operatore:
        profile_email = get_user_email_from_profile(db, id_operatore)
        if profile_email:
            return profile_email

    # 2. Fallback su email_notifica (per ticket anonimi o utenti senza email)
    return ticket_data.get('email_notifica')


def get_priority_style(priorita: str) -> str:
    """Ritorna stile CSS in base alla priorita"""
    styles = {
        'bassa': 'background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px;',
        'normale': 'background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px;',
        'alta': 'background: #fee2e2; color: #dc2626; padding: 2px 8px; border-radius: 4px; font-weight: 600;'
    }
    return styles.get(priorita, styles['normale'])


def send_ticket_notification(db, event_type: str,
                            ticket_data: Dict[str, Any],
                            message_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Invia notifica email per evento ticket.

    Args:
        db: Connessione database
        event_type: Tipo evento ('ticket_creato', 'stato_cambiato', 'nuova_risposta')
        ticket_data: Dict con dati ticket (id, oggetto, email_notifica, etc.)
        message_content: Contenuto messaggio (per 'nuova_risposta')

    Returns:
        Dict con 'success', eventuale 'error'
    """
    # v8.1: Risolvi email dinamicamente dal profilo utente
    email_notifica = resolve_notification_email(db, ticket_data)
    if not email_notifica:
        return {'success': False, 'skipped': True, 'reason': 'Nessuna email notifica (profilo o ticket)'}

    # Verifica sender configurato
    if not EmailSender.is_configured(db):
        return {'success': False, 'skipped': True, 'reason': 'SMTP non configurato'}

    try:
        sender = EmailSender(db)

        # Prepara contesto template
        context = {
            'id': ticket_data.get('id_ticket') or ticket_data.get('ticket_id'),
            'oggetto': ticket_data.get('oggetto') or ticket_data.get('ticket_oggetto', ''),
            'categoria': ticket_data.get('categoria', ''),
            'pagina_origine': ticket_data.get('pagina_origine', 'N/D'),
            'stato': ticket_data.get('new_status') or ticket_data.get('stato', ''),
            'messaggio': message_content or ''
        }

        # Mappa evento -> template
        template_map = {
            'ticket_creato': 'ticket_creato',
            'stato_cambiato': 'stato_cambiato',
            'nuova_risposta': 'nuova_risposta',
            'ticket_chiuso': 'ticket_chiuso'
        }

        template_name = template_map.get(event_type)
        if not template_name:
            return {'success': False, 'error': f'Tipo evento sconosciuto: {event_type}'}

        # Invia email
        result = sender.send_from_template(
            template_name=template_name,
            context=context,
            to=email_notifica,
            ticket_id=context['id']
        )

        return result

    except Exception as e:
        return {'success': False, 'error': str(e)}


def notify_ticket_created(db, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Notifica creazione ticket.

    Invia due notifiche:
    1. All'utente (se ha email_notifica)
    2. Agli admin configurati (se admin_notifica_email configurato)
    """
    results = {'user_notification': None, 'admin_notification': None}

    # 1. Notifica all'utente
    user_result = send_ticket_notification(db, 'ticket_creato', ticket_data)
    results['user_notification'] = user_result

    # 2. Notifica agli admin
    admin_result = notify_admins_new_ticket(db, ticket_data)
    results['admin_notification'] = admin_result

    # Ritorna successo se almeno una notifica e andata a buon fine
    success = (
        (user_result.get('success') or user_result.get('skipped')) and
        (admin_result.get('success') or admin_result.get('skipped'))
    )

    return {'success': success, 'details': results}


def notify_admins_new_ticket(db, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invia notifica agli admin per nuovo ticket.

    Args:
        db: Connessione database
        ticket_data: Dict con dati ticket

    Returns:
        Dict con 'success', eventuale 'error'
    """
    admin_emails = get_admin_emails(db)
    if not admin_emails:
        return {'success': False, 'skipped': True, 'reason': 'Nessuna email admin configurata'}

    # Verifica sender configurato
    if not EmailSender.is_configured(db):
        return {'success': False, 'skipped': True, 'reason': 'SMTP non configurato'}

    try:
        sender = EmailSender(db)

        # Prepara contesto template admin
        priorita = ticket_data.get('priorita', 'normale')
        context = {
            'id': ticket_data.get('id_ticket') or ticket_data.get('ticket_id'),
            'oggetto': ticket_data.get('oggetto') or ticket_data.get('ticket_oggetto', ''),
            'categoria': ticket_data.get('categoria', ''),
            'priorita': priorita.upper() if priorita else 'NORMALE',
            'priorita_style': get_priority_style(priorita),
            'utente': ticket_data.get('username', 'N/D'),
            'pagina_origine': ticket_data.get('pagina_origine', 'N/D'),
            'contenuto': ticket_data.get('contenuto', '')[:500]  # Limita contenuto
        }

        results = []
        for admin_email in admin_emails:
            try:
                result = sender.send_from_template(
                    template_name='admin_nuovo_ticket',
                    context=context,
                    to=admin_email,
                    ticket_id=context['id']
                )
                results.append({'email': admin_email, **result})
            except Exception as e:
                results.append({'email': admin_email, 'success': False, 'error': str(e)})

        # Successo se almeno un admin ha ricevuto
        any_success = any(r.get('success') for r in results)
        return {'success': any_success, 'results': results}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def notify_status_changed(db, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
    """Notifica cambio stato"""
    return send_ticket_notification(db, 'stato_cambiato', ticket_data)


def notify_new_reply(db, ticket_data: Dict[str, Any],
                    message_content: str) -> Dict[str, Any]:
    """Notifica nuova risposta admin"""
    return send_ticket_notification(db, 'nuova_risposta', ticket_data, message_content)


def notify_ticket_closed(db, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
    """Notifica chiusura ticket"""
    return send_ticket_notification(db, 'ticket_chiuso', ticket_data)
