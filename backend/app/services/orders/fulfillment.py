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

    if riga['stato_riga'] == 'CONFERMATO':
        return {'success': False, 'error': 'Riga già confermata'}

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

        if riga['stato_riga'] == 'CONFERMATO':
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
        if riga['stato_riga'] == 'PARZIALE':
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

        # v11.3 FIX: Log CONFERMA_RIGA per ogni riga (per tracking produttività)
        log_operation('CONFERMA_RIGA', 'ORDINI_DETTAGLIO', riga['id_dettaglio'],
                     f"Riga confermata (batch). Ordine: {id_testata}",
                     operatore=operatore)

    _aggiorna_contatori_ordine(id_testata)
    db.commit()

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

def imposta_q_da_evadere(
    id_testata: int,
    id_dettaglio: int,
    q_da_evadere: int,
    operatore: str
) -> Dict[str, Any]:
    """Imposta quantità DA EVADERE per una riga (per il prossimo tracciato).

    Nota: nonostante il nome storico `registra_evasione`, questa funzione NON
    registra un'evasione reale (non aggiorna q_evasa). L'evasione vera avviene
    solo a registrazione bolla.
    """
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

    log_operation('IMPOSTA_Q_DA_EVADERE', 'ORDINI_DETTAGLIO', id_dettaglio,
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


def _cloni_parziali_discendenti(id_testata: int) -> List[Dict[str, Any]]:
    """
    Restituisce la lista di cloni "consegna ripartita" discendenti dello stesso
    ordine root di `id_testata` (escluso l'ordine stesso).

    Se id_testata e' clone, root = id_testata_originale.
    Se id_testata e' root, root = id_testata.
    """
    db = get_db()
    parent = db.execute("""
        SELECT id_testata, is_clone_parziale, id_testata_originale
        FROM ordini_testata
        WHERE id_testata = ?
    """, (id_testata,)).fetchone()
    if not parent:
        return []

    root_id = parent['id_testata_originale'] if parent['is_clone_parziale'] else parent['id_testata']

    cloni = db.execute("""
        SELECT id_testata, numero_ordine_vendor, stato
        FROM ordini_testata
        WHERE id_testata_originale = ?
          AND is_clone_parziale = TRUE
          AND id_testata != ?
        ORDER BY id_testata
    """, (root_id, id_testata)).fetchall()

    return [dict(c) for c in cloni]


def ripristina_riga(
    id_testata: int,
    id_dettaglio: int,
    operatore: str
) -> Dict[str, Any]:
    """
    Ripristina una riga allo stato pre-conferma/pre-evasione.

    v11.5: HARD RESET - permette anche il ripristino di righe EVASO.
    Azzera q_evasa e q_da_evadere, la riga torna a ESTRATTO.

    v11.6: Bloccato se l'ordine ha cloni "consegna ripartita" discendenti
    (le righe residue sono ora gestite sui figli).

    NOTA: I tracciati già generati NON vengono annullati.
    L'operatore è responsabile di gestire eventuali discrepanze.
    """
    db = get_db()

    cloni = _cloni_parziali_discendenti(id_testata)
    if cloni:
        elenco = ', '.join(c['numero_ordine_vendor'] for c in cloni)
        return {
            'success': False,
            'error': (
                f"Impossibile ripristinare: l'ordine ha {len(cloni)} consegne "
                f"ripartite figlie ({elenco}). Le righe residue sono gestite "
                f"su quegli ordini. Ripristina/elimina prima i figli."
            ),
            'cloni_bloccanti': cloni
        }

    riga = db.execute("""
        SELECT id_dettaglio, stato_riga, q_da_evadere, q_evasa,
               q_venduta, q_sconto_merce, q_omaggio
        FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    q_totale = (riga['q_venduta'] or 0) + (riga['q_sconto_merce'] or 0) + (riga['q_omaggio'] or 0)
    q_evasa_precedente = riga['q_evasa'] or 0

    # v11.5: Tutti gli stati sono ripristinabili (incluso EVASO)
    # ARCHIVIATO: undo archiviazione
    # CONFERMATO/ESPORTATO: revoca conferma
    # PARZIALE: azzera q_evasa e q_da_evadere
    # EVASO: HARD RESET - azzera q_evasa e torna a ESTRATTO
    stati_ripristinabili = ('ARCHIVIATO', 'CONFERMATO', 'ESPORTATO', 'PARZIALE', 'EVASO')
    if riga['stato_riga'] not in stati_ripristinabili:
        return {'success': False, 'error': f'Stato riga {riga["stato_riga"]} non ripristinabile'}

    # v11.5: HARD RESET - azzera SEMPRE q_evasa e q_da_evadere
    # La riga torna a ESTRATTO (disponibile per nuova evasione)
    nuovo_stato = 'ESTRATTO'

    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET q_da_evadere = 0,
            q_evasa = 0,
            q_residua = %s,
            stato_riga = %s
        WHERE id_dettaglio = %s
    """, (q_totale, nuovo_stato, id_dettaglio))

    _aggiorna_contatori_ordine(id_testata)
    db.commit()

    # Log dettagliato per audit (importante per EVASO)
    log_msg = f"HARD RESET: {riga['stato_riga']} -> {nuovo_stato}"
    if q_evasa_precedente > 0:
        log_msg += f" (q_evasa azzerato: {q_evasa_precedente} -> 0)"

    log_operation('RIPRISTINA_RIGA', 'ORDINI_DETTAGLIO', id_dettaglio,
                 log_msg, operatore=operatore)

    return {
        'success': True,
        'id_dettaglio': id_dettaglio,
        'stato_precedente': riga['stato_riga'],
        'stato_nuovo': nuovo_stato,
        'q_da_evadere_precedente': riga['q_da_evadere'] or 0,
        'q_evasa_precedente': q_evasa_precedente,
        'q_evasa_nuovo': 0,
        'operatore': operatore,
        'warning': 'I tracciati già generati restano validi. Verificare eventuali discrepanze.' if q_evasa_precedente > 0 else None
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

    v11.6: Bloccato se l'ordine ha cloni "consegna ripartita" discendenti.
    """
    db = get_db()

    cloni = _cloni_parziali_discendenti(id_testata)
    if cloni:
        elenco = ', '.join(c['numero_ordine_vendor'] for c in cloni)
        return {
            'success': False,
            'error': (
                f"Impossibile ripristinare: l'ordine ha {len(cloni)} consegne "
                f"ripartite figlie ({elenco}). Le righe residue sono gestite "
                f"su quegli ordini. Ripristina/elimina prima i figli."
            ),
            'cloni_bloccanti': cloni
        }

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
# CONSEGNE RIPARTITE - CLONE PARZIALE (v11.6)
# =============================================================================

def crea_clone_parziale(
    id_testata: int,
    operatore: str = 'SYSTEM'
) -> Optional[int]:
    """
    Genera un clone "consegna ripartita" dell'ordine `id_testata`:
    - copia testata con `numero_ordine_vendor = root.N` (N progressivo .2/.3/...)
    - copia righe parent NON archiviate con residuo > 0; q_venduta/omaggi
      proporzionati al residuo, q_evasa=0, q_da_evadere=0, stato 'ESTRATTO'
    - copia child dei parent migrati con id_parent_espositore aggiornato
    - SPOSTA anomalie con id_dettaglio sulle righe migrate
    - COPIA supervisione_aic / supervisione_listino in stato PENDING legate
      alle righe migrate (preserva storico ML del parent)
    - lascia anomalie/supervisioni testata-level sul parent

    NON committa: la transazione e' del chiamante (tipicamente generator).

    Returns:
        id_testata del clone, o None se non ci sono righe residue da clonare.
    """
    db = get_db()

    # Righe residue = righe con quantita' ancora da esportare (q_residua > 0).
    # Quantita' "consumata" = q_evasa (post-bolla) + q_esportata (post-export
    # pre-bolla). Casi:
    # - ESTRATTO/CONFERMATO: q_evasa=0, q_esportata=0 → residuo = q_totale
    # - ESPORTATO totale (q_esportata = q_totale): residuo=0 → esclusa
    # - ESPORTATO parziale (0 < q_esportata < q_totale): residuo da clonare
    # - PARZIALE (post-bolla parziale): q_evasa < q_totale → residuo da clonare
    # - EVASO/ARCHIVIATO: stati finali → escluse
    righe_residue = db.execute("""
        SELECT id_dettaglio, q_venduta, q_sconto_merce, q_omaggio,
               COALESCE(q_evasa, 0) AS q_evasa,
               COALESCE(q_esportata, 0) AS q_esportata
        FROM ordini_dettaglio
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
          AND (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0))
              > (COALESCE(q_evasa, 0) + COALESCE(q_esportata, 0))
    """, (id_testata,)).fetchall()

    if not righe_residue:
        return None

    parent = db.execute("""
        SELECT id_testata, numero_ordine_vendor,
               id_testata_originale, is_clone_parziale
        FROM ordini_testata
        WHERE id_testata = ?
    """, (id_testata,)).fetchone()

    if parent['is_clone_parziale'] and parent['id_testata_originale']:
        root_id = parent['id_testata_originale']
        root_numero = db.execute(
            "SELECT numero_ordine_vendor FROM ordini_testata WHERE id_testata = ?",
            (root_id,)
        ).fetchone()['numero_ordine_vendor']
    else:
        root_id = parent['id_testata']
        root_numero = parent['numero_ordine_vendor']

    n_cloni = db.execute("""
        SELECT COUNT(*) FROM ordini_testata
        WHERE id_testata_originale = ? AND is_clone_parziale = TRUE
    """, (root_id,)).fetchone()[0]
    suffisso = n_cloni + 2  # primo clone = .2
    nuovo_numero = f"{root_numero}.{suffisso}"
    chiave_univoca = f"CLONE_{root_id}_{suffisso}_{int(datetime.now().timestamp())}"

    clone_row = db.execute("""
        INSERT INTO ordini_testata (
            id_acquisizione, id_vendor, numero_ordine_vendor,
            data_ordine, data_consegna,
            partita_iva_estratta, codice_ministeriale_estratto,
            ragione_sociale_1, ragione_sociale_2, indirizzo, cap, citta, provincia,
            nome_agente, gg_dilazione_1, gg_dilazione_2, gg_dilazione_3,
            note_ordine, note_ddt,
            id_farmacia_lookup, id_parafarmacia_lookup,
            lookup_method, lookup_source, lookup_score,
            ragione_sociale_1_estratta, indirizzo_estratto, cap_estratto,
            citta_estratta, provincia_estratta,
            data_ordine_estratta, data_consegna_estratta,
            fonte_anagrafica, deposito_riferimento, id_cliente_manuale,
            id_testata_originale, is_clone_parziale, is_ordine_duplicato,
            stato, data_estrazione,
            chiave_univoca_ordine, difarm
        )
        SELECT
            id_acquisizione, id_vendor, ?,
            data_ordine, data_consegna,
            partita_iva_estratta, codice_ministeriale_estratto,
            ragione_sociale_1, ragione_sociale_2, indirizzo, cap, citta, provincia,
            nome_agente, gg_dilazione_1, gg_dilazione_2, gg_dilazione_3,
            note_ordine, note_ddt,
            id_farmacia_lookup, id_parafarmacia_lookup,
            lookup_method, lookup_source, lookup_score,
            ragione_sociale_1_estratta, indirizzo_estratto, cap_estratto,
            citta_estratta, provincia_estratta,
            data_ordine_estratta, data_consegna_estratta,
            fonte_anagrafica, deposito_riferimento, id_cliente_manuale,
            ?, TRUE, FALSE,
            'ESTRATTO', CURRENT_TIMESTAMP,
            ?, difarm
        FROM ordini_testata
        WHERE id_testata = ?
        RETURNING id_testata
    """, (nuovo_numero, root_id, chiave_univoca, id_testata)).fetchone()

    id_clone = clone_row['id_testata']

    map_dettagli = {}  # old_id -> new_id

    for riga in righe_residue:
        q_venduta_orig = riga['q_venduta'] or 0
        q_sconto_merce_orig = riga['q_sconto_merce'] or 0
        q_omaggio_orig = riga['q_omaggio'] or 0
        q_totale_orig = q_venduta_orig + q_sconto_merce_orig + q_omaggio_orig
        q_consumata = (riga['q_evasa'] or 0) + (riga['q_esportata'] or 0)
        q_residuo = q_totale_orig - q_consumata

        if q_consumata == 0 or q_totale_orig == 0:
            nuovo_q_venduta = q_venduta_orig
            nuovo_q_sconto_merce = q_sconto_merce_orig
            nuovo_q_omaggio = q_omaggio_orig
        else:
            ratio = q_residuo / q_totale_orig
            nuovo_q_venduta = int(q_venduta_orig * ratio)
            nuovo_q_sconto_merce = int(q_sconto_merce_orig * ratio)
            nuovo_q_omaggio = int(q_omaggio_orig * ratio)
            diff = q_residuo - (nuovo_q_venduta + nuovo_q_sconto_merce + nuovo_q_omaggio)
            if diff != 0:
                if nuovo_q_venduta > 0:
                    nuovo_q_venduta += diff
                elif nuovo_q_omaggio > 0:
                    nuovo_q_omaggio += diff
                else:
                    nuovo_q_sconto_merce += diff

        nuovo_q_totale = nuovo_q_venduta + nuovo_q_sconto_merce + nuovo_q_omaggio

        riga_clone = db.execute("""
            INSERT INTO ordini_dettaglio (
                id_testata, n_riga, codice_aic, codice_originale, codice_materiale,
                descrizione, tipo_posizione,
                q_venduta, q_sconto_merce, q_omaggio,
                data_consegna_riga,
                sconto_1, sconto_2, sconto_3, sconto_4,
                prezzo_netto, prezzo_scontare, prezzo_pubblico, prezzo_listino,
                valore_netto, aliquota_iva, scorporo_iva,
                note_allestimento, is_espositore, is_child, is_no_aic, tipo_riga,
                id_parent_espositore, espositore_metadata,
                stato_riga, richiede_supervisione,
                modificato_manualmente, valori_originali,
                q_originale, q_residua, q_evasa, q_da_evadere,
                codice_aic_inserito, descrizione_estratta,
                fonte_codice_aic, fonte_quantita,
                num_esportazioni
            )
            SELECT
                ?, n_riga, codice_aic, codice_originale, codice_materiale,
                descrizione, tipo_posizione,
                ?, ?, ?,
                data_consegna_riga,
                sconto_1, sconto_2, sconto_3, sconto_4,
                prezzo_netto, prezzo_scontare, prezzo_pubblico, prezzo_listino,
                valore_netto, aliquota_iva, scorporo_iva,
                note_allestimento, is_espositore, is_child, is_no_aic, tipo_riga,
                NULL, espositore_metadata,
                'ESTRATTO', richiede_supervisione,
                modificato_manualmente, valori_originali,
                ?, ?, 0, 0,
                codice_aic_inserito, descrizione_estratta,
                fonte_codice_aic, fonte_quantita,
                0
            FROM ordini_dettaglio
            WHERE id_dettaglio = ?
            RETURNING id_dettaglio
        """, (
            id_clone,
            nuovo_q_venduta, nuovo_q_sconto_merce, nuovo_q_omaggio,
            nuovo_q_totale, nuovo_q_totale,
            riga['id_dettaglio']
        )).fetchone()

        map_dettagli[riga['id_dettaglio']] = riga_clone['id_dettaglio']

    if map_dettagli:
        parent_old_ids = list(map_dettagli.keys())
        placeholders = ','.join(['?'] * len(parent_old_ids))
        children = db.execute(f"""
            SELECT id_dettaglio, id_parent_espositore
            FROM ordini_dettaglio
            WHERE id_testata = ?
              AND is_child = TRUE
              AND id_parent_espositore IN ({placeholders})
              AND stato_riga != 'ARCHIVIATO'
        """, (id_testata, *parent_old_ids)).fetchall()

        for child in children:
            new_parent_id = map_dettagli.get(child['id_parent_espositore'])
            child_clone = db.execute("""
                INSERT INTO ordini_dettaglio (
                    id_testata, n_riga, codice_aic, codice_originale, codice_materiale,
                    descrizione, tipo_posizione,
                    q_venduta, q_sconto_merce, q_omaggio,
                    data_consegna_riga,
                    sconto_1, sconto_2, sconto_3, sconto_4,
                    prezzo_netto, prezzo_scontare, prezzo_pubblico, prezzo_listino,
                    valore_netto, aliquota_iva, scorporo_iva,
                    note_allestimento, is_espositore, is_child, is_no_aic, tipo_riga,
                    id_parent_espositore, espositore_metadata,
                    stato_riga, richiede_supervisione,
                    modificato_manualmente, valori_originali,
                    q_originale, q_residua, q_evasa, q_da_evadere,
                    codice_aic_inserito, descrizione_estratta,
                    fonte_codice_aic, fonte_quantita,
                    num_esportazioni
                )
                SELECT
                    ?, n_riga, codice_aic, codice_originale, codice_materiale,
                    descrizione, tipo_posizione,
                    q_venduta, q_sconto_merce, q_omaggio,
                    data_consegna_riga,
                    sconto_1, sconto_2, sconto_3, sconto_4,
                    prezzo_netto, prezzo_scontare, prezzo_pubblico, prezzo_listino,
                    valore_netto, aliquota_iva, scorporo_iva,
                    note_allestimento, is_espositore, is_child, is_no_aic, tipo_riga,
                    ?, espositore_metadata,
                    'ESTRATTO', richiede_supervisione,
                    modificato_manualmente, valori_originali,
                    q_originale, q_originale, 0, 0,
                    codice_aic_inserito, descrizione_estratta,
                    fonte_codice_aic, fonte_quantita,
                    0
                FROM ordini_dettaglio
                WHERE id_dettaglio = ?
                RETURNING id_dettaglio
            """, (id_clone, new_parent_id, child['id_dettaglio'])).fetchone()
            map_dettagli[child['id_dettaglio']] = child_clone['id_dettaglio']

        # Sposta anomalie con id_dettaglio sulle righe migrate
        for old_id, new_id in map_dettagli.items():
            db.execute("""
                UPDATE anomalie
                SET id_dettaglio = ?, id_testata = ?
                WHERE id_dettaglio = ? AND id_testata = ?
            """, (new_id, id_clone, old_id, id_testata))

        # Copia supervisione_aic e supervisione_listino PENDING legate alle righe
        for tabella in ('supervisione_aic', 'supervisione_listino'):
            _copia_supervisione_pending(
                tabella,
                map_dettagli,
                id_testata_old=id_testata,
                id_testata_new=id_clone,
                db=db
            )

    # NB: il logging operatore va fatto DOPO il commit del chiamante
    # (log_operation committa internamente, romperebbe l'atomicita').
    return id_clone


def _copia_supervisione_pending(
    tabella: str,
    map_dettagli: Dict[int, int],
    id_testata_old: int,
    id_testata_new: int,
    db
) -> None:
    """
    Copia righe PENDING da una tabella di supervisione (tipo riga-level)
    sostituendo id_testata e id_dettaglio con i nuovi valori.
    Schema dinamico: introspect colonne escludendo PK seriale.
    """
    cols_rows = db.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = ?
          AND column_name NOT IN ('id_supervisione', 'id_correzione', 'id')
        ORDER BY ordinal_position
    """, (tabella,)).fetchall()

    cols = [c['column_name'] for c in cols_rows]
    if 'id_dettaglio' not in cols or 'id_testata' not in cols:
        return  # Non e' una tabella riga-level

    cols_str = ', '.join(cols)

    for old_det, new_det in map_dettagli.items():
        select_parts = []
        params = []
        for col in cols:
            if col == 'id_testata':
                select_parts.append('?')
                params.append(id_testata_new)
            elif col == 'id_dettaglio':
                select_parts.append('?')
                params.append(new_det)
            else:
                select_parts.append(col)
        select_str = ', '.join(select_parts)
        params.extend([old_det, id_testata_old])

        db.execute(f"""
            INSERT INTO {tabella} ({cols_str})
            SELECT {select_str}
            FROM {tabella}
            WHERE id_dettaglio = ? AND id_testata = ?
              AND COALESCE(stato, 'PENDING') = 'PENDING'
        """, tuple(params))


