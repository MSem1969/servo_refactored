# =============================================================================
# TO_EXTRACTOR v6.1 - ORDINI SERVICE
# =============================================================================
# Gestione ordini, dettagli, anomalie e conferma righe
# =============================================================================

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from ..database_pg import get_db, log_operation


from ..utils import calcola_q_totale  # v6.2: Shared utility


def _json_serializer(obj):
    """Converte tipi non serializzabili per JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, 'isoformat'):  # date, time
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# =============================================================================
# ORDINI - QUERY
# =============================================================================

def get_ordini(
    vendor: str = None,
    stato: str = None,
    lookup_method: str = None,
    data_da: str = None,
    data_a: str = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Ritorna lista ordini con filtri opzionali.
    
    Args:
        vendor: Filtra per vendor
        stato: Filtra per stato (ESTRATTO, VALIDATO, ANOMALIA, ESPORTATO)
        lookup_method: Filtra per metodo lookup
        data_da: Data ordine da (DD/MM/YYYY)
        data_a: Data ordine a (DD/MM/YYYY)
        limit: Max risultati
        offset: Offset paginazione
        
    Returns:
        Dict con 'ordini' (lista) e 'totale' (count)
    """
    db = get_db()
    
    # Costruisci query con filtri
    conditions = []
    params = []

    # Escludi ordini EVASO e ARCHIVIATO dalla lista (a meno che non sia esplicitamente richiesto)
    if stato:
        conditions.append("stato = ?")
        params.append(stato)
    else:
        # Default: escludi EVASO e ARCHIVIATO
        conditions.append("stato NOT IN ('EVASO', 'ARCHIVIATO')")

    if vendor:
        conditions.append("vendor = ?")
        params.append(vendor)
    
    if lookup_method:
        conditions.append("lookup_method = ?")
        params.append(lookup_method)
    
    if data_da:
        conditions.append("data_ordine >= ?")
        params.append(data_da)
    
    if data_a:
        conditions.append("data_ordine <= ?")
        params.append(data_a)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Count totale
    count_query = f"SELECT COUNT(*) FROM V_ORDINI_COMPLETI WHERE {where_clause}"
    totale = db.execute(count_query, params).fetchone()[0]
    
    # Query con paginazione
    query = f"""
        SELECT * FROM V_ORDINI_COMPLETI 
        WHERE {where_clause}
        ORDER BY id_testata DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    rows = db.execute(query, params).fetchall()
    
    return {
        'ordini': [dict(row) for row in rows],
        'totale': totale,
        'limit': limit,
        'offset': offset
    }


def get_ordine_detail(id_testata: int) -> Optional[Dict[str, Any]]:
    """
    Ritorna dettaglio completo ordine con righe e anomalie.
    """
    db = get_db()
    
    # Testata
    ordine = db.execute(
        "SELECT * FROM V_ORDINI_COMPLETI WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()
    
    if not ordine:
        return None
    
    result = dict(ordine)
    
    # Righe dettaglio
    righe = db.execute("""
        SELECT * FROM ORDINI_DETTAGLIO 
        WHERE id_testata = ?
        ORDER BY n_riga
    """, (id_testata,)).fetchall()
    result['righe'] = [dict(r) for r in righe]
    
    # Anomalie
    anomalie = db.execute("""
        SELECT * FROM ANOMALIE 
        WHERE id_testata = ?
        ORDER BY data_rilevazione DESC
    """, (id_testata,)).fetchall()
    result['anomalie'] = [dict(a) for a in anomalie]
    
    # Info acquisizione
    acquisizione = db.execute("""
        SELECT * FROM ACQUISIZIONI 
        WHERE id_acquisizione = ?
    """, (result.get('id_acquisizione'),)).fetchone()
    if acquisizione:
        result['acquisizione'] = dict(acquisizione)
    
    return result


def get_ordine_righe(id_testata: int) -> List[Dict]:
    """
    Ritorna solo le righe dettaglio di un ordine.
    Esclude i CHILD_ESPOSITORE (visibili solo in gestione anomalie).
    """
    db = get_db()
    rows = db.execute("""
        SELECT * FROM ORDINI_DETTAGLIO
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
        ORDER BY n_riga
    """, (id_testata,)).fetchall()
    return [dict(r) for r in rows]


# =============================================================================
# ORDINI - MODIFICA
# =============================================================================

def update_ordine_stato(id_testata: int, nuovo_stato: str) -> bool:
    """
    Aggiorna stato ordine e sincronizza stato_riga delle righe dettaglio.

    Stati validi: ESTRATTO, CONFERMATO, ANOMALIA, PARZ_EVASO, EVASO, ARCHIVIATO

    v6.2.5: Quando l'ordine diventa EVASO o ARCHIVIATO, aggiorna anche
    lo stato_riga di tutte le righe dettaglio per mantenerle sincronizzate.
    """
    stati_validi = ['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO']
    if nuovo_stato not in stati_validi:
        return False

    db = get_db()

    # Aggiorna stato testata
    db.execute(
        "UPDATE ORDINI_TESTATA SET stato = ? WHERE id_testata = ?",
        (nuovo_stato, id_testata)
    )

    # v6.2.5: Sincronizza stato_riga delle righe dettaglio
    if nuovo_stato in ('EVASO', 'ARCHIVIATO'):
        # Quando l'ordine è EVASO/ARCHIVIATO, tutte le righe devono essere EVASO
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'EVASO'
            WHERE id_testata = ?
              AND stato_riga NOT IN ('EVASO')
        """, (id_testata,))
    elif nuovo_stato == 'PARZ_EVASO':
        # Per PARZ_EVASO, correggi righe con stato inconsistente
        # Righe completamente evase (q_evasa >= q_totale) → EVASO
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'EVASO'
            WHERE id_testata = ?
              AND COALESCE(q_evasa, 0) >= (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
              AND (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0)) > 0
              AND stato_riga != 'EVASO'
        """, (id_testata,))
        # Righe parzialmente evase → PARZIALE
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'PARZIALE'
            WHERE id_testata = ?
              AND COALESCE(q_evasa, 0) > 0
              AND COALESCE(q_evasa, 0) < (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
              AND stato_riga NOT IN ('PARZIALE', 'EVASO')
        """, (id_testata,))
    elif nuovo_stato == 'ESTRATTO':
        # Quando si torna a ESTRATTO, correggi righe con stato 'PENDING' o altri stati invalidi
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'ESTRATTO'
            WHERE id_testata = ?
              AND stato_riga NOT IN ('ESTRATTO', 'CONFERMATO', 'PARZIALE', 'EVASO', 'IN_SUPERVISIONE', 'SUPERVISIONATO')
        """, (id_testata,))

    db.commit()

    log_operation('UPDATE_STATO', 'ORDINI_TESTATA', id_testata,
                 f"Stato cambiato in {nuovo_stato}")
    return True


def delete_ordine(id_testata: int) -> bool:
    """
    Elimina un ordine e tutti i dati correlati.
    
    Returns:
        True se eliminato
    """
    db = get_db()
    
    # Verifica esistenza
    ordine = db.execute(
        "SELECT numero_ordine_vendor FROM ORDINI_TESTATA WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()
    
    if not ordine:
        return False
    
    # Elimina anomalie
    db.execute("DELETE FROM ANOMALIE WHERE id_testata = ?", (id_testata,))
    
    # Elimina dettagli
    db.execute("DELETE FROM ORDINI_DETTAGLIO WHERE id_testata = ?", (id_testata,))
    
    # Elimina esportazioni dettaglio
    db.execute("DELETE FROM ESPORTAZIONI_DETTAGLIO WHERE id_testata = ?", (id_testata,))
    
    # Elimina testata
    db.execute("DELETE FROM ORDINI_TESTATA WHERE id_testata = ?", (id_testata,))
    
    db.commit()
    
    log_operation('DELETE', 'ORDINI_TESTATA', id_testata,
                 f"Eliminato ordine {ordine['numero_ordine_vendor']}")
    return True


# =============================================================================
# ANOMALIE
# =============================================================================

def get_anomalie(
    tipo: str = None,
    livello: str = None,
    stato: str = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Ritorna lista anomalie con filtri.
    
    Args:
        tipo: LOOKUP, ESPOSITORE, CHILD, NO_AIC, PIVA_MULTIPUNTO, 
              VALIDAZIONE, DUPLICATO_PDF, DUPLICATO_ORDINE, ALTRO
        livello: INFO, ATTENZIONE, ERRORE, CRITICO
        stato: APERTA, IN_GESTIONE, RISOLTA, IGNORATA
    """
    db = get_db()
    
    conditions = []
    params = []
    
    if tipo:
        conditions.append("tipo_anomalia = ?")
        params.append(tipo)
    
    if livello:
        conditions.append("livello = ?")
        params.append(livello)
    
    if stato:
        conditions.append("an.stato = ?")
        params.append(stato)
    else:
        # Default: solo aperte
        conditions.append("an.stato IN ('APERTA', 'IN_GESTIONE')")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Count
    count_query = f"""
        SELECT COUNT(*) FROM ANOMALIE an
        LEFT JOIN ORDINI_TESTATA ot ON an.id_testata = ot.id_testata
        WHERE {where_clause}
    """
    totale = db.execute(count_query, params).fetchone()[0]
    
    # Query
    query = f"""
        SELECT 
            an.*,
            v.codice_vendor as vendor,
            ot.numero_ordine_vendor as numero_ordine,
            a.nome_file_originale as pdf_file
        FROM ANOMALIE an
        LEFT JOIN ORDINI_TESTATA ot ON an.id_testata = ot.id_testata
        LEFT JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        LEFT JOIN ACQUISIZIONI a ON COALESCE(an.id_acquisizione, ot.id_acquisizione) = a.id_acquisizione
        WHERE {where_clause}
        ORDER BY 
            CASE an.livello 
                WHEN 'CRITICO' THEN 1 
                WHEN 'ERRORE' THEN 2 
                WHEN 'ATTENZIONE' THEN 3 
                ELSE 4 
            END,
            an.data_rilevazione DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    rows = db.execute(query, params).fetchall()
    
    return {
        'anomalie': [dict(row) for row in rows],
        'totale': totale,
        'limit': limit,
        'offset': offset
    }


def get_anomalie_by_ordine(id_testata: int) -> List[Dict]:
    """Ritorna anomalie di un ordine specifico."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM ANOMALIE
        WHERE id_testata = ?
        ORDER BY data_rilevazione DESC
    """, (id_testata,)).fetchall()
    return [dict(row) for row in rows]


def _sblocca_ordine_se_anomalie_risolte(id_testata: int) -> bool:
    """
    v6.2.4: Sblocca ordine quando tutte le anomalie sono risolte/ignorate.

    Quando tutte le anomalie di un ordine sono RISOLTA o IGNORATA,
    E non ci sono supervisioni pending, l'ordine passa da
    ANOMALIA/PENDING_REVIEW a ESTRATTO.

    Returns:
        True se l'ordine è stato sbloccato, False altrimenti
    """
    db = get_db()

    # Conta anomalie ancora aperte (APERTA o IN_GESTIONE)
    anomalie_aperte = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = ? AND stato IN ('APERTA', 'IN_GESTIONE')
    """, (id_testata,)).fetchone()

    # Conta supervisioni ancora pending
    supervisioni_pending = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_espositore
        WHERE id_testata = ? AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    anomalie_cnt = anomalie_aperte['cnt'] if anomalie_aperte else 0
    supervisioni_cnt = supervisioni_pending['cnt'] if supervisioni_pending else 0

    if anomalie_cnt == 0 and supervisioni_cnt == 0:
        # Nessuna anomalia aperta e nessuna supervisione pending
        result = db.execute("""
            UPDATE ordini_testata
            SET stato = 'ESTRATTO'
            WHERE id_testata = ? AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
            RETURNING id_testata
        """, (id_testata,)).fetchone()

        db.commit()

        if result:
            log_operation(
                'SBLOCCO_ORDINE',
                'ORDINI_TESTATA',
                id_testata,
                'Ordine sbloccato - tutte le anomalie risolte'
            )
            return True

    return False


