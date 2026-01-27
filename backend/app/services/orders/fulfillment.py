# =============================================================================
# SERV.O v11.3 - ORDERS FULFILLMENT
# =============================================================================
# Funzioni per conferma righe, evasioni parziali, supervisione
# Estratto da ordini.py per modularità
# v11.3: Validazione data consegna (max 30 giorni)
# =============================================================================

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from ...database_pg import get_db, log_operation
from ...utils import calcola_q_totale
from .queries import get_stato_righe_ordine


# =============================================================================
# VALIDAZIONE DATA CONSEGNA (v11.3)
# =============================================================================
# Le righe con data_consegna > 30 giorni da oggi NON possono essere confermate.
# Questo serve a evitare l'export di ordini con date di consegna troppo lontane.
# =============================================================================

MAX_GIORNI_CONSEGNA = 30  # Massimo giorni di anticipo per conferma


def _parse_data_consegna(data_val) -> Optional[date]:
    """
    Converte data_consegna_riga in oggetto date.
    Accetta: datetime.date, datetime.datetime, stringa DD/MM/YYYY, YYYY-MM-DD.
    """
    if not data_val:
        return None

    if isinstance(data_val, date) and not isinstance(data_val, datetime):
        return data_val

    if isinstance(data_val, datetime):
        return data_val.date()

    # Stringa
    data_str = str(data_val).strip()
    if not data_str:
        return None

    # DD/MM/YYYY
    try:
        return datetime.strptime(data_str, '%d/%m/%Y').date()
    except ValueError:
        pass

    # YYYY-MM-DD (ISO)
    try:
        return datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        pass

    return None


def _verifica_data_consegna(data_consegna_riga) -> Dict[str, Any]:
    """
    Verifica se la data consegna è entro 30 giorni da oggi.

    Returns:
        {
            'valida': bool,
            'data_consegna': date o None,
            'data_limite': date,
            'giorni_mancanti': int (se non valida)
        }
    """
    oggi = date.today()
    data_limite = oggi + timedelta(days=MAX_GIORNI_CONSEGNA)

    data_consegna = _parse_data_consegna(data_consegna_riga)

    if data_consegna is None:
        # Se non c'è data consegna, considera valida (usa oggi come default)
        return {
            'valida': True,
            'data_consegna': None,
            'data_limite': data_limite,
            'giorni_mancanti': 0
        }

    if data_consegna <= data_limite:
        return {
            'valida': True,
            'data_consegna': data_consegna,
            'data_limite': data_limite,
            'giorni_mancanti': 0
        }

    # Data troppo lontana
    giorni_mancanti = (data_consegna - data_limite).days
    return {
        'valida': False,
        'data_consegna': data_consegna,
        'data_limite': data_limite,
        'giorni_mancanti': giorni_mancanti
    }


# =============================================================================
# CONFERMA RIGHE
# =============================================================================

