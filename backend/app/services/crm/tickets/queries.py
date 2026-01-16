"""
Query tickets - Operazioni di lettura.
"""

from typing import List, Dict, Any, Optional


def get_tickets(db, filters: Optional[Dict[str, Any]] = None,
                user_id: Optional[int] = None,
                is_admin: bool = False,
                limit: int = 100,
                offset: int = 0) -> List[Dict]:
    """
    Lista ticket con filtri.

    Args:
        db: Connessione database
        filters: Dict con filtri (stato, categoria, search, priorita)
        user_id: ID utente (per filtrare propri ticket)
        is_admin: Se True, vede tutti i ticket
        limit: Numero massimo risultati
        offset: Offset paginazione

    Returns:
        Lista di ticket
    """
    query = """
        SELECT t.*,
               o.username as operatore_nome,
               o.nome as operatore_nome_completo,
               (SELECT COUNT(*) FROM crm_messaggi m WHERE m.id_ticket = t.id_ticket) as num_messaggi,
               (SELECT MAX(created_at) FROM crm_messaggi m WHERE m.id_ticket = t.id_ticket) as ultimo_messaggio
        FROM crm_tickets t
        LEFT JOIN operatori o ON t.id_operatore = o.id_operatore
        WHERE 1=1
    """
    params = []

    # Filtro per utente (se non admin)
    if not is_admin and user_id:
        query += " AND t.id_operatore = %s"
        params.append(user_id)

    # Filtri opzionali
    if filters:
        if filters.get('stato'):
            query += " AND t.stato = %s"
            params.append(filters['stato'])

        if filters.get('categoria'):
            query += " AND t.categoria = %s"
            params.append(filters['categoria'])

        if filters.get('priorita'):
            query += " AND t.priorita = %s"
            params.append(filters['priorita'])

        if filters.get('search'):
            search = filters['search']
            query += " AND (t.oggetto ILIKE %s OR t.id_ticket::text = %s)"
            params.extend([f"%{search}%", search])

        if filters.get('data_da'):
            query += " AND t.created_at >= %s"
            params.append(filters['data_da'])

        if filters.get('data_a'):
            query += " AND t.created_at <= %s"
            params.append(filters['data_a'])

    # Ordinamento: priorita alta prima, poi data
    query += """
        ORDER BY
            CASE t.priorita
                WHEN 'alta' THEN 3
                WHEN 'normale' THEN 2
                WHEN 'bassa' THEN 1
            END DESC,
            t.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_ticket_detail(db, ticket_id: int,
                      user_id: Optional[int] = None,
                      is_admin: bool = False) -> Optional[Dict]:
    """
    Dettaglio singolo ticket con messaggi.

    Args:
        db: Connessione database
        ticket_id: ID ticket
        user_id: ID utente (per verifica permessi)
        is_admin: Se True, puo vedere qualsiasi ticket

    Returns:
        Dict con ticket e messaggi, None se non trovato/non autorizzato
    """
    # Query ticket
    query = """
        SELECT t.*,
               o.username as operatore_nome,
               o.nome as operatore_nome_completo,
               o.email as operatore_email,
               c.username as closed_by_nome
        FROM crm_tickets t
        LEFT JOIN operatori o ON t.id_operatore = o.id_operatore
        LEFT JOIN operatori c ON t.closed_by = c.id_operatore
        WHERE t.id_ticket = %s
    """
    params = [ticket_id]

    # Verifica permessi
    if not is_admin and user_id:
        query += " AND t.id_operatore = %s"
        params.append(user_id)

    row = db.execute(query, params).fetchone()
    if not row:
        return None

    ticket = dict(row)

    # Carica messaggi
    msg_query = """
        SELECT m.*,
               o.username as autore_nome,
               o.nome as autore_nome_completo
        FROM crm_messaggi m
        LEFT JOIN operatori o ON m.id_operatore = o.id_operatore
        WHERE m.id_ticket = %s
        ORDER BY m.created_at ASC
    """
    messages = db.execute(msg_query, [ticket_id]).fetchall()
    ticket['messaggi'] = [dict(m) for m in messages]

    return ticket


def get_ticket_stats(db, user_id: Optional[int] = None,
                     is_admin: bool = False) -> Dict[str, Any]:
    """
    Statistiche ticket per dashboard.

    Args:
        db: Connessione database
        user_id: ID utente (filtra per utente se non admin)
        is_admin: Se True, statistiche globali

    Returns:
        Dict con conteggi per stato e categoria
    """
    where = "WHERE 1=1"
    params = []

    if not is_admin and user_id:
        where += " AND id_operatore = %s"
        params.append(user_id)

    # Conteggi per stato
    query = f"""
        SELECT
            COUNT(*) FILTER (WHERE stato = 'aperto') as aperti,
            COUNT(*) FILTER (WHERE stato = 'in_lavorazione') as in_lavorazione,
            COUNT(*) FILTER (WHERE stato = 'chiuso') as chiusi,
            COUNT(*) as totale,
            COUNT(*) FILTER (WHERE priorita = 'alta' AND stato != 'chiuso') as alta_priorita
        FROM crm_tickets
        {where}
    """
    row = db.execute(query, params).fetchone()

    stats = dict(row) if row else {
        'aperti': 0,
        'in_lavorazione': 0,
        'chiusi': 0,
        'totale': 0,
        'alta_priorita': 0
    }

    # Conteggi per categoria
    cat_query = f"""
        SELECT categoria, COUNT(*) as count
        FROM crm_tickets
        {where}
        GROUP BY categoria
    """
    cat_rows = db.execute(cat_query, params).fetchall()
    stats['per_categoria'] = {row['categoria']: row['count'] for row in cat_rows}

    return stats