def update_anomalia_stato(
    id_anomalia: int,
    nuovo_stato: str,
    note: str = None
) -> bool:
    """
    Aggiorna stato anomalia.

    Stati validi: APERTA, IN_GESTIONE, RISOLTA, IGNORATA

    v6.2: Quando un'anomalia ESPOSITORE viene RISOLTA, registra
    il pattern ML per apprendimento automatico.
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
    if nuovo_stato not in stati_validi:
        return False

    db = get_db()

    # Recupera info anomalia prima di aggiornarla
    anomalia = db.execute(
        "SELECT tipo_anomalia, id_testata FROM anomalie WHERE id_anomalia = ?",
        (id_anomalia,)
    ).fetchone()

    if nuovo_stato in ('RISOLTA', 'IGNORATA'):
        db.execute("""
            UPDATE anomalie
            SET stato = ?,
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = ?
            WHERE id_anomalia = ?
        """, (nuovo_stato, note, id_anomalia))

        # v6.2.4: Risolvi anche la supervisione collegata (se esiste)
        sup_stato = 'APPROVED' if nuovo_stato == 'RISOLTA' else 'REJECTED'
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = ?,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || 'Risolto da anomalia'
            WHERE id_anomalia = ? AND stato = 'PENDING'
        """, (sup_stato, id_anomalia))
    else:
        db.execute(
            "UPDATE anomalie SET stato = ? WHERE id_anomalia = ?",
            (nuovo_stato, id_anomalia)
        )

    db.commit()

    # v6.2: Se anomalia ESPOSITORE risolta, registra pattern ML
    if anomalia and nuovo_stato == 'RISOLTA':
        tipo = anomalia['tipo_anomalia']
        id_testata = anomalia['id_testata']

        if tipo == 'ESPOSITORE' and id_testata:
            try:
                from .ml_pattern_matching import registra_pattern_da_anomalia_risolta
                registra_pattern_da_anomalia_risolta(id_anomalia, id_testata)
            except Exception as e:
                # Non bloccare la risoluzione per errori ML
                log_operation(
                    'ERRORE_ML_PATTERN',
                    'ANOMALIE',
                    id_anomalia,
                    f"Errore registrazione pattern ML: {str(e)}"
                )

    # v6.2.4: Sblocca ordine se tutte le anomalie sono risolte/ignorate
    if anomalia and nuovo_stato in ('RISOLTA', 'IGNORATA'):
        id_testata = anomalia['id_testata']
        if id_testata:
            _sblocca_ordine_se_anomalie_risolte(id_testata)

    return True


