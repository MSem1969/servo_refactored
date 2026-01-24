# =============================================================================
# SERV.O v8.1 - LOOKUP QUERIES
# =============================================================================
# Query database e operazioni batch per lookup
# =============================================================================

from typing import Dict, Any, List

from ...database_pg import get_db
from ...utils import normalize_piva

from .matching import lookup_farmacia
from .scoring import fuzzy_match_full


# =============================================================================
# POPOLA HEADER DA ANAGRAFICA
# =============================================================================

def popola_header_da_anagrafica(id_testata: int, operatore: str = None) -> bool:
    """
    Popola i campi header dell'ordine con i dati dell'anagrafica.

    Quando un ordine ha una farmacia/parafarmacia associata (id_farmacia_lookup
    o id_parafarmacia_lookup), recupera i dati dall'anagrafica e aggiorna
    l'header dell'ordine (MIN_ID, CAP, citta, provincia, indirizzo).

    Args:
        id_testata: ID ordine da aggiornare
        operatore: Username operatore (per audit)

    Returns:
        True se aggiornato, False altrimenti
    """
    from ...database_pg import log_modifiche_batch

    db = get_db()

    # Recupera valori correnti PRIMA dell'aggiornamento per audit
    ordine = db.execute("""
        SELECT id_farmacia_lookup, id_parafarmacia_lookup,
               codice_ministeriale_estratto, cap, citta, provincia, indirizzo,
               fonte_anagrafica
        FROM ordini_testata WHERE id_testata = %s
    """, (id_testata,)).fetchone()

    if not ordine:
        return False

    id_farmacia = ordine['id_farmacia_lookup']
    id_parafarmacia = ordine['id_parafarmacia_lookup']

    if not id_farmacia and not id_parafarmacia:
        return False

    # Recupera dati anagrafica
    if id_farmacia:
        farm_data = db.execute("""
            SELECT min_id, partita_iva, ragione_sociale, indirizzo, cap, citta, provincia
            FROM anagrafica_farmacie WHERE id_farmacia = %s
        """, (id_farmacia,)).fetchone()
        fonte_anagrafica = 'LOOKUP_FARMACIA'
    else:
        farm_data = db.execute("""
            SELECT codice_sito as min_id, partita_iva, sito_logistico as ragione_sociale,
                   indirizzo, cap, citta, provincia
            FROM anagrafica_parafarmacie WHERE id_parafarmacia = %s
        """, (id_parafarmacia,)).fetchone()
        fonte_anagrafica = 'LOOKUP_PARAFARMACIA'

    if not farm_data:
        return False

    # Prepara modifiche per audit
    modifiche = {}
    valori_precedenti = {
        'codice_ministeriale_estratto': ordine['codice_ministeriale_estratto'],
        'cap': ordine['cap'],
        'citta': ordine['citta'],
        'provincia': ordine['provincia'],
        'indirizzo': ordine['indirizzo'],
        'fonte_anagrafica': ordine['fonte_anagrafica'] if 'fonte_anagrafica' in ordine.keys() else None
    }

    nuovi_valori = {
        'codice_ministeriale_estratto': farm_data['min_id'] or '',
        'cap': farm_data['cap'] or '',
        'citta': farm_data['citta'] or '',
        'provincia': farm_data['provincia'] or '',
        'indirizzo': farm_data['indirizzo'] or ''
    }

    # Identifica campi modificati
    for campo, nuovo_val in nuovi_valori.items():
        if nuovo_val and nuovo_val != valori_precedenti.get(campo):
            modifiche[campo] = (valori_precedenti.get(campo), nuovo_val)

    # Aggiorna header ordine con dati anagrafica
    db.execute("""
        UPDATE ordini_testata
        SET codice_ministeriale_estratto = COALESCE(NULLIF(%s, ''), codice_ministeriale_estratto),
            cap = COALESCE(NULLIF(%s, ''), cap),
            citta = COALESCE(NULLIF(%s, ''), citta),
            provincia = COALESCE(NULLIF(%s, ''), provincia),
            indirizzo = COALESCE(NULLIF(%s, ''), indirizzo),
            fonte_anagrafica = %s,
            data_modifica_anagrafica = CURRENT_TIMESTAMP,
            operatore_modifica_anagrafica = %s
        WHERE id_testata = %s
    """, (
        farm_data['min_id'] or '',
        farm_data['cap'] or '',
        farm_data['citta'] or '',
        farm_data['provincia'] or '',
        farm_data['indirizzo'] or '',
        fonte_anagrafica,
        operatore,
        id_testata
    ))

    db.commit()

    # Registra audit per ogni campo modificato
    if modifiche:
        if valori_precedenti.get('fonte_anagrafica') != fonte_anagrafica:
            modifiche['fonte_anagrafica'] = (valori_precedenti.get('fonte_anagrafica'), fonte_anagrafica)

        try:
            log_modifiche_batch(
                entita='TESTATA',
                id_entita=id_testata,
                modifiche=modifiche,
                fonte_modifica='LOOKUP_AUTO',
                id_testata=id_testata,
                username_operatore=operatore or 'SISTEMA',
                motivazione=f"Popolamento automatico da anagrafica {fonte_anagrafica}"
            )
        except Exception as e:
            print(f"Warning: Audit log fallito: {e}")

    return True


