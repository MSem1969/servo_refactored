# =============================================================================
# SERV.O v11.2 - LOOKUP MATCHING
# =============================================================================
# Logica principale di lookup farmacia/parafarmacia
# v11.2: Integrazione anagrafica_clienti per lookup MIN_ID e deposito_riferimento
# =============================================================================

from typing import Dict, Any, List, Tuple, Optional

from ...config import config
from ...database_pg import get_db
from ...utils import normalize_piva
from ...utils.codes import filtro_min_id_cliente, is_codice_parafarmacia

from .scoring import (
    FUZZY_AVAILABLE,
    fuzzy_match_address,
    fuzzy_match_full,
)


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

FUZZY_THRESHOLD = config.FUZZY_THRESHOLD  # Default: 60


# =============================================================================
# LOOKUP ANAGRAFICA CLIENTI (v11.2)
# =============================================================================

def lookup_cliente_by_piva(piva: str, min_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Cerca cliente in anagrafica_clienti per P.IVA.

    Usato per ottenere deposito_riferimento e validazione cliente (LKP-A05).
    NON deve essere usato per determinare il MIN_ID ai fini del matching
    (il matching avviene su anagrafica_farmacie ministeriale).

    Args:
        piva: Partita IVA normalizzata (senza zeri iniziali)
        min_id: Se fornito, disambigua il record corretto in caso multipunto

    Returns:
        Dict con min_id e deposito_riferimento se trovato, None altrimenti
    """
    if not piva or len(piva) < 8:
        return None

    db = get_db()

    # Se abbiamo il MIN_ID (dal matching ministeriale), cerchiamo il record esatto
    if min_id:
        filtro, params = filtro_min_id_cliente(min_id)
        cliente = db.execute(f"""
            SELECT min_id, deposito_riferimento, ragione_sociale_1, codice_cliente
            FROM anagrafica_clienti
            WHERE partita_iva = %s AND {filtro}
        """, [piva] + params).fetchone()
        if cliente and cliente.get('min_id'):
            return {
                'min_id': cliente['min_id'],
                'deposito_riferimento': cliente.get('deposito_riferimento'),
                'ragione_sociale': cliente.get('ragione_sociale_1'),
                'codice_cliente': cliente.get('codice_cliente'),
            }

    # Fallback: cerca per sola P.IVA (ok se monopunto)
    cliente = db.execute("""
        SELECT min_id, deposito_riferimento, ragione_sociale_1, codice_cliente
        FROM anagrafica_clienti
        WHERE partita_iva = %s
    """, (piva,)).fetchone()

    if cliente and cliente.get('min_id'):
        return {
            'min_id': cliente['min_id'],
            'deposito_riferimento': cliente.get('deposito_riferimento'),
            'ragione_sociale': cliente.get('ragione_sociale_1'),
            'codice_cliente': cliente.get('codice_cliente'),
        }

    return None


def lookup_farmacia_extended(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Versione estesa di lookup_farmacia che include deposito_riferimento.

    Gerarchia: il matching avviene su anagrafica_farmacie (ministeriale).
    L'anagrafica_clienti è usata solo per deposito_riferimento e validazione,
    disambiguata tramite il MIN_ID risultante dal matching ministeriale.

    Args:
        data: Dict con dati estratti

    Returns:
        Dict con:
        - id_farmacia: int o None
        - id_parafarmacia: int o None
        - lookup_method: str
        - lookup_source: str
        - score: int
        - deposito_riferimento: str o None (da anagrafica_clienti)
        - cliente_trovato: bool (True se P.IVA trovata in anagrafica_clienti)
    """
    db = get_db()
    id_farm, id_parafarm, method, source, score = lookup_farmacia(data)

    # Recupera il MIN_ID dal match ministeriale per disambiguare anagrafica_clienti
    matched_min_id = None
    if id_farm:
        row = db.execute(
            "SELECT min_id FROM anagrafica_farmacie WHERE id_farmacia = %s",
            (id_farm,)
        ).fetchone()
        if row:
            matched_min_id = row['min_id']
    elif id_parafarm:
        row = db.execute(
            "SELECT codice_sito FROM anagrafica_parafarmacie WHERE id_parafarmacia = %s",
            (id_parafarm,)
        ).fetchone()
        if row:
            matched_min_id = row['codice_sito']

    # Cerca in anagrafica_clienti per deposito_riferimento, disambiguando con MIN_ID
    piva_raw = data.get('partita_iva', '').strip()
    cliente_info = lookup_cliente_by_piva(piva_raw, min_id=matched_min_id)

    return {
        'id_farmacia': id_farm,
        'id_parafarmacia': id_parafarm,
        'lookup_method': method,
        'lookup_source': source,
        'score': score,
        'deposito_riferimento': cliente_info.get('deposito_riferimento') if cliente_info else None,
        'cliente_trovato': cliente_info is not None,
        'min_id_cliente': cliente_info.get('min_id') if cliente_info else None,
    }


# =============================================================================
# FUNZIONE LOOKUP PRINCIPALE
# =============================================================================

def lookup_farmacia(data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], str, str, int]:
    """
    Cerca farmacia/parafarmacia nel database.

    Usa indirizzo concatenato per lookup fuzzy:
    Formato: {Indirizzo} {CAP} {Citta} {Provincia}

    Args:
        data: Dict con dati estratti (partita_iva, codice_ministeriale, citta, indirizzo,
              ragione_sociale, cap, provincia)

    Returns:
        Tuple (id_farmacia, id_parafarmacia, lookup_method, lookup_source, score)

    Lookup methods:
        - MIN_ID: Match diretto su codice ministeriale (caso ANGELINI)
        - PIVA: Match esatto P.IVA
        - PIVA+FUZZY: P.IVA multipunto disambiguata con fuzzy
        - PIVA_AMBIGUA: P.IVA multipunto non disambiguata
        - FUZZY: Solo fuzzy matching su indirizzo concatenato
        - NESSUNO: Nessun match trovato
    """
    db = get_db()

    piva_raw = data.get('partita_iva', '').strip()
    piva = normalize_piva(piva_raw)
    citta = data.get('citta', '').strip()
    indirizzo = data.get('indirizzo', '').strip()
    ragione_sociale = data.get('ragione_sociale', '').strip()
    min_id = data.get('codice_ministeriale', '').strip()
    cap = data.get('cap', '').strip()
    provincia = data.get('provincia', '').strip()

    # Verifica anagrafica caricata
    count_farm = db.execute("SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE").fetchone()[0]
    if count_farm == 0:
        return None, None, 'NESSUNO', 'FARMACIA', 0

    # =========================================================================
    # 0. LOOKUP DIRETTO PER MIN_ID (caso ANGELINI con ID MIN nel PDF)
    # =========================================================================
    # NOTA: il MIN_ID deve provenire dal documento (PDF), NON dall'anagrafica_clienti.
    # L'anagrafica ministeriale (ANAGRAFICA_FARMACIE) è la fonte primaria per il matching.
    # L'anagrafica_clienti serve solo per deposito_riferimento e validazione (LKP-A05).
    if min_id and len(min_id) >= 4:
        min_id_norm = min_id.lstrip('0')

        # Tolti gli zeri, farmacia 000014706 e parafarmacia 014706 coincidono:
        # si cerca prima nell'elenco del tipo indicato dalla lunghezza del codice.
        ricerche = [
            ('FARMACIA', """
                SELECT id_farmacia AS id, partita_iva
                FROM ANAGRAFICA_FARMACIE
                WHERE LTRIM(min_id, '0') = %s
                AND attiva = TRUE
            """),
            ('PARAFARMACIA', """
                SELECT id_parafarmacia AS id, partita_iva
                FROM ANAGRAFICA_PARAFARMACIE
                WHERE LTRIM(codice_sito, '0') = %s
                AND attiva = TRUE
            """),
        ]
        if is_codice_parafarmacia(min_id):
            ricerche.reverse()

        # Se la P.IVA non corrisponde si prova anche l'altro elenco prima di
        # segnalare il subentro (LKP-A04): il codice puo' essere della
        # farmacia/parafarmacia omonima con la P.IVA del PDF (015280 scritto
        # 15280 nel PDF: la lunghezza indica l'elenco sbagliato).
        mismatch = None
        for tipo, query in ricerche:
            trovato = db.execute(query, (min_id_norm,)).fetchone()
            if not trovato:
                continue

            id_farm = trovato['id'] if tipo == 'FARMACIA' else None
            id_parafarm = trovato['id'] if tipo == 'PARAFARMACIA' else None

            # v8.2: Verifica coerenza P.IVA tra PDF e anagrafica
            piva_anagrafica = normalize_piva(trovato.get('partita_iva') or '')

            if piva and piva_anagrafica and piva != piva_anagrafica:
                # P.IVA MISMATCH! Probabile subentro/cambio proprietà
                # Score 50 per triggerare anomalia LKP-A04
                mismatch = mismatch or (id_farm, id_parafarm, 'MIN_ID_PIVA_MISMATCH', tipo, 50)
                continue

            return id_farm, id_parafarm, 'MIN_ID', tipo, 100

        if mismatch:
            return mismatch

    # =========================================================================
    # 1. LOOKUP PER P.IVA
    # =========================================================================
    if piva and len(piva) >= 8:
        # Cerca nelle farmacie
        farmacie = db.execute("""
            SELECT id_farmacia, min_id, cap, citta, indirizzo, ragione_sociale, provincia
            FROM ANAGRAFICA_FARMACIE
            WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = %s
            AND attiva = TRUE
        """, (piva,)).fetchall()

        if len(farmacie) == 1:
            return farmacie[0]['id_farmacia'], None, 'PIVA', 'FARMACIA', 100

        if len(farmacie) > 1:
            # P.IVA multipunto -> disambiguazione fuzzy
            best_match, best_score = _disambiguate_multipunto(
                farmacie, citta, indirizzo, 'id_farmacia', cap, provincia
            )

            if best_match and best_score >= FUZZY_THRESHOLD:
                return best_match['id_farmacia'], None, 'PIVA+FUZZY', 'FARMACIA', best_score
            elif best_match:
                return farmacie[0]['id_farmacia'], None, 'PIVA_AMBIGUA', 'FARMACIA', best_score

        # Cerca nelle parafarmacie
        parafarmacie = db.execute("""
            SELECT id_parafarmacia, codice_sito, cap, citta, indirizzo, sito_logistico as ragione_sociale, provincia
            FROM ANAGRAFICA_PARAFARMACIE
            WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = %s
            AND attiva = TRUE
        """, (piva,)).fetchall()

        if len(parafarmacie) == 1:
            return None, parafarmacie[0]['id_parafarmacia'], 'PIVA', 'PARAFARMACIA', 100

        if len(parafarmacie) > 1:
            best_match, best_score = _disambiguate_multipunto(
                parafarmacie, citta, indirizzo, 'id_parafarmacia', cap, provincia
            )

            if best_match and best_score >= FUZZY_THRESHOLD:
                return None, best_match['id_parafarmacia'], 'PIVA+FUZZY', 'PARAFARMACIA', best_score
            elif best_match:
                return None, parafarmacie[0]['id_parafarmacia'], 'PIVA_AMBIGUA', 'PARAFARMACIA', best_score

    # =========================================================================
    # 2. FALLBACK: FUZZY SU INDIRIZZO CONCATENATO
    # =========================================================================
    if FUZZY_AVAILABLE and (ragione_sociale or citta):
        search_patterns = []
        if citta and len(citta) >= 3:
            search_patterns.extend([f"%{citta[:4]}%", f"%{citta}%"])
        if cap:
            search_patterns.append(f"{cap}%")

        candidates = []
        if search_patterns:
            citta_clause = "(citta LIKE %s OR citta LIKE %s)" if citta and len(citta) >= 3 else "1=0"
            cap_clause = "cap LIKE %s" if cap else "1=0"
            query = f"""
                SELECT id_farmacia, ragione_sociale, citta, indirizzo, cap, provincia
                FROM ANAGRAFICA_FARMACIE
                WHERE attiva = TRUE
                AND ({citta_clause} OR {cap_clause})
                LIMIT 200
            """
            params = []
            if citta and len(citta) >= 3:
                params.extend([f"%{citta[:4]}%", f"%{citta}%"])
            if cap:
                params.append(f"{cap}%")
            candidates = db.execute(query, params).fetchall()

        best_match = None
        best_score = 0
        best_is_parafarmacia = False

        for c in candidates:
            score = fuzzy_match_full(
                ragione_sociale, citta, indirizzo,
                c['ragione_sociale'] or '', c['citta'] or '', c['indirizzo'] or '',
                cap, c['cap'] or '',
                provincia, c['provincia'] or ''
            )
            if score > best_score:
                best_score = score
                best_match = c
                best_is_parafarmacia = False

        # Cerca anche in parafarmacie
        candidates_para = []
        if search_patterns:
            query_para = f"""
                SELECT id_parafarmacia, sito_logistico as ragione_sociale, citta, indirizzo, cap, provincia
                FROM ANAGRAFICA_PARAFARMACIE
                WHERE attiva = TRUE
                AND ({citta_clause} OR {cap_clause})
                LIMIT 200
            """
            candidates_para = db.execute(query_para, params).fetchall()

        for c in candidates_para:
            score = fuzzy_match_full(
                ragione_sociale, citta, indirizzo,
                c['ragione_sociale'] or '', c['citta'] or '', c['indirizzo'] or '',
                cap, c['cap'] or '',
                provincia, c['provincia'] or ''
            )
            if score > best_score:
                best_score = score
                best_match = c
                best_is_parafarmacia = True

        if best_match and best_score >= FUZZY_THRESHOLD:
            if best_is_parafarmacia:
                return None, best_match['id_parafarmacia'], 'FUZZY', 'PARAFARMACIA', best_score
            else:
                return best_match['id_farmacia'], None, 'FUZZY', 'FARMACIA', best_score

    # =========================================================================
    # 3. NESSUN MATCH
    # =========================================================================
    return None, None, 'NESSUNO', 'FARMACIA', 0


def _disambiguate_multipunto(
    records: List,
    citta: str,
    indirizzo: str,
    id_field: str,
    cap: str = '',
    provincia: str = ''
) -> Tuple[Optional[Dict], int]:
    """
    Disambigua match multipunto usando fuzzy su indirizzo concatenato.

    Args:
        records: Lista di record candidati
        citta: Citta estratta
        indirizzo: Indirizzo estratto
        id_field: Nome campo ID (id_farmacia o id_parafarmacia)
        cap: CAP estratto
        provincia: Provincia estratta

    Returns:
        Tuple (best_match, best_score)
    """
    best_match = None
    best_score = 0

    for r in records:
        score = fuzzy_match_address(
            citta, indirizzo,
            r['citta'] or '', r['indirizzo'] or '',
            cap, r.get('cap') or '',
            provincia, r.get('provincia') or ''
        )
        if score > best_score:
            best_score = score
            best_match = dict(r)

    return best_match, best_score