def create_anomalia(
    id_testata: int = None,
    id_dettaglio: int = None,
    id_acquisizione: int = None,
    tipo: str = 'ALTRO',
    livello: str = 'ATTENZIONE',
    descrizione: str = '',
    valore_anomalo: str = None
) -> int:
    """
    Crea nuova anomalia manualmente.
    
    Returns:
        ID anomalia creata
    """
    db = get_db()
    
    cursor = db.execute("""
        INSERT INTO ANOMALIE
        (id_testata, id_dettaglio, id_acquisizione, tipo_anomalia,
         livello, descrizione, valore_anomalo, stato)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'APERTA')
    """, (id_testata, id_dettaglio, id_acquisizione, tipo,
          livello, descrizione, valore_anomalo))

    db.commit()
    return cursor.lastrowid


# =============================================================================
# DASHBOARD & STATISTICHE
# =============================================================================

def get_dashboard_stats() -> Dict[str, Any]:
    """
    Ritorna statistiche per dashboard.
    """
    db = get_db()
    
    # Ordini per stato
    ordini_per_stato = {}
    rows = db.execute("""
        SELECT stato, COUNT(*) as count 
        FROM ORDINI_TESTATA 
        GROUP BY stato
    """).fetchall()
    for row in rows:
        ordini_per_stato[row['stato']] = row['count']
    
    # Ordini per vendor
    ordini_per_vendor = {}
    rows = db.execute("""
        SELECT v.codice_vendor, COUNT(*) as count 
        FROM ORDINI_TESTATA ot
        JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        GROUP BY v.codice_vendor
    """).fetchall()
    for row in rows:
        ordini_per_vendor[row['codice_vendor']] = row['count']
    
    # Anomalie aperte per tipo
    anomalie_per_tipo = {}
    rows = db.execute("""
        SELECT tipo_anomalia, COUNT(*) as count 
        FROM ANOMALIE 
        WHERE stato IN ('APERTA', 'IN_GESTIONE')
        GROUP BY tipo_anomalia
    """).fetchall()
    for row in rows:
        anomalie_per_tipo[row['tipo_anomalia']] = row['count']
    
    # Lookup stats
    lookup_stats = {}
    rows = db.execute("""
        SELECT lookup_method, COUNT(*) as count 
        FROM ORDINI_TESTATA 
        GROUP BY lookup_method
    """).fetchall()
    for row in rows:
        lookup_stats[row['lookup_method'] or 'NULL'] = row['count']
    
    # Ultimi 7 giorni (PostgreSQL syntax)
    ordini_ultimi_7gg = db.execute("""
        SELECT data_estrazione::date as giorno, COUNT(*) as count
        FROM ORDINI_TESTATA
        WHERE data_estrazione >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY data_estrazione::date
        ORDER BY giorno
    """).fetchall()
    
    return {
        'totali': {
            'ordini': db.execute("SELECT COUNT(*) FROM ORDINI_TESTATA").fetchone()[0],
            'righe': db.execute("SELECT COUNT(*) FROM ORDINI_DETTAGLIO").fetchone()[0],
            'anomalie_aperte': db.execute(
                "SELECT COUNT(*) FROM ANOMALIE WHERE stato IN ('APERTA', 'IN_GESTIONE')"
            ).fetchone()[0],
            'pdf_elaborati': db.execute(
                "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ELABORATO'"
            ).fetchone()[0],
        },
        'ordini_per_stato': ordini_per_stato,
        'ordini_per_vendor': ordini_per_vendor,
        'anomalie_per_tipo': anomalie_per_tipo,
        'lookup_stats': lookup_stats,
        'ordini_ultimi_7gg': [dict(r) for r in ordini_ultimi_7gg],
        'timestamp': datetime.now().isoformat()
    }