# =============================================================================
# HELPER INTERNI
# =============================================================================

def _calcola_stato_ordine(stato_attuale: str, stats: Dict[str, int],
                          righe_con_da_evadere: int) -> str:
    """Calcola stato testata canonico basato su statistiche righe.

    Regole (ordine di precedenza):
    1. righe_attive == 0:
       - se ci sono righe EVASO → EVASO (archiviazione post-evasione)
       - altrimenti → ARCHIVIATO
    2. tutte righe attive EVASO → EVASO
    3. almeno una EVASO o PARZIALE → PARZ_EVASO
    4. stato_attuale post-tracciato (VALIDATO/ESPORTATO/PARZ_ESPORTATO):
       - se l'operatore ha riportato righe a CONFERMATO con q_da_evadere > 0
         → retrocede a CONFERMATO (mutabilita' ESPORTATO)
       - altrimenti mantiene lo stato post-tracciato
    5. righe confermate o con q_da_evadere > 0 → CONFERMATO
    6. default → ESTRATTO
    """
    totale = stats.get('totale', 0)
    evaso = stats.get('evaso', 0)
    archiviato = stats.get('archiviato', 0)
    parziale = stats.get('parziale', 0)
    confermato = stats.get('confermato', 0)
    esportato = stats.get('esportato', 0)

    righe_attive = totale - archiviato

    if righe_attive == 0:
        return 'EVASO' if evaso > 0 else 'ARCHIVIATO'

    if evaso == righe_attive:
        return 'EVASO'

    if evaso > 0 or parziale > 0:
        return 'PARZ_EVASO'

    stati_post_tracciato = ('VALIDATO', 'ESPORTATO', 'PARZ_ESPORTATO')
    if stato_attuale in stati_post_tracciato:
        # Mutabilita' ESPORTATO: se sono state riportate righe a CONFERMATO
        # con quantita' da esportare, retrocedi a CONFERMATO.
        if righe_con_da_evadere > 0 and confermato > 0 and esportato == 0:
            return 'CONFERMATO'
        return stato_attuale

    if confermato > 0 or esportato > 0 or righe_con_da_evadere > 0:
        return 'CONFERMATO'

    return 'ESTRATTO'


def _aggiorna_contatori_ordine(id_testata: int):
    """Aggiorna contatori righe nella testata ordine E lo stato dell'ordine."""
    db = get_db()
    stats = get_stato_righe_ordine(id_testata)

    righe_confermate = (
        stats.get('confermato', 0) +
        stats.get('esportato', 0) +
        stats.get('parziale', 0)
    )

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

    # Leggi stato attuale per logica stati post-tracciato
    stato_attuale_row = db.execute("""
        SELECT stato FROM ORDINI_TESTATA WHERE id_testata = ?
    """, (id_testata,)).fetchone()
    stato_attuale = stato_attuale_row['stato'] if stato_attuale_row else None

    nuovo_stato = _calcola_stato_ordine(stato_attuale, stats, righe_con_da_evadere)

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
