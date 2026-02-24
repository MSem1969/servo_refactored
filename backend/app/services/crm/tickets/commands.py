"""
Commands tickets - Operazioni di scrittura.

v11.4: Aggiunta funzione crea_ticket_sistema per notifiche automatiche.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..constants import TicketStatus, is_valid_transition

# ID utente sistema per ticket automatici (admin)
SYSTEM_USER_ID = 1


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


# =============================================================================
# v11.4: TICKET SISTEMA PER NOTIFICHE AUTOMATICHE
# =============================================================================

def crea_ticket_sistema(
    db,
    tipo_alert: str,
    oggetto: str,
    contenuto: str,
    priorita: str = 'normale',
    contesto: Optional[Dict[str, Any]] = None,
    file_content: Optional[bytes] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crea un ticket di sistema per notifiche automatiche ad admin/supervisore.

    v11.4: Funzione centralizzata per alert di sistema via CRM.

    Args:
        db: Connessione database
        tipo_alert: Tipo di alert (es. 'IMPORT', 'ERRORE', 'MONITORAGGIO')
        oggetto: Oggetto del ticket (verrà prefissato con [SISTEMA])
        contenuto: Contenuto dettagliato dell'alert
        priorita: 'bassa', 'normale', 'alta' (default: normale)
        contesto: Dict opzionale con:
            - pagina_origine: Pagina che ha generato l'alert
            - pagina_dettaglio: Dettaglio specifico (es. ID ordine)
            - dati_extra: Dict con dati aggiuntivi da includere nel contenuto

    Returns:
        Dict con:
            - success: bool
            - id_ticket: int (se success)
            - error: str (se fallito)

    Esempi di utilizzo:
        # Alert per errore import anagrafica
        crea_ticket_sistema(db, 'IMPORT',
            'Errore import anagrafica clienti',
            'Fallito import file clienti.csv: formato non valido',
            priorita='alta',
            contesto={'pagina_origine': 'anagrafica'})

        # Alert per nuovo ordine da monitoraggio email
        crea_ticket_sistema(db, 'MONITORAGGIO',
            'Nuovo ordine ricevuto via email',
            'Ordine #12345 ricevuto da fornitore@example.com',
            contesto={'pagina_dettaglio': 'Ordine #12345'})
    """
    try:
        # Costruisci oggetto con prefisso sistema
        oggetto_completo = f"[SISTEMA - {tipo_alert}] {oggetto}"

        # Costruisci contenuto con eventuali dati extra
        contenuto_completo = contenuto
        if contesto and contesto.get('dati_extra'):
            contenuto_completo += "\n\n--- Dettagli Tecnici ---\n"
            for k, v in contesto['dati_extra'].items():
                contenuto_completo += f"• {k}: {v}\n"

        # Dati ticket
        ticket_data = {
            'categoria': 'assistenza',
            'oggetto': oggetto_completo,
            'contenuto': contenuto_completo,
            'priorita': priorita,
            'pagina_origine': contesto.get('pagina_origine') if contesto else None,
            'pagina_dettaglio': contesto.get('pagina_dettaglio') if contesto else None
        }

        # Crea ticket usando funzione esistente
        result = create_ticket(db, ticket_data, SYSTEM_USER_ID)

        if result.get('success'):
            print(f"✅ Ticket sistema #{result['id_ticket']} creato: {oggetto_completo}")

            # Salva allegato PDF nel ticket CRM (visibile nel frontend)
            if file_content and filename:
                try:
                    from ..attachments import save_attachment
                    mime_type = 'application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream'
                    attach_result = save_attachment(
                        db, result['id_ticket'], file_content, filename,
                        mime_type, SYSTEM_USER_ID
                    )
                    if attach_result.get('success'):
                        print(f"📎 Allegato '{filename}' salvato nel ticket #{result['id_ticket']}")
                    else:
                        print(f"⚠️ Errore salvataggio allegato: {attach_result.get('error')}")
                except Exception as e:
                    print(f"⚠️ Errore salvataggio allegato nel ticket: {e}")

            # Notifica admin via email
            try:
                from ..notifications import notify_ticket_created

                ticket_data = {
                    'id_ticket': result['id_ticket'],
                    'id_operatore': SYSTEM_USER_ID,
                    'oggetto': oggetto_completo,
                    'categoria': 'assistenza',
                    'priorita': priorita,
                    'pagina_origine': contesto.get('pagina_origine') if contesto else None,
                    'contenuto': contenuto_completo,
                    'username': 'SISTEMA'
                }
                email_attachments = None
                if file_content and filename:
                    email_attachments = [{'filename': filename, 'content': file_content, 'mime_type': 'application/pdf'}]

                notify_result = notify_ticket_created(db, ticket_data, attachments=email_attachments)
                details = notify_result.get('details', {})
                user_ok = details.get('user_notification', {}).get('success')
                admin_ok = details.get('admin_notification', {}).get('success')
                user_skip = details.get('user_notification', {}).get('skipped')
                admin_skip = details.get('admin_notification', {}).get('skipped')

                if user_ok or admin_ok:
                    parts = []
                    if user_ok: parts.append('utente')
                    if admin_ok: parts.append('admin')
                    print(f"📧 Email inviata a {', '.join(parts)} per ticket #{result['id_ticket']}")
                if user_skip:
                    print(f"⏭️ Email utente skippata: {details.get('user_notification', {}).get('reason', 'N/D')}")
                if admin_skip:
                    print(f"⏭️ Email admin skippata: {details.get('admin_notification', {}).get('reason', 'N/D')}")
            except Exception as e:
                print(f"⚠️ Errore invio notifica email: {e}")
        else:
            print(f"⚠️ Errore creazione ticket sistema: {result.get('error')}")

        return result

    except Exception as e:
        print(f"❌ Eccezione in crea_ticket_sistema: {e}")
        return {'success': False, 'error': str(e)}