def get_ordini_recenti(limit: int = 10) -> List[Dict]:
    """Ritorna ordini più recenti."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM V_ORDINI_COMPLETI
        ORDER BY id_testata DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_anomalie_critiche(limit: int = 10) -> List[Dict]:
    """Ritorna anomalie critiche/errore aperte."""
    db = get_db()
    rows = db.execute("""
        SELECT 
            an.*,
            v.codice_vendor as vendor,
            ot.numero_ordine_vendor as numero_ordine
        FROM ANOMALIE an
        LEFT JOIN ORDINI_TESTATA ot ON an.id_testata = ot.id_testata
        LEFT JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        WHERE an.stato IN ('APERTA', 'IN_GESTIONE')
        AND an.livello IN ('CRITICO', 'ERRORE')
        ORDER BY 
            CASE an.livello WHEN 'CRITICO' THEN 1 ELSE 2 END,
            an.data_rilevazione DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# v6.1: CONFERMA RIGHE E SUPERVISIONE
# =============================================================================

def conferma_singola_riga(
    id_testata: int,
    id_dettaglio: int,
    operatore: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conferma una singola riga per inserimento in tracciato.
    
    LOGICA v6.1.2:
    1. Verifica appartenenza riga a ordine
    2. Se richiede_supervisione=1 e stato_riga != 'SUPERVISIONATO' → blocca
    3. Altrimenti → conferma e imposta q_residua = q_venduta corrente
    """
    db = get_db()
    
    riga = db.execute("""
        SELECT id_dettaglio, id_testata, stato_riga, richiede_supervisione, 
               id_supervisione, tipo_riga, is_espositore, q_venduta, q_originale
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()
    
    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}
    
    # Permetti ri-conferma per righe PARZIALMENTE_ESP (per esportare il residuo)
    if riga['stato_riga'] in ('CONFERMATO', 'IN_TRACCIATO', 'ESPORTATO'):
        return {'success': False, 'error': 'Riga già confermata o esportata'}
    
    if riga['richiede_supervisione'] and riga['stato_riga'] != 'SUPERVISIONATO':
        return {
            'success': False,
            'richiede_supervisione': True,
            'id_supervisione': riga['id_supervisione'],
            'tipo_anomalia': 'ESPOSITORE' if riga['is_espositore'] else 'ALTRO'
        }
    
    now = datetime.now().isoformat()

    # v6.2: Usa funzione condivisa per calcolo quantità
    q_totale = calcola_q_totale(riga)

    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'CONFERMATO',
            confermato_da = ?,
            data_conferma = ?,
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || ?,
            q_residua = ?
        WHERE id_dettaglio = ?
    """, (operatore, now, note or '', q_totale, id_dettaglio))

    _aggiorna_contatori_ordine(id_testata)
    db.commit()
    return {'success': True, 'q_residua': q_totale}


def conferma_ordine_completo(
    id_testata: int,
    operatore: str,
    forza_conferma: bool = False,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conferma tutte le righe confermabili di un ordine.

    v6.1.2: Gestisce nuovi stati esportazione parziale
    - ESPORTATO → già completate, skip
    - PARZIALMENTE_ESP → ri-conferma per esportare residuo
    """
    print(f"🔵 conferma_ordine_completo CHIAMATA: id_testata={id_testata}, operatore={operatore}")
    db = get_db()
    now = datetime.now().isoformat()
    
    righe = db.execute("""
        SELECT id_dettaglio, stato_riga, richiede_supervisione, tipo_riga,
               q_venduta, q_sconto_merce, q_omaggio, q_originale, q_residua
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
        ORDER BY n_riga
    """, (id_testata,)).fetchall()

    confermate = 0
    bloccate = []
    gia_confermate = 0
    gia_esportate = 0
    
    for riga in righe:
        # Righe già completamente esportate → skip
        if riga['stato_riga'] == 'ESPORTATO':
            gia_esportate += 1
            continue
        
        # Righe già confermate → skip
        if riga['stato_riga'] in ('CONFERMATO', 'IN_TRACCIATO'):
            gia_confermate += 1
            continue
        
        # Righe che richiedono supervisione non completata → blocca
        if riga['richiede_supervisione'] and riga['stato_riga'] != 'SUPERVISIONATO':
            bloccate.append({
                'id_dettaglio': riga['id_dettaglio'],
                'tipo_riga': riga['tipo_riga'],
                'motivo': 'Richiede supervisione'
            })
            continue
        
        # Righe parzialmente esportate → ri-conferma con q_residua
        # Righe ESTRATTO o SUPERVISIONATO → conferma normale
        # v6.2: Usa funzione condivisa per calcolo quantità
        q_totale = calcola_q_totale(riga)
        if riga['stato_riga'] == 'PARZIALMENTE_ESP':
            q_da_esportare = riga['q_residua'] or q_totale
        else:
            q_da_esportare = q_totale
        
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'CONFERMATO',
                confermato_da = ?,
                data_conferma = ?,
                note_supervisione = COALESCE(note_supervisione || ' | ', '') || ?,
                q_residua = ?
            WHERE id_dettaglio = ?
        """, (operatore, now, note or 'Conferma batch', q_da_esportare, riga['id_dettaglio']))
        confermate += 1
    
    _aggiorna_contatori_ordine(id_testata)
    db.commit()
    
    return {
        'confermate': confermate,
        'bloccate': bloccate,
        'gia_confermate': gia_confermate,
        'gia_esportate': gia_esportate,
        'ordine_completo': len(bloccate) == 0 and confermate + gia_confermate + gia_esportate == len(righe)
    }


def get_riga_dettaglio(id_testata: int, id_dettaglio: int) -> Optional[Dict[str, Any]]:
    """Recupera dettaglio completo riga con info supervisione."""
    db = get_db()
    
    row = db.execute("""
        SELECT od.*,
               se.id_supervisione,
               se.stato AS stato_supervisione,
               se.codice_anomalia,
               se.pezzi_attesi,
               se.pezzi_trovati,
               se.note AS note_supervisore
        FROM ORDINI_DETTAGLIO od
        LEFT JOIN SUPERVISIONE_ESPOSITORE se ON od.id_supervisione = se.id_supervisione
        WHERE od.id_dettaglio = ? AND od.id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()
    
    if not row:
        return None
    
    result = dict(row)
    
    if result.get('espositore_metadata'):
        try:
            result['espositore_metadata_parsed'] = json.loads(result['espositore_metadata'])
        except:
            pass
    
    if result.get('valori_originali'):
        try:
            result['valori_originali_parsed'] = json.loads(result['valori_originali'])
        except:
            pass
    
    return result