# =============================================================================
# FUNZIONI BATCH E MANUALI
# =============================================================================

def run_lookup_batch(limit: int = 100) -> Dict[str, Any]:
    """
    Esegue lookup batch su ordini con lookup_method = 'NESSUNO'.

    Returns:
        Dict con statistiche: processati, successi, falliti
    """
    db = get_db()

    # Trova ordini senza lookup
    ordini = db.execute("""
        SELECT id_testata, partita_iva_estratta, citta, indirizzo, ragione_sociale_1
        FROM ORDINI_TESTATA
        WHERE lookup_method = 'NESSUNO' OR lookup_method IS NULL
        LIMIT %s
    """, (limit,)).fetchall()

    stats = {'processati': 0, 'successi': 0, 'falliti': 0}

    for ordine in ordini:
        data = {
            'partita_iva': ordine['partita_iva_estratta'],
            'citta': ordine['citta'],
            'indirizzo': ordine['indirizzo'],
            'ragione_sociale': ordine['ragione_sociale_1'],
        }

        id_farm, id_parafarm, method, source, score = lookup_farmacia(data)
        stats['processati'] += 1

        if method != 'NESSUNO':
            # Aggiorna ordine
            db.execute("""
                UPDATE ORDINI_TESTATA
                SET id_farmacia_lookup = %s,
                    id_parafarmacia_lookup = %s,
                    lookup_method = %s,
                    lookup_source = %s,
                    lookup_score = %s,
                    stato = CASE WHEN stato = 'ANOMALIA' THEN 'ESTRATTO' ELSE stato END
                WHERE id_testata = %s
            """, (id_farm, id_parafarm, method, source, score, ordine['id_testata']))

            # Risolvi anomalia lookup se presente
            db.execute("""
                UPDATE ANOMALIE
                SET stato = 'RISOLTA', data_risoluzione = CURRENT_TIMESTAMP
                WHERE id_testata = %s AND tipo_anomalia = 'LOOKUP' AND stato = 'APERTA'
            """, (ordine['id_testata'],))

            stats['successi'] += 1
        else:
            stats['falliti'] += 1

    db.commit()
    return stats


