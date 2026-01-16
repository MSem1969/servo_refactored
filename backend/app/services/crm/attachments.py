"""
Gestione allegati ticket CRM.
"""

import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional


# Directory allegati
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads', 'crm_allegati')

# Estensioni permesse
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx'}

# Dimensione massima (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def save_attachment(db, ticket_id: int, file_data: bytes, filename: str,
                    content_type: str, user_id: int) -> Dict[str, Any]:
    """
    Salva allegato su disco e registra nel database.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        file_data: Contenuto file
        filename: Nome file originale
        content_type: MIME type
        user_id: ID operatore

    Returns:
        Dict con risultato operazione
    """
    # Verifica estensione
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {
            'success': False,
            'error': f'Estensione non permessa. Ammesse: {", ".join(ALLOWED_EXTENSIONS)}'
        }

    # Verifica dimensione
    if len(file_data) > MAX_FILE_SIZE:
        return {
            'success': False,
            'error': f'File troppo grande. Max {MAX_FILE_SIZE // (1024*1024)} MB'
        }

    # Verifica ticket esiste
    ticket = db.execute(
        "SELECT id_ticket FROM crm_tickets WHERE id_ticket = %s",
        [ticket_id]
    ).fetchone()

    if not ticket:
        return {'success': False, 'error': 'Ticket non trovato'}

    # Genera nome univoco
    unique_name = f"{ticket_id}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    # Assicura directory esista
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    try:
        # Salva file
        with open(file_path, 'wb') as f:
            f.write(file_data)

        # Registra in DB
        query = """
            INSERT INTO crm_allegati (id_ticket, nome_file, nome_originale, mime_type, dimensione, path_file, id_operatore)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_allegato
        """
        result = db.execute(query, [
            ticket_id, unique_name, filename, content_type, len(file_data), file_path, user_id
        ]).fetchone()

        db.commit()

        return {
            'success': True,
            'id_allegato': result['id_allegato'],
            'nome_file': unique_name,
            'nome_originale': filename
        }

    except Exception as e:
        # Rimuovi file se errore DB
        if os.path.exists(file_path):
            os.remove(file_path)
        return {'success': False, 'error': str(e)}


def get_attachments(db, ticket_id: int) -> List[Dict]:
    """
    Lista allegati di un ticket.
    """
    query = """
        SELECT a.*, o.username as autore_nome
        FROM crm_allegati a
        LEFT JOIN operatori o ON a.id_operatore = o.id_operatore
        WHERE a.id_ticket = %s
        ORDER BY a.created_at ASC
    """
    rows = db.execute(query, [ticket_id]).fetchall()
    return [dict(row) for row in rows]


def get_attachment(db, allegato_id: int) -> Optional[Dict]:
    """
    Dettaglio singolo allegato.
    """
    query = "SELECT * FROM crm_allegati WHERE id_allegato = %s"
    row = db.execute(query, [allegato_id]).fetchone()
    return dict(row) if row else None


def delete_attachment(db, allegato_id: int, user_id: int, is_admin: bool = False) -> Dict[str, Any]:
    """
    Elimina allegato (solo proprietario o admin).
    """
    # Recupera allegato
    allegato = get_attachment(db, allegato_id)
    if not allegato:
        return {'success': False, 'error': 'Allegato non trovato'}

    # Verifica permessi
    if not is_admin and allegato['id_operatore'] != user_id:
        return {'success': False, 'error': 'Non autorizzato'}

    try:
        # Elimina file
        if os.path.exists(allegato['path_file']):
            os.remove(allegato['path_file'])

        # Elimina da DB
        db.execute("DELETE FROM crm_allegati WHERE id_allegato = %s", [allegato_id])
        db.commit()

        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': str(e)}