def modifica_riga_dettaglio(
    id_testata: int,
    id_dettaglio: int,
    modifiche: Dict[str, Any],
    operatore: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Modifica valori di una riga, salvando backup originale."""
    CAMPI_MODIFICABILI = {
        'codice_aic', 'descrizione',
        'q_venduta', 'q_sconto_merce', 'q_omaggio',
        'prezzo_netto', 'prezzo_pubblico',
        'sconto_1', 'sconto_2', 'sconto_3', 'sconto_4',
        'note_allestimento'
    }
    
    campi_invalidi = set(modifiche.keys()) - CAMPI_MODIFICABILI
    if campi_invalidi:
        return {'success': False, 'error': f'Campi non modificabili: {campi_invalidi}'}
    
    db = get_db()
    now = datetime.now().isoformat()
    
    riga = db.execute("""
        SELECT * FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()
    
    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}
    
    riga_dict = dict(riga)
    
    if not riga_dict.get('valori_originali'):
        valori_originali = {k: riga_dict.get(k) for k in CAMPI_MODIFICABILI}
        valori_originali['_timestamp_backup'] = now
        valori_originali['_operatore_backup'] = operatore
    else:
        valori_originali = None
    
    set_clauses = []
    params = []
    for campo, valore in modifiche.items():
        set_clauses.append(f"{campo} = ?")
        params.append(valore)
    
    set_clauses.append("modificato_manualmente = TRUE")
    set_clauses.append("data_conferma = ?")
    params.append(now)
    
    if valori_originali:
        set_clauses.append("valori_originali = ?")
        params.append(json.dumps(valori_originali, ensure_ascii=False, default=_json_serializer))
    
    if note:
        set_clauses.append("note_supervisione = COALESCE(note_supervisione || ' | ', '') || ?")
        params.append(f"[{operatore}] {note}")
    
    params.extend([id_dettaglio, id_testata])
    
    db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET {', '.join(set_clauses)}
        WHERE id_dettaglio = ? AND id_testata = ?
    """, params)
    
    db.commit()
    return {'success': True}


def crea_o_recupera_supervisione(
    id_testata: int,
    id_dettaglio: int,
    operatore: str
) -> Dict[str, Any]:
    """Crea supervisione per riga o recupera esistente."""
    db = get_db()
    
    riga = db.execute("""
        SELECT od.*, ot.numero_ordine_vendor, v.codice_vendor
        FROM ORDINI_DETTAGLIO od
        JOIN ORDINI_TESTATA ot ON od.id_testata = ot.id_testata
        JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        WHERE od.id_dettaglio = ? AND od.id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()
    
    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}
    
    if riga['id_supervisione']:
        return {
            'id_supervisione': riga['id_supervisione'],
            'creata_nuova': False
        }
    
    metadata = {}
    if riga['espositore_metadata']:
        try:
            metadata = json.loads(riga['espositore_metadata'])
        except:
            pass
    
    codice_anomalia = 'ESP-A01' if riga['is_espositore'] else 'ALTRO'
    pattern_sig = f"{riga['codice_vendor']}_{codice_anomalia}_{riga['codice_originale']}"
    
    cursor = db.execute("""
        INSERT INTO SUPERVISIONE_ESPOSITORE (
            id_testata, codice_anomalia, codice_espositore, descrizione_espositore,
            pezzi_attesi, pezzi_trovati, valore_calcolato, pattern_signature,
            stato, operatore
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
    """, (
        id_testata,
        codice_anomalia,
        riga['codice_originale'],
        riga['descrizione'],
        metadata.get('pezzi_attesi', 0),
        metadata.get('pezzi_trovati', 0),
        metadata.get('valore_netto_child', 0),
        pattern_sig,
        operatore
    ))
    
    id_supervisione = cursor.lastrowid
    
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET id_supervisione = ?,
            stato_riga = 'IN_SUPERVISIONE'
        WHERE id_dettaglio = ?
    """, (id_supervisione, id_dettaglio))
    
    db.commit()
    
    return {
        'id_supervisione': id_supervisione,
        'creata_nuova': True
    }


def get_stato_righe_ordine(id_testata: int) -> Dict[str, int]:
    """
    Ritorna conteggio righe per stato.
    
    v6.1.2: Aggiunge stati esportazione parziale
    """
    db = get_db()
    
    stats = db.execute("""
        SELECT
            COUNT(*) AS totale,
            SUM(CASE WHEN stato_riga = 'ESTRATTO' THEN 1 ELSE 0 END) AS estratto,
            SUM(CASE WHEN stato_riga = 'IN_SUPERVISIONE' THEN 1 ELSE 0 END) AS in_supervisione,
            SUM(CASE WHEN stato_riga = 'SUPERVISIONATO' THEN 1 ELSE 0 END) AS supervisionato,
            SUM(CASE WHEN stato_riga = 'CONFERMATO' THEN 1 ELSE 0 END) AS confermato,
            SUM(CASE WHEN stato_riga = 'IN_TRACCIATO' THEN 1 ELSE 0 END) AS in_tracciato,
            SUM(CASE WHEN stato_riga = 'ESPORTATO' THEN 1 ELSE 0 END) AS esportato,
            SUM(CASE WHEN stato_riga IN ('PARZIALMENTE_ESP', 'PARZIALE') THEN 1 ELSE 0 END) AS parzialmente_esp,
            SUM(CASE WHEN richiede_supervisione = TRUE THEN 1 ELSE 0 END) AS richiede_supervisione
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
    """, (id_testata,)).fetchone()
    
    return dict(stats) if stats else {
        'totale': 0, 'estratto': 0, 'in_supervisione': 0,
        'supervisionato': 0, 'confermato': 0, 'in_tracciato': 0,
        'esportato': 0, 'parzialmente_esp': 0, 'richiede_supervisione': 0
    }


# =============================================================================
# v6.2: EVASIONI PARZIALI
# =============================================================================

def registra_evasione(
    id_testata: int,
    id_dettaglio: int,
    q_da_evadere: int,
    operatore: str
) -> Dict[str, Any]:
    """
    Imposta quantità DA EVADERE per una riga (per il prossimo tracciato).

    v6.2.1: NUOVA LOGICA
    - q_da_evadere: quantità che verrà esportata nel PROSSIMO tracciato
    - q_evasa: cumulativo già esportato (aggiornato SOLO dopo generazione tracciato)
    - q_residua: rimanente da evadere = q_totale - q_evasa

    Args:
        id_testata: ID ordine
        id_dettaglio: ID riga
        q_da_evadere: Quantità da evadere nel prossimo tracciato
        operatore: Nome operatore

    Returns:
        Dict con success, q_da_evadere, q_evasa (cumulativo), q_residua
    """
    db = get_db()

    # Recupera riga con tutte le quantità
    riga = db.execute("""
        SELECT id_dettaglio, id_testata, q_venduta, q_sconto_merce, q_omaggio, q_evasa, q_da_evadere
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    # Quantità totale = venduta + sconto merce + omaggio
    q_venduta = riga['q_venduta'] or 0
    q_sconto_merce = riga['q_sconto_merce'] or 0
    q_omaggio = riga['q_omaggio'] or 0
    q_totale = q_venduta + q_sconto_merce + q_omaggio

    # Cumulativo già esportato
    q_evasa_cumulativo = riga['q_evasa'] or 0

    # Residuo disponibile = totale - già evaso
    q_residuo_disponibile = q_totale - q_evasa_cumulativo

    # v6.2.1: Se già completamente evaso, non permettere modifiche
    if q_evasa_cumulativo >= q_totale and q_totale > 0:
        return {
            'success': False,
            'error': f'Riga già completamente evasa (evaso: {q_evasa_cumulativo}, totale: {q_totale}). Non modificabile.'
        }

    # Validazione
    if q_da_evadere < 0:
        return {'success': False, 'error': 'Quantità da evadere non può essere negativa'}

    if q_da_evadere > q_residuo_disponibile:
        return {
            'success': False,
            'error': f'Quantità da evadere ({q_da_evadere}) supera il residuo disponibile ({q_residuo_disponibile}). '
                     f'Già evaso: {q_evasa_cumulativo}, Totale: {q_totale}'
        }

    # Calcola q_residua dopo questa evasione (sarà effettivo dopo generazione tracciato)
    q_residua_dopo = q_residuo_disponibile - q_da_evadere

    # v6.2.1: Determina stato riga
    # - Se q_da_evadere > 0 → CONFERMATO (pronto per tracciato)
    # - Se q_da_evadere = 0 e q_evasa > 0 → PARZIALE (già parzialmente evaso)
    # - Se q_da_evadere = 0 e q_evasa = 0 → ESTRATTO (pending)
    if q_da_evadere > 0:
        nuovo_stato = 'CONFERMATO'
    elif q_evasa_cumulativo > 0:
        nuovo_stato = 'PARZIALE'
    else:
        nuovo_stato = 'ESTRATTO'

    # Aggiorna q_da_evadere e stato_riga
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET q_da_evadere = ?,
            stato_riga = ?
        WHERE id_dettaglio = ?
    """, (q_da_evadere, nuovo_stato, id_dettaglio))

    # Aggiorna contatori righe
    _aggiorna_contatori_ordine(id_testata)

    db.commit()

    log_operation('IMPOSTA_DA_EVADERE', 'ORDINI_DETTAGLIO', id_dettaglio,
                 f"q_da_evadere={q_da_evadere}, stato={nuovo_stato}, q_evasa_cumulativo={q_evasa_cumulativo}, q_residuo={q_residua_dopo}",
                 operatore=operatore)

    return {
        'success': True,
        'id_dettaglio': id_dettaglio,
        'q_da_evadere': q_da_evadere,
        'q_evasa': q_evasa_cumulativo,  # Cumulativo (non cambia finché non generi tracciato)
        'q_residua': q_residua_dopo,     # Residuo dopo questa evasione
        'q_totale': q_totale,
        'stato_riga': nuovo_stato,
        'operatore': operatore
    }


def _aggiorna_contatori_ordine(id_testata: int):
    """
    Aggiorna contatori righe nella testata ordine E lo stato dell'ordine.

    v6.2.1: Aggiorna anche stato testata in base a righe:
    - Se almeno una riga ha q_da_evadere > 0 → CONFERMATO
    - Se tutte le righe sono EVASO → EVASO
    - Se alcune righe sono EVASO e altre no → PARZ_EVASO
    - Altrimenti → ESTRATTO
    """
    db = get_db()
    stats = get_stato_righe_ordine(id_testata)

    print(f"📊 _aggiorna_contatori_ordine({id_testata}): stats={stats}")

    # Righe confermate = CONFERMATO + IN_TRACCIATO + ESPORTATO + PARZIALMENTE_ESP
    righe_confermate = (
        stats.get('confermato', 0) +
        stats.get('in_tracciato', 0) +
        stats.get('esportato', 0) +
        stats.get('parzialmente_esp', 0)
    )

    print(f"📊 righe_confermate calcolate: {righe_confermate}")

    # v6.2.1: Determina stato testata in base a righe
    totale = stats.get('totale', 0)
    esportate = stats.get('esportato', 0)
    confermate = stats.get('confermato', 0)
    parziali = stats.get('parzialmente_esp', 0)

    # Conta righe con q_da_evadere > 0
    righe_con_da_evadere = db.execute("""
        SELECT COUNT(*) FROM ORDINI_DETTAGLIO
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_da_evadere, 0) > 0
    """, (id_testata,)).fetchone()[0]

    # Determina stato ordine
    if totale > 0 and esportate == totale:
        # Tutte le righe sono state completamente evase
        nuovo_stato = 'EVASO'
    elif esportate > 0 or parziali > 0:
        # Alcune righe evase (totalmente o parzialmente)
        nuovo_stato = 'PARZ_EVASO'
    elif righe_con_da_evadere > 0 or confermate > 0:
        # Almeno una riga ha quantità da evadere impostata
        nuovo_stato = 'CONFERMATO'
    else:
        # Nessuna riga confermata
        nuovo_stato = 'ESTRATTO'

    print(f"📊 nuovo_stato testata: {nuovo_stato} (esportate={esportate}, parziali={parziali}, confermate={confermate}, righe_con_da_evadere={righe_con_da_evadere})")

    db.execute("""
        UPDATE ORDINI_TESTATA
        SET righe_totali = ?,
            righe_confermate = ?,
            righe_in_supervisione = ?,
            stato = ?,
            data_ultimo_aggiornamento = CURRENT_TIMESTAMP
        WHERE id_testata = ?
    """, (
        stats['totale'],
        righe_confermate,
        stats['in_supervisione'],
        nuovo_stato,
        id_testata
    ))
    print(f"📊 UPDATE eseguito per id_testata={id_testata}, stato={nuovo_stato}")
    # Nota: commit gestito dalla funzione chiamante


# =============================================================================
# v6.2.1: RIPRISTINO CONFERME
# =============================================================================

def ripristina_riga(
    id_testata: int,
    id_dettaglio: int,
    operatore: str
) -> Dict[str, Any]:
    """
    Ripristina una riga allo stato pre-conferma.

    Resetta q_da_evadere a 0.
    Lo stato dipende da q_evasa:
    - Se q_evasa >= q_totale → EVASO (non ripristinabile)
    - Se q_evasa > 0 → PARZIALE
    - Se q_evasa = 0 → ESTRATTO

    NON modifica q_evasa (quantità già esportate in tracciati precedenti).

    Args:
        id_testata: ID ordine
        id_dettaglio: ID riga
        operatore: Nome operatore

    Returns:
        Dict con success e dettagli
    """
    db = get_db()

    # Recupera riga con quantità totale
    riga = db.execute("""
        SELECT id_dettaglio, stato_riga, q_da_evadere, q_evasa,
               q_venduta, q_sconto_merce, q_omaggio
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    # Calcola totale e evaso
    q_totale = (riga['q_venduta'] or 0) + (riga['q_sconto_merce'] or 0) + (riga['q_omaggio'] or 0)
    q_evasa = riga['q_evasa'] or 0

    # Non permettere ripristino se già completamente evasa
    if q_evasa >= q_totale and q_totale > 0:
        return {'success': False, 'error': f'Riga già completamente evasa ({q_evasa}/{q_totale}), non ripristinabile'}

    # Determina nuovo stato in base a q_evasa
    # - Se q_evasa > 0 → PARZIALE (ha già esportazioni precedenti)
    # - Se q_evasa = 0 → ESTRATTO (nessuna esportazione)
    if q_evasa > 0:
        nuovo_stato = 'PARZIALE'
    else:
        nuovo_stato = 'ESTRATTO'

    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET q_da_evadere = 0,
            stato_riga = ?
        WHERE id_dettaglio = ?
    """, (nuovo_stato, id_dettaglio))

    # Aggiorna contatori ordine (e stato testata)
    _aggiorna_contatori_ordine(id_testata)

    db.commit()

    log_operation('RIPRISTINA_RIGA', 'ORDINI_DETTAGLIO', id_dettaglio,
                 f"Ripristinato da {riga['stato_riga']} a {nuovo_stato}, q_da_evadere reset a 0",
                 operatore=operatore)

    return {
        'success': True,
        'id_dettaglio': id_dettaglio,
        'stato_precedente': riga['stato_riga'],
        'stato_nuovo': nuovo_stato,
        'q_da_evadere_precedente': riga['q_da_evadere'] or 0,
        'operatore': operatore
    }


def ripristina_ordine(
    id_testata: int,
    operatore: str
) -> Dict[str, Any]:
    """
    Ripristina TUTTE le righe confermabili di un ordine allo stato pre-conferma.

    Resetta q_da_evadere a 0 per tutte le righe con stato CONFERMATO.
    NON tocca righe già completamente EVASO (q_evasa >= q_totale).

    Stati dopo ripristino:
    - Se q_evasa > 0 ma < q_totale → PARZIALE
    - Se q_evasa = 0 → ESTRATTO

    Args:
        id_testata: ID ordine
        operatore: Nome operatore

    Returns:
        Dict con success e statistiche
    """
    db = get_db()

    # Conta righe da ripristinare (CONFERMATO e non completamente evase)
    righe_da_ripristinare = db.execute("""
        SELECT COUNT(*) FROM ORDINI_DETTAGLIO
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND stato_riga = 'CONFERMATO'
          AND COALESCE(q_evasa, 0) < (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
    """, (id_testata,)).fetchone()[0]

    if righe_da_ripristinare == 0:
        return {
            'success': True,
            'message': 'Nessuna riga da ripristinare',
            'righe_ripristinate': 0
        }

    # Ripristina tutte le righe CONFERMATO (escluse quelle completamente evase)
    # Se hanno q_evasa > 0 → PARZIALE, altrimenti → ESTRATTO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET q_da_evadere = 0,
            stato_riga = CASE
                WHEN COALESCE(q_evasa, 0) > 0 THEN 'PARZIALE'
                ELSE 'ESTRATTO'
            END
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND stato_riga = 'CONFERMATO'
          AND COALESCE(q_evasa, 0) < (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
    """, (id_testata,))

    # Aggiorna contatori ordine (e stato testata)
    _aggiorna_contatori_ordine(id_testata)

    db.commit()

    log_operation('RIPRISTINA_ORDINE', 'ORDINI_TESTATA', id_testata,
                 f"Ripristinate {righe_da_ripristinare} righe",
                 operatore=operatore)

    return {
        'success': True,
        'righe_ripristinate': righe_da_ripristinare,
        'operatore': operatore
    }


