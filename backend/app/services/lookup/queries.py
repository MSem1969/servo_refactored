# =============================================================================
# SERV.O v11.3 - LOOKUP QUERIES
# =============================================================================
# Query database e operazioni batch per lookup
# v11.3: Verifica caratteri corrotti prima di sovrascrivere dati estratti
# =============================================================================

from typing import Dict, Any, List

from ...database_pg import get_db
from ...utils import normalize_piva

from .matching import lookup_farmacia
from .scoring import fuzzy_match_full


# =============================================================================
# UTILITY - RILEVAMENTO CARATTERI CORROTTI (MOJIBAKE)
# =============================================================================

def _has_corrupted_chars(text: str) -> bool:
    """
    Verifica se un testo contiene caratteri corrotti tipici del mojibake UTF-8.

    Pattern comuni di mojibake (UTF-8 interpretato come Latin-1):
    - Â¿, Â°, Â\u0093, Â\u0094 (caratteri speciali corrotti)
    - Ã¨, Ã¬, Ã², Ã¹, Ã  (accenti gravi corrotti)
    - Ã©, Ã³ (accenti acuti corrotti)

    Args:
        text: Testo da verificare

    Returns:
        True se contiene caratteri corrotti
    """
    if not text:
        return False

    # Pattern mojibake comuni
    corrupted_patterns = [
        'Â¿', 'Â°', 'Â\u0093', 'Â\u0094', 'Â\u0092',  # Caratteri speciali
        'Ã¨', 'Ã¬', 'Ã²', 'Ã¹', 'Ã ',  # Accenti gravi
        'Ã©', 'Ã³', 'Ã¡', 'Ã­', 'Ãº',  # Accenti acuti
        'Ã€', 'Ã‰', 'Ã"', 'Ã™', 'ÃŒ',  # Maiuscole accentate
    ]

    for pattern in corrupted_patterns:
        if pattern in text:
            return True

    return False


# =============================================================================
# POPOLA HEADER DA ANAGRAFICA
# =============================================================================