def lookup_manuale(
    id_testata: int,
    id_farmacia: int = None,
    id_parafarmacia: int = None,
    min_id_manuale: str = None
) -> bool:
    """
    Assegna manualmente una farmacia/parafarmacia a un ordine.

    Args:
        id_testata: ID ordine
        id_farmacia: ID farmacia da database (opzionale)
        id_parafarmacia: ID parafarmacia da database (opzionale)
        min_id_manuale: Codice ministeriale inserito manualmente (opzionale)

    Returns:
        True se successo
    """
    db = get_db()

    # Supporto MIN_ID manuale
    if min_id_manuale:
        min_id_norm = min_id_manuale.strip().zfill(9)

        db.execute("""
            UPDATE ORDINI_TESTATA
            SET codice_ministeriale_estratto = %s,
                id_farmacia_lookup = NULL,
                id_parafarmacia_lookup = NULL,
                lookup_method = 'MANUALE',
                lookup_source = 'MANUALE',
                lookup_score = 100,
                stato = CASE WHEN stato = 'ANOMALIA' THEN 'ESTRATTO' ELSE stato END
            WHERE id_testata = %s
        """, (min_id_norm, id_testata))

        # Risolvi anomalia lookup
        db.execute("""
            UPDATE ANOMALIE
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_testata = %s AND tipo_anomalia = 'LOOKUP' AND stato = 'APERTA'
        """, (f'MIN_ID inserito manualmente: {min_id_norm}', id_testata))

        db.commit()
        return True

    # Assegnazione da database
    if not id_farmacia and not id_parafarmacia:
        return False

    source = 'PARAFARMACIA' if id_parafarmacia else 'FARMACIA'

    # Aggiorna lookup info
    db.execute("""
        UPDATE ORDINI_TESTATA
        SET id_farmacia_lookup = %s,
            id_parafarmacia_lookup = %s,
            lookup_method = 'MANUALE',
            lookup_source = %s,
            lookup_score = 100,
            stato = CASE WHEN stato = 'ANOMALIA' THEN 'ESTRATTO' ELSE stato END
        WHERE id_testata = %s
    """, (id_farmacia, id_parafarmacia, source, id_testata))

    # Risolvi anomalia lookup
    db.execute("""
        UPDATE ANOMALIE
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = 'Assegnazione manuale da database'
        WHERE id_testata = %s AND tipo_anomalia = 'LOOKUP' AND stato = 'APERTA'
    """, (id_testata,))

    db.commit()

    # Popola header con dati anagrafica
    popola_header_da_anagrafica(id_testata)

    # Sblocca ordine se tutte le anomalie sono risolte
    from ..orders.commands import _sblocca_ordine_se_anomalie_risolte
    _sblocca_ordine_se_anomalie_risolte(id_testata)

    return True