def fix_stati_righe(id_testata: Optional[int] = None) -> Dict[str, Any]:
    """
    Corregge gli stati delle righe in base a q_evasa, q_totale e stato ordine.

    v6.2.5: Aggiunta sincronizzazione con stato ordine parent

    Logica:
    - Ordine EVASO/ARCHIVIATO → tutte le righe EVASO
    - Se q_evasa >= q_totale → EVASO
    - Se q_evasa > 0 ma < q_totale e q_da_evadere = 0 → PARZIALE
    - Se q_evasa = 0 e q_da_evadere = 0 → ESTRATTO
    - Se q_da_evadere > 0 → CONFERMATO (non toccare)
    - Stati invalidi (PENDING, ecc.) → corretti in base alla logica sopra

    Args:
        id_testata: Se specificato, corregge solo le righe di questo ordine.
                   Se None, corregge tutte le righe.

    Returns:
        Dict con statistiche delle correzioni
    """
    db = get_db()

    where_clause = "WHERE id_testata = ?" if id_testata else ""
    params = (id_testata,) if id_testata else ()

    # 0. v6.2.5: Sincronizza righe con ordini EVASO/ARCHIVIATO
    # Righe di ordini EVASO/ARCHIVIATO che hanno stato_riga errato → EVASO
    righe_sync_evaso = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'EVASO'
        WHERE id_testata IN (
            SELECT id_testata FROM ORDINI_TESTATA
            WHERE stato IN ('EVASO', 'ARCHIVIATO')
            {f"AND id_testata = {id_testata}" if id_testata else ""}
        )
        AND stato_riga != 'EVASO'
    """).rowcount

    # 1. Righe completamente evase → EVASO
    righe_evaso = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'EVASO'
        {where_clause}
        {"AND" if where_clause else "WHERE"} (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_evasa, 0) >= (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
          AND (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0)) > 0
          AND stato_riga != 'EVASO'
    """, params).rowcount

    # 2. Righe parzialmente evase senza q_da_evadere → PARZIALE
    righe_parziale = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'PARZIALE'
        {where_clause}
        {"AND" if where_clause else "WHERE"} (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_evasa, 0) > 0
          AND COALESCE(q_evasa, 0) < (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
          AND COALESCE(q_da_evadere, 0) = 0
          AND stato_riga NOT IN ('PARZIALE', 'CONFERMATO', 'EVASO')
    """, params).rowcount

    # 3. Righe non evase senza q_da_evadere → ESTRATTO
    # Include correzione stati invalidi come 'PENDING'
    righe_estratto = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'ESTRATTO'
        {where_clause}
        {"AND" if where_clause else "WHERE"} (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_evasa, 0) = 0
          AND COALESCE(q_da_evadere, 0) = 0
          AND stato_riga NOT IN ('ESTRATTO', 'IN_SUPERVISIONE', 'SUPERVISIONATO', 'CONFERMATO', 'EVASO', 'PARZIALE')
    """, params).rowcount

    db.commit()

    # Aggiorna contatori ordini interessati
    if id_testata:
        _aggiorna_contatori_ordine(id_testata)
    else:
        # Aggiorna tutti gli ordini con righe modificate
        ordini = db.execute("""
            SELECT DISTINCT id_testata FROM ORDINI_DETTAGLIO
        """).fetchall()
        for o in ordini:
            _aggiorna_contatori_ordine(o['id_testata'])

    db.commit()

    totale = righe_sync_evaso + righe_evaso + righe_parziale + righe_estratto

    log_operation('FIX_STATI_RIGHE', 'ORDINI_DETTAGLIO', id_testata or 0,
                 f"Corretti {totale} stati: SYNC_EVASO={righe_sync_evaso}, EVASO={righe_evaso}, PARZIALE={righe_parziale}, ESTRATTO={righe_estratto}",
                 operatore='SYSTEM')

    return {
        'success': True,
        'totale_corretti': totale,
        'sync_evaso': righe_sync_evaso,
        'evaso': righe_evaso,
        'parziale': righe_parziale,
        'estratto': righe_estratto,
        'id_testata': id_testata
    }