def popola_header_da_anagrafica(id_testata: int, operatore: str = None) -> bool:
    """
    Popola i campi header dell'ordine con i dati dell'anagrafica.

    Quando un ordine ha una farmacia/parafarmacia associata (id_farmacia_lookup
    o id_parafarmacia_lookup), recupera i dati dall'anagrafica e aggiorna
    l'header dell'ordine (MIN_ID, CAP, citta, provincia, indirizzo).

    v11.3:
    - NON sovrascrive ragione_sociale se già estratta (caso subentro)
    - Aggiunge lookup su anagrafica_clienti per deposito_riferimento

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
               ragione_sociale_1, ragione_sociale_1_estratta, deposito_riferimento,
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

    min_id = farm_data['min_id'] or ''

    # v11.4: Lookup anagrafica_clienti per deposito_riferimento usando MIN_ID
    # Normalizza MIN_ID rimuovendo zeri iniziali per matching
    deposito_riferimento = None
    if min_id:
        min_id_norm = min_id.lstrip('0')
        cliente = db.execute("""
            SELECT deposito_riferimento
            FROM anagrafica_clienti
            WHERE LTRIM(min_id, '0') = %s
            LIMIT 1
        """, (min_id_norm,)).fetchone()
        if cliente and cliente['deposito_riferimento']:
            deposito_riferimento = cliente['deposito_riferimento']

    # Prepara modifiche per audit
    modifiche = {}
    valori_precedenti = {
        'codice_ministeriale_estratto': ordine['codice_ministeriale_estratto'],
        'cap': ordine['cap'],
        'citta': ordine['citta'],
        'provincia': ordine['provincia'],
        'indirizzo': ordine['indirizzo'],
        'deposito_riferimento': ordine['deposito_riferimento'],
        'fonte_anagrafica': ordine['fonte_anagrafica'] if 'fonte_anagrafica' in ordine.keys() else None
    }

    # v11.3: Verifica caratteri corrotti - usa valore anagrafica solo se pulito
    # MIN_ID viene sempre preso dall'anagrafica (è l'obiettivo principale del lookup)
    # Gli altri campi vengono presi dall'anagrafica SOLO SE VUOTI nell'ordine
    # Ragione sociale: NON viene mai sovrascritta (caso subentro)
    nuovi_valori = {
        'codice_ministeriale_estratto': min_id,  # MIN_ID sempre dall'anagrafica
        'deposito_riferimento': deposito_riferimento or '',  # Da anagrafica_clienti
    }

    # Popola campi SOLO se vuoti nell'ordine (non sovrascrivere dati estratti)
    if not ordine['cap'] and farm_data.get('cap') and not _has_corrupted_chars(farm_data.get('cap') or ''):
        nuovi_valori['cap'] = farm_data['cap']
    if not ordine['citta'] and farm_data.get('citta') and not _has_corrupted_chars(farm_data.get('citta') or ''):
        nuovi_valori['citta'] = farm_data['citta']
    if not ordine['provincia'] and farm_data.get('provincia') and not _has_corrupted_chars(farm_data.get('provincia') or ''):
        nuovi_valori['provincia'] = farm_data['provincia']
    if not ordine['indirizzo'] and farm_data.get('indirizzo') and not _has_corrupted_chars(farm_data.get('indirizzo') or ''):
        nuovi_valori['indirizzo'] = farm_data['indirizzo']

    # v11.3: Ragione sociale - popola SOLO se vuota nell'ordine
    # Se già estratta, la manteniamo (potrebbe essere subentro con nuova denominazione)
    ragione_sociale_da_usare = None
    if not ordine['ragione_sociale_1'] and not ordine['ragione_sociale_1_estratta']:
        if farm_data.get('ragione_sociale') and not _has_corrupted_chars(farm_data.get('ragione_sociale') or ''):
            ragione_sociale_da_usare = farm_data['ragione_sociale']
            nuovi_valori['ragione_sociale_1'] = ragione_sociale_da_usare

    # Identifica campi modificati
    for campo, nuovo_val in nuovi_valori.items():
        if nuovo_val and nuovo_val != valori_precedenti.get(campo):
            modifiche[campo] = (valori_precedenti.get(campo), nuovo_val)

    # Aggiorna header ordine con dati anagrafica
    # v11.3: Usa COALESCE per non sovrascrivere valori esistenti
    db.execute("""
        UPDATE ordini_testata
        SET codice_ministeriale_estratto = COALESCE(NULLIF(%s, ''), codice_ministeriale_estratto),
            cap = COALESCE(NULLIF(%s, ''), cap),
            citta = COALESCE(NULLIF(%s, ''), citta),
            provincia = COALESCE(NULLIF(%s, ''), provincia),
            indirizzo = COALESCE(NULLIF(%s, ''), indirizzo),
            ragione_sociale_1 = COALESCE(NULLIF(%s, ''), ragione_sociale_1),
            deposito_riferimento = COALESCE(NULLIF(%s, ''), deposito_riferimento),
            fonte_anagrafica = %s,
            data_modifica_anagrafica = CURRENT_TIMESTAMP,
            operatore_modifica_anagrafica = %s
        WHERE id_testata = %s
    """, (
        min_id,
        nuovi_valori.get('cap', ''),
        nuovi_valori.get('citta', ''),
        nuovi_valori.get('provincia', ''),
        nuovi_valori.get('indirizzo', ''),
        ragione_sociale_da_usare or '',
        deposito_riferimento or '',
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

def _parse_search_query(query: str) -> tuple:
    """
    Parsa la query di ricerca per operatori logici.

    Operatori supportati:
    - " + " (OR): SEMINARA + CATANIA → trova record con SEMINARA oppure CATANIA
    - " * " (AND): SEMINARA * CATANIA → trova record con SEMINARA e CATANIA (in campi diversi)
    - Senza operatori: ricerca stringa normale

    Returns:
        tuple: (operator, terms) dove operator è 'OR', 'AND' o None
    """
    query = query.strip()

    # Controlla operatore OR (spazio + spazio)
    if ' + ' in query:
        terms = [t.strip() for t in query.split(' + ') if t.strip()]
        if len(terms) >= 2:
            return ('OR', terms)

    # Controlla operatore AND (spazio * spazio)
    if ' * ' in query:
        terms = [t.strip() for t in query.split(' * ') if t.strip()]
        if len(terms) >= 2:
            return ('AND', terms)

    # Nessun operatore - ricerca normale
    return (None, [query])


def _build_search_condition_farmacie(operator: str, terms: List[str]) -> tuple:
    """
    Costruisce la condizione WHERE e i parametri per la ricerca farmacie.

    Returns:
        tuple: (where_clause, params)
    """
    fields = [
        'ragione_sociale', 'citta', 'indirizzo', 'cap',
        'provincia', 'partita_iva', 'min_id'
    ]

    if operator is None:
        # Ricerca normale - un termine su tutti i campi (OR tra campi)
        term_like = f"%{terms[0]}%"
        field_conditions = ' OR '.join([f"{f} ILIKE %s" for f in fields])
        return (f"({field_conditions})", [term_like] * len(fields), term_like)

    elif operator == 'OR':
        # OR tra termini: ogni termine può essere in qualsiasi campo
        # (term1 in any field) OR (term2 in any field)
        term_conditions = []
        params = []
        for term in terms:
            term_like = f"%{term}%"
            field_conditions = ' OR '.join([f"{f} ILIKE %s" for f in fields])
            term_conditions.append(f"({field_conditions})")
            params.extend([term_like] * len(fields))
        where_clause = ' OR '.join(term_conditions)
        # Per ORDER BY, usa il primo termine
        return (f"({where_clause})", params, f"%{terms[0]}%")

    elif operator == 'AND':
        # AND tra termini: ogni termine deve essere presente (in qualsiasi campo)
        # (term1 in any field) AND (term2 in any field)
        term_conditions = []
        params = []
        for term in terms:
            term_like = f"%{term}%"
            field_conditions = ' OR '.join([f"{f} ILIKE %s" for f in fields])
            term_conditions.append(f"({field_conditions})")
            params.extend([term_like] * len(fields))
        where_clause = ' AND '.join(term_conditions)
        # Per ORDER BY, usa il primo termine
        return (f"({where_clause})", params, f"%{terms[0]}%")

    return ("TRUE", [], "%")


def _build_search_condition_parafarmacie(operator: str, terms: List[str]) -> tuple:
    """
    Costruisce la condizione WHERE e i parametri per la ricerca parafarmacie.

    Returns:
        tuple: (where_clause, params)
    """
    fields = [
        'sito_logistico', 'citta', 'indirizzo', 'cap',
        'provincia', 'partita_iva', 'codice_sito'
    ]

    if operator is None:
        # Ricerca normale
        term_like = f"%{terms[0]}%"
        field_conditions = ' OR '.join([f"{f} ILIKE %s" for f in fields])
        return (f"({field_conditions})", [term_like] * len(fields), term_like)

    elif operator == 'OR':
        term_conditions = []
        params = []
        for term in terms:
            term_like = f"%{term}%"
            field_conditions = ' OR '.join([f"{f} ILIKE %s" for f in fields])
            term_conditions.append(f"({field_conditions})")
            params.extend([term_like] * len(fields))
        where_clause = ' OR '.join(term_conditions)
        return (f"({where_clause})", params, f"%{terms[0]}%")

    elif operator == 'AND':
        term_conditions = []
        params = []
        for term in terms:
            term_like = f"%{term}%"
            field_conditions = ' OR '.join([f"{f} ILIKE %s" for f in fields])
            term_conditions.append(f"({field_conditions})")
            params.extend([term_like] * len(fields))
        where_clause = ' AND '.join(term_conditions)
        return (f"({where_clause})", params, f"%{terms[0]}%")

    return ("TRUE", [], "%")


def search_farmacie(query: str, limit: int = 20) -> List[Dict]:
    """
    Cerca farmacie per ragione sociale, citta, indirizzo, CAP, provincia, P.IVA o MIN_ID.

    Supporta operatori logici:
    - " + " (OR): SEMINARA + CATANIA → trova SEMINARA oppure CATANIA
    - " * " (AND): SEMINARA * CATANIA → trova SEMINARA e CATANIA
    - Senza operatori: ricerca stringa normale
    """
    db = get_db()

    # Parsa query per operatori
    operator, terms = _parse_search_query(query)
    where_clause, params, order_param = _build_search_condition_farmacie(operator, terms)

    sql = f"""
        SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_FARMACIE
        WHERE attiva = TRUE
        AND {where_clause}
        ORDER BY
            CASE WHEN citta ILIKE %s THEN 0 ELSE 1 END,
            ragione_sociale
        LIMIT %s
    """

    all_params = params + [order_param, limit]
    rows = db.execute(sql, all_params).fetchall()

    return [dict(row) for row in rows]


def search_parafarmacie(query: str, limit: int = 20) -> List[Dict]:
    """
    Cerca parafarmacie per ragione sociale, citta, indirizzo, CAP, provincia, P.IVA o codice_sito.

    Supporta operatori logici:
    - " + " (OR): SEMINARA + CATANIA → trova SEMINARA oppure CATANIA
    - " * " (AND): SEMINARA * CATANIA → trova SEMINARA e CATANIA
    - Senza operatori: ricerca stringa normale
    """
    db = get_db()

    # Parsa query per operatori
    operator, terms = _parse_search_query(query)
    where_clause, params, order_param = _build_search_condition_parafarmacie(operator, terms)

    sql = f"""
        SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico as ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_PARAFARMACIE
        WHERE attiva = TRUE
        AND {where_clause}
        ORDER BY
            CASE WHEN citta ILIKE %s THEN 0 ELSE 1 END,
            sito_logistico
        LIMIT %s
    """

    all_params = params + [order_param, limit]
    rows = db.execute(sql, all_params).fetchall()

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
