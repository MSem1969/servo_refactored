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

def lookup_cliente_by_piva(piva: str) -> Optional[Dict[str, Any]]:
    """
    Cerca cliente in anagrafica_clienti per P.IVA.

    Args:
        piva: Partita IVA normalizzata (senza zeri iniziali)

    Returns:
        Dict con min_id e deposito_riferimento se trovato, None altrimenti
    """
    if not piva or len(piva) < 8:
        return None

    db = get_db()

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

    v11.2: Prima cerca in anagrafica_clienti per P.IVA per ottenere MIN_ID,
           poi usa quel MIN_ID per collegare ad anagrafica_farmacie.

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
    id_farm, id_parafarm, method, source, score = lookup_farmacia(data)

    # Cerca anche in anagrafica_clienti per ottenere deposito_riferimento
    piva_raw = data.get('partita_iva', '').strip()
    cliente_info = lookup_cliente_by_piva(piva_raw)

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
    # 0a. LOOKUP VIA ANAGRAFICA_CLIENTI (v11.2)
    # =========================================================================
    # Se non abbiamo MIN_ID dal PDF ma abbiamo P.IVA, cerchiamo il MIN_ID
    # nella tabella anagrafica_clienti (ANAG_TOT_V.csv) che contiene il link
    # tra P.IVA cliente e MIN_ID farmacia.
    if not min_id and piva and len(piva) >= 8:
        cliente_info = lookup_cliente_by_piva(piva_raw)
        if cliente_info and cliente_info.get('min_id'):
            # Trovato MIN_ID in anagrafica_clienti, usalo per il lookup
            min_id = cliente_info['min_id']
            # Nota: il deposito_riferimento viene recuperato separatamente
            # tramite lookup_farmacia_extended() nel pdf_processor

    # =========================================================================
    # 0b. LOOKUP DIRETTO PER MIN_ID (caso ANGELINI con ID MIN o da anagrafica_clienti)
    # =========================================================================
    if min_id and len(min_id) >= 4:
        min_id_norm = min_id.lstrip('0')

        farmacia = db.execute("""
            SELECT id_farmacia, min_id, partita_iva, ragione_sociale
            FROM ANAGRAFICA_FARMACIE
            WHERE LTRIM(min_id, '0') = %s
            AND attiva = TRUE
        """, (min_id_norm,)).fetchone()

        if farmacia:
            # v8.2: Verifica coerenza P.IVA tra PDF e anagrafica
            piva_anagrafica = normalize_piva(farmacia.get('partita_iva') or '')

            if piva and piva_anagrafica and piva != piva_anagrafica:
                # P.IVA MISMATCH! Probabile subentro/cambio proprietà
                # Score 50 per triggerare anomalia LKP-A04
                return farmacia['id_farmacia'], None, 'MIN_ID_PIVA_MISMATCH', 'FARMACIA', 50

            return farmacia['id_farmacia'], None, 'MIN_ID', 'FARMACIA', 100

        # Prova anche nelle parafarmacie (codice_sito)
        parafarmacia = db.execute("""
            SELECT id_parafarmacia, codice_sito, partita_iva
            FROM ANAGRAFICA_PARAFARMACIE
            WHERE LTRIM(codice_sito, '0') = %s
            AND attiva = TRUE
        """, (min_id_norm,)).fetchone()

        if parafarmacia:
            # v8.2: Verifica coerenza P.IVA anche per parafarmacie
            piva_anagrafica = normalize_piva(parafarmacia.get('partita_iva') or '')

            if piva and piva_anagrafica and piva != piva_anagrafica:
                return None, parafarmacia['id_parafarmacia'], 'MIN_ID_PIVA_MISMATCH', 'PARAFARMACIA', 50

            return None, parafarmacia['id_parafarmacia'], 'MIN_ID', 'PARAFARMACIA', 100

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