def get_pending_lookup(limit: int = 50) -> List[Dict]:
    """Ritorna ordini in attesa di lookup."""
    db = get_db()
    rows = db.execute("""
        SELECT
            ot.id_testata,
            v.codice_vendor as vendor,
            ot.numero_ordine_vendor as numero_ordine,
            ot.partita_iva_estratta as partita_iva,
            ot.ragione_sociale_1 as ragione_sociale,
            ot.indirizzo,
            ot.citta,
            ot.provincia,
            a.nome_file_originale as pdf_file
        FROM ORDINI_TESTATA ot
        JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        JOIN ACQUISIZIONI a ON ot.id_acquisizione = a.id_acquisizione
        WHERE ot.lookup_method = 'NESSUNO' OR ot.lookup_method IS NULL
        ORDER BY ot.data_estrazione DESC
        LIMIT %s
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# RICERCA ANAGRAFICA
# =============================================================================

def search_farmacie(query: str, limit: int = 20) -> List[Dict]:
    """Cerca farmacie per ragione sociale, citta, indirizzo, CAP, provincia, P.IVA o MIN_ID."""
    db = get_db()
    query_like = f"%{query}%"

    rows = db.execute("""
        SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_FARMACIE
        WHERE attiva = TRUE
        AND (
            ragione_sociale ILIKE %s
            OR citta ILIKE %s
            OR indirizzo ILIKE %s
            OR cap ILIKE %s
            OR provincia ILIKE %s
            OR partita_iva ILIKE %s
            OR min_id ILIKE %s
        )
        ORDER BY
            CASE WHEN citta ILIKE %s THEN 0 ELSE 1 END,
            ragione_sociale
        LIMIT %s
    """, (query_like, query_like, query_like, query_like, query_like, query_like, query_like,
          query_like, limit)).fetchall()

    return [dict(row) for row in rows]


def search_parafarmacie(query: str, limit: int = 20) -> List[Dict]:
    """Cerca parafarmacie per ragione sociale, citta, indirizzo, CAP, provincia, P.IVA o codice_sito."""
    db = get_db()
    query_like = f"%{query}%"

    rows = db.execute("""
        SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico as ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_PARAFARMACIE
        WHERE attiva = TRUE
        AND (
            sito_logistico ILIKE %s
            OR citta ILIKE %s
            OR indirizzo ILIKE %s
            OR cap ILIKE %s
            OR provincia ILIKE %s
            OR partita_iva ILIKE %s
            OR codice_sito ILIKE %s
        )
        ORDER BY
            CASE WHEN citta ILIKE %s THEN 0 ELSE 1 END,
            sito_logistico
        LIMIT %s
    """, (query_like, query_like, query_like, query_like, query_like, query_like, query_like,
          query_like, limit)).fetchall()

    return [dict(row) for row in rows]


# =============================================================================
# ALTERNATIVE LOOKUP PER P.IVA
# =============================================================================

def get_alternative_lookup_by_piva(id_testata: int) -> Dict[str, Any]:
    """
    Restituisce le alternative di lookup per un ordine con P.IVA ambigua.

    Quando la P.IVA e stata rilevata correttamente ma corrisponde a piu
    farmacie/parafarmacie (multipunto), questa funzione restituisce tutte
    le alternative filtrate per quella specifica P.IVA, con fuzzy score
    per aiutare la disambiguazione.

    Args:
        id_testata: ID dell'ordine

    Returns:
        Dict con:
        - ordine_data: dati estratti dall'ordine
        - farmacie: lista farmacie con stessa P.IVA e fuzzy score
        - parafarmacie: lista parafarmacie con stessa P.IVA e fuzzy score
        - totale_alternative: numero totale alternative
    """
    db = get_db()

    # Recupera dati ordine
    ordine = db.execute("""
        SELECT
            id_testata,
            partita_iva_estratta AS partita_iva,
            codice_ministeriale_estratto AS codice_ministeriale,
            ragione_sociale_1 AS ragione_sociale,
            indirizzo,
            cap,
            citta,
            provincia,
            lookup_method,
            lookup_score,
            id_farmacia_lookup,
            id_parafarmacia_lookup
        FROM ORDINI_TESTATA
        WHERE id_testata = %s
    """, (id_testata,)).fetchone()

    if not ordine:
        return {'success': False, 'error': 'Ordine non trovato'}

    ordine_data = dict(ordine)
    piva_raw = ordine_data.get('partita_iva', '').strip()
    piva = normalize_piva(piva_raw)

    if not piva or len(piva) < 8:
        return {
            'success': False,
            'error': 'P.IVA non presente o non valida',
            'ordine_data': ordine_data,
            'farmacie': [],
            'parafarmacie': [],
            'totale_alternative': 0
        }

    # Dati per fuzzy matching
    citta = ordine_data.get('citta', '').strip()
    indirizzo = ordine_data.get('indirizzo', '').strip()
    cap = ordine_data.get('cap', '').strip()
    provincia = ordine_data.get('provincia', '').strip()
    ragione_sociale = ordine_data.get('ragione_sociale', '').strip()

    # Cerca farmacie con stessa P.IVA
    farmacie_rows = db.execute("""
        SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_FARMACIE
        WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = %s
        AND attiva = TRUE
        ORDER BY ragione_sociale
    """, (piva,)).fetchall()

    farmacie = []
    for f in farmacie_rows:
        f_dict = dict(f)
        # Calcola fuzzy score per questa alternativa
        score = fuzzy_match_full(
            ragione_sociale, citta, indirizzo,
            f_dict.get('ragione_sociale') or '', f_dict.get('citta') or '', f_dict.get('indirizzo') or '',
            cap, f_dict.get('cap') or '',
            provincia, f_dict.get('provincia') or ''
        )
        f_dict['fuzzy_score'] = score
        f_dict['is_selected'] = (ordine_data.get('id_farmacia_lookup') == f_dict['id_farmacia'])
        farmacie.append(f_dict)

    # Ordina per score decrescente
    farmacie.sort(key=lambda x: x['fuzzy_score'], reverse=True)

    # Cerca parafarmacie con stessa P.IVA
    parafarmacie_rows = db.execute("""
        SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico as ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_PARAFARMACIE
        WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = %s
        AND attiva = TRUE
        ORDER BY sito_logistico
    """, (piva,)).fetchall()

    parafarmacie = []
    for p in parafarmacie_rows:
        p_dict = dict(p)
        # Calcola fuzzy score
        score = fuzzy_match_full(
            ragione_sociale, citta, indirizzo,
            p_dict.get('ragione_sociale') or '', p_dict.get('citta') or '', p_dict.get('indirizzo') or '',
            cap, p_dict.get('cap') or '',
            provincia, p_dict.get('provincia') or ''
        )
        p_dict['fuzzy_score'] = score
        p_dict['is_selected'] = (ordine_data.get('id_parafarmacia_lookup') == p_dict['id_parafarmacia'])
        parafarmacie.append(p_dict)

    # Ordina per score decrescente
    parafarmacie.sort(key=lambda x: x['fuzzy_score'], reverse=True)

    return {
        'success': True,
        'ordine_data': ordine_data,
        'farmacie': farmacie,
        'parafarmacie': parafarmacie,
        'totale_alternative': len(farmacie) + len(parafarmacie),
        'piva_bloccata': piva_raw
    }