def conferma_singola_riga(
    id_testata: int,
    id_dettaglio: int,
    operatore: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conferma una singola riga per inserimento in tracciato.

    v11.3: Blocca conferma se data_consegna_riga > 30 giorni da oggi.
    """
    db = get_db()

    riga = db.execute("""
        SELECT id_dettaglio, id_testata, stato_riga, richiede_supervisione,
               id_supervisione, tipo_riga, is_espositore, q_venduta, q_originale,
               q_sconto_merce, q_omaggio, data_consegna_riga
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    # Stati finali - non modificabili
    if riga['stato_riga'] == 'ARCHIVIATO':
        return {'success': False, 'error': 'Riga archiviata - non modificabile'}

    if riga['stato_riga'] == 'EVASO':
        return {'success': False, 'error': 'Riga già evasa - non modificabile'}

    if riga['stato_riga'] in ('CONFERMATO', 'IN_TRACCIATO', 'ESPORTATO'):
        return {'success': False, 'error': 'Riga già confermata o esportata'}

    # v11.3: Verifica data consegna (max 30 giorni da oggi)
    verifica_data = _verifica_data_consegna(riga.get('data_consegna_riga'))
    if not verifica_data['valida']:
        data_consegna = verifica_data['data_consegna']
        data_limite = verifica_data['data_limite']
        giorni_mancanti = verifica_data['giorni_mancanti']
        return {
            'success': False,
            'error': f'Data consegna {data_consegna.strftime("%d/%m/%Y")} supera il limite di {MAX_GIORNI_CONSEGNA} giorni. '
                     f'Confermabile dal {(data_consegna - timedelta(days=MAX_GIORNI_CONSEGNA)).strftime("%d/%m/%Y")}',
            'data_consegna_bloccante': True,
            'data_consegna': data_consegna.isoformat(),
            'data_limite': data_limite.isoformat(),
            'giorni_mancanti': giorni_mancanti
        }

    if riga['richiede_supervisione'] and riga['stato_riga'] != 'SUPERVISIONATO':
        return {
            'success': False,
            'richiede_supervisione': True,
            'id_supervisione': riga['id_supervisione'],
            'tipo_anomalia': 'ESPOSITORE' if riga['is_espositore'] else 'ALTRO'
        }

    now = datetime.now().isoformat()
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

    # Log operazione per tracking produttività
    log_operation('CONFERMA_RIGA', 'ORDINI_DETTAGLIO', id_dettaglio,
                 f"Riga confermata per tracciato. Ordine: {id_testata}",
                 operatore=operatore)

    return {'success': True, 'q_residua': q_totale}


def conferma_ordine_completo(
    id_testata: int,
    operatore: str,
    forza_conferma: bool = False,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conferma tutte le righe confermabili di un ordine.

    v11.3: Esclude righe con data_consegna_riga > 30 giorni da oggi.
    Queste righe restano in stato ESTRATTO/PARZIALE e possono essere confermate
    solo quando la data consegna rientra nei 30 giorni.
    """
    db = get_db()
    now = datetime.now().isoformat()

    righe = db.execute("""
        SELECT id_dettaglio, stato_riga, richiede_supervisione, tipo_riga,
               q_venduta, q_sconto_merce, q_omaggio, q_originale, q_residua,
               data_consegna_riga
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
        ORDER BY n_riga
    """, (id_testata,)).fetchall()

    confermate = 0
    bloccate = []
    bloccate_data_consegna = []  # v11.3: righe bloccate per data consegna
    gia_confermate = 0
    gia_esportate = 0

    for riga in righe:
        # Stati finali - non possono essere modificati
        if riga['stato_riga'] == 'ARCHIVIATO':
            continue

        if riga['stato_riga'] == 'EVASO':
            continue

        if riga['stato_riga'] == 'ESPORTATO':
            gia_esportate += 1
            continue

        if riga['stato_riga'] in ('CONFERMATO', 'IN_TRACCIATO'):
            gia_confermate += 1
            continue

        # v11.3: Verifica data consegna (max 30 giorni da oggi)
        verifica_data = _verifica_data_consegna(riga.get('data_consegna_riga'))
        if not verifica_data['valida']:
            data_consegna = verifica_data['data_consegna']
            bloccate_data_consegna.append({
                'id_dettaglio': riga['id_dettaglio'],
                'tipo_riga': riga['tipo_riga'],
                'motivo': f'Data consegna {data_consegna.strftime("%d/%m/%Y")} oltre {MAX_GIORNI_CONSEGNA} giorni',
                'data_consegna': data_consegna.isoformat(),
                'confermabile_dal': (data_consegna - timedelta(days=MAX_GIORNI_CONSEGNA)).strftime('%d/%m/%Y')
            })
            continue

        if riga['richiede_supervisione'] and riga['stato_riga'] != 'SUPERVISIONATO':
            bloccate.append({
                'id_dettaglio': riga['id_dettaglio'],
                'tipo_riga': riga['tipo_riga'],
                'motivo': 'Richiede supervisione'
            })
            continue

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
                q_residua = ?,
                q_da_evadere = ?
            WHERE id_dettaglio = ?
        """, (operatore, now, note or 'Conferma batch', q_da_esportare, q_da_esportare, riga['id_dettaglio']))
        confermate += 1

    _aggiorna_contatori_ordine(id_testata)
    db.commit()

    # Log operazione per tracking produttività (solo se righe confermate)
    if confermate > 0:
        log_operation('CONFERMA_ORDINE', 'ORDINI_TESTATA', id_testata,
                     f"Confermate {confermate} righe",
                     operatore=operatore)

    # v11.3: Combina bloccate (supervisione) e bloccate_data_consegna
    tutte_bloccate = bloccate + bloccate_data_consegna

    return {
        'confermate': confermate,
        'bloccate': tutte_bloccate,
        'bloccate_supervisione': bloccate,
        'bloccate_data_consegna': bloccate_data_consegna,
        'gia_confermate': gia_confermate,
        'gia_esportate': gia_esportate,
        'ordine_completo': len(tutte_bloccate) == 0 and confermate + gia_confermate + gia_esportate == len(righe)
    }


# =============================================================================
# EVASIONI PARZIALI
# =============================================================================

def registra_evasione(
    id_testata: int,
    id_dettaglio: int,
    q_da_evadere: int,
    operatore: str
) -> Dict[str, Any]:
    """Imposta quantità DA EVADERE per una riga (per il prossimo tracciato)."""
    db = get_db()

    riga = db.execute("""
        SELECT id_dettaglio, id_testata, q_venduta, q_sconto_merce, q_omaggio, q_evasa, q_da_evadere, stato_riga
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    # v9.1: Protezione righe ARCHIVIATO - stato finale immutabile
    if riga['stato_riga'] == 'ARCHIVIATO':
        return {'success': False, 'error': 'Riga archiviata - non modificabile'}

    q_venduta = riga['q_venduta'] or 0
    q_sconto_merce = riga['q_sconto_merce'] or 0
    q_omaggio = riga['q_omaggio'] or 0
    q_totale = q_venduta + q_sconto_merce + q_omaggio
    q_evasa_cumulativo = riga['q_evasa'] or 0
    q_residuo_disponibile = q_totale - q_evasa_cumulativo

    if q_evasa_cumulativo >= q_totale and q_totale > 0:
        return {
            'success': False,
            'error': f'Riga già completamente evasa (evaso: {q_evasa_cumulativo}, totale: {q_totale}). Non modificabile.'
        }

    if q_da_evadere < 0:
        return {'success': False, 'error': 'Quantità da evadere non può essere negativa'}

    if q_da_evadere > q_residuo_disponibile:
        return {
            'success': False,
            'error': f'Quantità da evadere ({q_da_evadere}) supera il residuo disponibile ({q_residuo_disponibile}). '
                     f'Già evaso: {q_evasa_cumulativo}, Totale: {q_totale}'
        }

    q_residua_dopo = q_residuo_disponibile - q_da_evadere

    if q_da_evadere > 0:
        nuovo_stato = 'CONFERMATO'
    elif q_evasa_cumulativo > 0:
        nuovo_stato = 'PARZIALE'
    else:
        nuovo_stato = 'ESTRATTO'

    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET q_da_evadere = ?,
            stato_riga = ?
        WHERE id_dettaglio = ?
    """, (q_da_evadere, nuovo_stato, id_dettaglio))

    _aggiorna_contatori_ordine(id_testata)
    db.commit()

    log_operation('REGISTRA_EVASIONE', 'ORDINI_DETTAGLIO', id_dettaglio,
                 f"q_da_evadere={q_da_evadere}, stato={nuovo_stato}",
                 operatore=operatore)

    return {
        'success': True,
        'id_dettaglio': id_dettaglio,
        'q_da_evadere': q_da_evadere,
        'q_evasa': q_evasa_cumulativo,
        'q_residua': q_residua_dopo,
        'q_totale': q_totale,
        'stato_riga': nuovo_stato,
        'operatore': operatore
    }


def ripristina_riga(
    id_testata: int,
    id_dettaglio: int,
    operatore: str
) -> Dict[str, Any]:
    """
    Ripristina una riga allo stato pre-conferma/pre-archiviazione.

    NOTA: Permette il ripristino di righe ARCHIVIATO per consentire
    all'utente di annullare un'archiviazione fatta per errore.
    Solo EVASO (completamente processato) non è ripristinabile.
    """
    db = get_db()

    riga = db.execute("""
        SELECT id_dettaglio, stato_riga, q_da_evadere, q_evasa,
               q_venduta, q_sconto_merce, q_omaggio
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    q_totale = (riga['q_venduta'] or 0) + (riga['q_sconto_merce'] or 0) + (riga['q_omaggio'] or 0)
    q_evasa = riga['q_evasa'] or 0

    # Solo EVASO (completamente processato) non è ripristinabile
    if riga['stato_riga'] == 'EVASO':
        return {'success': False, 'error': 'Riga già evasa - non ripristinabile'}

    if q_evasa >= q_totale and q_totale > 0:
        return {'success': False, 'error': f'Riga già completamente evasa ({q_evasa}/{q_totale}), non ripristinabile'}

    # ARCHIVIATO può essere ripristinato (undo dell'archiviazione)
    # CONFERMATO, IN_TRACCIATO possono essere ripristinati
    # PARZIALE può essere ripristinato (torna a PARZIALE, azzera q_da_evadere)
    stati_ripristinabili = ('ARCHIVIATO', 'CONFERMATO', 'IN_TRACCIATO', 'PARZIALE')
    if riga['stato_riga'] not in stati_ripristinabili:
        return {'success': False, 'error': f'Stato riga {riga["stato_riga"]} non ripristinabile'}

    # Determina nuovo stato in base a q_evasa
    nuovo_stato = 'PARZIALE' if q_evasa > 0 else 'ESTRATTO'

    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET q_da_evadere = 0,
            stato_riga = ?
        WHERE id_dettaglio = ?
    """, (nuovo_stato, id_dettaglio))

    _aggiorna_contatori_ordine(id_testata)
    db.commit()

    log_operation('RIPRISTINA_RIGA', 'ORDINI_DETTAGLIO', id_dettaglio,
                 f"Ripristinato da {riga['stato_riga']} a {nuovo_stato}",
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
    Ripristina TUTTE le righe CONFERMATO di un ordine allo stato pre-conferma.

    STATI ESCLUSI (non toccati):
    - ARCHIVIATO: stato finale freezato
    - EVASO: già processato completamente
    - PARZIALE: ha già q_evasa > 0
    - ESTRATTO: non ancora confermato
    - IN_SUPERVISIONE: in attesa supervisione

    Opera SOLO su righe con stato_riga = 'CONFERMATO' e q_evasa < q_totale.
    """
    db = get_db()

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


# =============================================================================
# SUPERVISIONE
# =============================================================================

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


# =============================================================================
# HELPER INTERNI
# =============================================================================

def _aggiorna_contatori_ordine(id_testata: int):
    """Aggiorna contatori righe nella testata ordine E lo stato dell'ordine."""
    db = get_db()
    stats = get_stato_righe_ordine(id_testata)

    righe_confermate = (
        stats.get('confermato', 0) +
        stats.get('in_tracciato', 0) +
        stats.get('esportato', 0) +
        stats.get('parzialmente_esp', 0)
    )

    totale = stats.get('totale', 0)
    esportate = stats.get('esportato', 0)
    evaso = stats.get('evaso', 0)
    archiviato = stats.get('archiviato', 0)
    confermate = stats.get('confermato', 0)
    parziali = stats.get('parzialmente_esp', 0)

    # Righe completate = EVASO + ESPORTATO + ARCHIVIATO
    righe_completate = evaso + esportate + archiviato

    righe_con_da_evadere = db.execute("""
        SELECT COUNT(*) FROM ORDINI_DETTAGLIO
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_da_evadere, 0) > 0
    """, (id_testata,)).fetchone()[0]

    # Calcola valore totale netto ordine (esclusi child espositore)
    valore_totale_row = db.execute("""
        SELECT COALESCE(SUM(COALESCE(prezzo_netto, 0) * COALESCE(q_venduta, 0)), 0)
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
    """, (id_testata,)).fetchone()
    valore_totale_netto = float(valore_totale_row[0]) if valore_totale_row else 0.0

    # Logica stato ordine:
    # - EVASO: tutte le righe sono completate (EVASO/ESPORTATO/ARCHIVIATO)
    # - PARZ_EVASO: alcune righe completate, altre no
    # - CONFERMATO: righe confermate ma non ancora evase
    # - ESTRATTO: nessuna riga confermata
    if totale > 0 and righe_completate == totale:
        nuovo_stato = 'EVASO'
    elif righe_completate > 0 or parziali > 0:
        nuovo_stato = 'PARZ_EVASO'
    elif righe_con_da_evadere > 0 or confermate > 0:
        nuovo_stato = 'CONFERMATO'
    else:
        nuovo_stato = 'ESTRATTO'

    db.execute("""
        UPDATE ORDINI_TESTATA
        SET righe_totali = ?,
            righe_confermate = ?,
            righe_in_supervisione = ?,
            stato = ?,
            valore_totale_netto = ?,
            data_ultimo_aggiornamento = CURRENT_TIMESTAMP
        WHERE id_testata = ?
    """, (
        stats['totale'],
        righe_confermate,
        stats['in_supervisione'],
        nuovo_stato,
        valore_totale_netto,
        id_testata
    ))


def fix_stati_righe(id_testata: Optional[int] = None) -> Dict[str, Any]:
    """
    Corregge gli stati delle righe in base a q_evasa e q_totale.

    NOTA: Lo stato dell'ordine NON influenza lo stato delle righe.
    Ogni riga ha il suo stato indipendente basato su:
    - EVASO: q_evasa >= q_totale
    - PARZIALE: q_evasa > 0 AND q_evasa < q_totale
    - ARCHIVIATO: stato manuale, mai sovrascritto
    """
    db = get_db()

    where_clause = "WHERE id_testata = ?" if id_testata else ""
    params = (id_testata,) if id_testata else ()

    # RIMOSSO: Non sincronizzare più stato ordine -> stato righe
    # Lo stato riga è indipendente dallo stato ordine

    righe_evaso = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'EVASO'
        {where_clause}
        {"AND" if where_clause else "WHERE"} (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_evasa, 0) >= (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
          AND (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0)) > 0
          AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
    """, params).rowcount

    righe_parziale = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'PARZIALE'
        {where_clause}
        {"AND" if where_clause else "WHERE"} (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_evasa, 0) > 0
          AND COALESCE(q_evasa, 0) < (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
          AND COALESCE(q_da_evadere, 0) = 0
          AND stato_riga NOT IN ('PARZIALE', 'CONFERMATO', 'EVASO', 'ARCHIVIATO')
    """, params).rowcount

    righe_estratto = db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'ESTRATTO'
        {where_clause}
        {"AND" if where_clause else "WHERE"} (is_child = FALSE OR is_child IS NULL)
          AND COALESCE(q_evasa, 0) = 0
          AND COALESCE(q_da_evadere, 0) = 0
          AND stato_riga NOT IN ('ESTRATTO', 'IN_SUPERVISIONE', 'SUPERVISIONATO', 'CONFERMATO', 'EVASO', 'PARZIALE', 'ARCHIVIATO')
    """, params).rowcount

    db.commit()

    if id_testata:
        _aggiorna_contatori_ordine(id_testata)
    else:
        ordini = db.execute("""
            SELECT DISTINCT id_testata FROM ORDINI_DETTAGLIO
        """).fetchall()
        for o in ordini:
            _aggiorna_contatori_ordine(o['id_testata'])

    db.commit()

    totale = righe_evaso + righe_parziale + righe_estratto

    log_operation('FIX_STATI_RIGHE', 'ORDINI_DETTAGLIO', id_testata or 0,
                 f"Corretti {totale} stati",
                 operatore='SYSTEM')

    return {
        'success': True,
        'totale_corretti': totale,
        'evaso': righe_evaso,
        'parziale': righe_parziale,
        'estratto': righe_estratto,
        'id_testata': id_testata
    }
