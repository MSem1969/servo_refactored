# =============================================================================
# TO_EXTRACTOR v6.2 - LOOKUP SERVICE
# =============================================================================
# Convertito da notebook Colab - Cella 12
# Ricerca farmacia/parafarmacia con fuzzy matching
# v6.2: Usa indirizzo concatenato per lookup
# =============================================================================

from typing import Dict, Any, List, Tuple, Optional

from ..config import config
from ..database_pg import get_db
from ..utils import normalize_piva

# Fuzzy matching (opzionale)
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("⚠️ fuzzywuzzy non disponibile - fuzzy matching disabilitato")


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

FUZZY_THRESHOLD = config.FUZZY_THRESHOLD  # Default: 60


# =============================================================================
# POPOLA HEADER DA ANAGRAFICA (v6.2.4)
# =============================================================================

def popola_header_da_anagrafica(id_testata: int) -> bool:
    """
    v6.2.4: Popola i campi header dell'ordine con i dati dell'anagrafica.

    Quando un ordine ha una farmacia/parafarmacia associata (id_farmacia_lookup
    o id_parafarmacia_lookup), recupera i dati dall'anagrafica e aggiorna
    l'header dell'ordine (MIN_ID, CAP, città, provincia, indirizzo).

    Args:
        id_testata: ID ordine da aggiornare

    Returns:
        True se aggiornato, False altrimenti
    """
    db = get_db()

    # Recupera ordine con farmacia associata
    ordine = db.execute("""
        SELECT id_farmacia_lookup, id_parafarmacia_lookup
        FROM ordini_testata WHERE id_testata = ?
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
            FROM anagrafica_farmacie WHERE id_farmacia = ?
        """, (id_farmacia,)).fetchone()
    else:
        farm_data = db.execute("""
            SELECT min_id, partita_iva, ragione_sociale, indirizzo, cap, citta, provincia
            FROM anagrafica_parafarmacie WHERE id_parafarmacia = ?
        """, (id_parafarmacia,)).fetchone()

    if not farm_data:
        return False

    # Aggiorna header ordine - usa COALESCE per non sovrascrivere valori esistenti
    # ma qui vogliamo sovrascrivere con i dati corretti dall'anagrafica
    db.execute("""
        UPDATE ordini_testata
        SET codice_ministeriale_estratto = COALESCE(NULLIF(?, ''), codice_ministeriale_estratto),
            cap = COALESCE(NULLIF(?, ''), cap),
            citta = COALESCE(NULLIF(?, ''), citta),
            provincia = COALESCE(NULLIF(?, ''), provincia),
            indirizzo = COALESCE(NULLIF(?, ''), indirizzo)
        WHERE id_testata = ?
    """, (
        farm_data['min_id'] or '',
        farm_data['cap'] or '',
        farm_data['citta'] or '',
        farm_data['provincia'] or '',
        farm_data['indirizzo'] or '',
        id_testata
    ))

    db.commit()
    return True



# =============================================================================
# FUNZIONI FUZZY MATCHING
# =============================================================================

def build_indirizzo_concatenato(indirizzo: str, cap: str, citta: str, provincia: str) -> str:
    """
    Costruisce indirizzo concatenato per lookup (v6.2).

    Formato: {Indirizzo} {CAP} {Città} {Provincia}
    Esempio: "VIA ROMA 123 00100 ROMA RM"

    Args:
        indirizzo: Indirizzo (include numero civico)
        cap: CAP (5 cifre)
        citta: Località
        provincia: Provincia (sigla 2 lettere)

    Returns:
        Stringa concatenata normalizzata
    """
    parts = []
    if indirizzo:
        parts.append(indirizzo.strip().upper())
    if cap:
        parts.append(cap.strip())
    if citta:
        parts.append(citta.strip().upper())
    if provincia:
        parts.append(provincia.strip().upper())
    return ' '.join(parts)


def fuzzy_match_address(citta_estratta: str, indirizzo_estratto: str,
                        citta_db: str, indirizzo_db: str,
                        cap_estratto: str = '', cap_db: str = '',
                        provincia_estratta: str = '', provincia_db: str = '') -> int:
    """
    Calcola score fuzzy su indirizzo concatenato (v6.2).

    Args:
        citta_estratta: Città dal PDF
        indirizzo_estratto: Indirizzo dal PDF
        citta_db: Città da anagrafica
        indirizzo_db: Indirizzo da anagrafica
        cap_estratto: CAP dal PDF
        cap_db: CAP da anagrafica
        provincia_estratta: Provincia dal PDF
        provincia_db: Provincia da anagrafica

    Returns:
        Score 0-100
    """
    if not FUZZY_AVAILABLE:
        # Fallback: match esatto città + CAP
        citta_ok = (citta_estratta and citta_db and
                   citta_estratta.upper().strip() == citta_db.upper().strip())
        cap_ok = (cap_estratto and cap_db and cap_estratto.strip() == cap_db.strip())
        if citta_ok and cap_ok:
            return 100
        elif citta_ok:
            return 70
        return 0

    # v6.2: Usa indirizzo concatenato per match più preciso
    addr_estratto = build_indirizzo_concatenato(
        indirizzo_estratto, cap_estratto, citta_estratta, provincia_estratta
    )
    addr_db = build_indirizzo_concatenato(
        indirizzo_db, cap_db, citta_db, provincia_db
    )

    if addr_estratto and addr_db:
        return fuzz.token_sort_ratio(addr_estratto, addr_db)

    # Fallback se concatenazione vuota
    scores = []

    if citta_estratta and citta_db:
        score_citta = fuzz.token_sort_ratio(
            citta_estratta.upper(),
            citta_db.upper()
        )
        scores.append(score_citta)

    if indirizzo_estratto and indirizzo_db:
        score_indirizzo = fuzz.token_sort_ratio(
            indirizzo_estratto.upper(),
            indirizzo_db.upper()
        )
        scores.append(score_indirizzo)

    if scores:
        return int(sum(scores) / len(scores))
    return 0


def fuzzy_match_full(ragione_sociale_e: str, citta_e: str, indirizzo_e: str,
                     ragione_sociale_db: str, citta_db: str, indirizzo_db: str,
                     cap_e: str = '', cap_db: str = '',
                     provincia_e: str = '', provincia_db: str = '') -> int:
    """
    Calcola score fuzzy combinato su ragione sociale e indirizzo concatenato (v6.2).
    Ragione sociale ha peso 40%, indirizzo concatenato ha peso 60%.

    Args:
        ragione_sociale_e/db: Ragione sociale estratta/da anagrafica
        citta_e/db: Città estratta/da anagrafica
        indirizzo_e/db: Indirizzo estratto/da anagrafica
        cap_e/db: CAP estratto/da anagrafica
        provincia_e/db: Provincia estratta/da anagrafica

    Returns:
        Score 0-100
    """
    if not FUZZY_AVAILABLE:
        return 0

    scores = []
    weights = []

    # Ragione sociale (peso 40%)
    if ragione_sociale_e and ragione_sociale_db:
        score_rs = fuzz.token_sort_ratio(
            ragione_sociale_e.upper(),
            ragione_sociale_db.upper()
        )
        scores.append(score_rs)
        weights.append(0.4)

    # Indirizzo concatenato (peso 60%)
    addr_estratto = build_indirizzo_concatenato(indirizzo_e, cap_e, citta_e, provincia_e)
    addr_db = build_indirizzo_concatenato(indirizzo_db, cap_db, citta_db, provincia_db)

    if addr_estratto and addr_db:
        score_addr = fuzz.token_sort_ratio(addr_estratto, addr_db)
        scores.append(score_addr)
        weights.append(0.6)
    else:
        # Fallback: città + indirizzo separati
        if citta_e and citta_db:
            score_citta = fuzz.token_sort_ratio(citta_e.upper(), citta_db.upper())
            scores.append(score_citta)
            weights.append(0.3)

        if indirizzo_e and indirizzo_db:
            score_indirizzo = fuzz.token_sort_ratio(indirizzo_e.upper(), indirizzo_db.upper())
            scores.append(score_indirizzo)
            weights.append(0.3)

    if scores and weights:
        # Media pesata
        total_weight = sum(weights)
        if total_weight > 0:
            return int(sum(s * w for s, w in zip(scores, weights)) / total_weight)
    return 0


# =============================================================================
# FUNZIONE LOOKUP PRINCIPALE
# =============================================================================

def lookup_farmacia(data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], str, str, int]:
    """
    Cerca farmacia/parafarmacia nel database (v6.2).

    Usa indirizzo concatenato per lookup fuzzy:
    Formato: {Indirizzo} {CAP} {Città} {Provincia}

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
    # v6.2: Estrai anche CAP e provincia per indirizzo concatenato
    cap = data.get('cap', '').strip()
    provincia = data.get('provincia', '').strip()
    
    # Verifica anagrafica caricata
    count_farm = db.execute("SELECT COUNT(*) FROM ANAGRAFICA_FARMACIE").fetchone()[0]
    if count_farm == 0:
        return None, None, 'NESSUNO', 'FARMACIA', 0
    
    # =========================================================================
    # 0. LOOKUP DIRETTO PER MIN_ID (caso ANGELINI con ID MIN)
    # =========================================================================
    # Se ho il codice ministeriale estratto dal documento, cerco direttamente
    # Questo evita lookup superflui quando i dati sono già completi
    
    if min_id and len(min_id) >= 6:
        # Normalizza min_id (rimuovi zeri iniziali per confronto)
        min_id_norm = min_id.lstrip('0')
        
        farmacia = db.execute("""
            SELECT id_farmacia, min_id, partita_iva 
            FROM ANAGRAFICA_FARMACIE 
            WHERE LTRIM(min_id, '0') = ? 
            AND attiva = TRUE
        """, (min_id_norm,)).fetchone()
        
        if farmacia:
            return farmacia['id_farmacia'], None, 'MIN_ID', 'FARMACIA', 100
        
        # Prova anche nelle parafarmacie (codice_sito)
        parafarmacia = db.execute("""
            SELECT id_parafarmacia, codice_sito 
            FROM ANAGRAFICA_PARAFARMACIE 
            WHERE LTRIM(codice_sito, '0') = ? 
            AND attiva = TRUE
        """, (min_id_norm,)).fetchone()
        
        if parafarmacia:
            return None, parafarmacia['id_parafarmacia'], 'MIN_ID', 'PARAFARMACIA', 100
    
    # =========================================================================
    # 1. LOOKUP PER P.IVA
    # =========================================================================
    if piva and len(piva) >= 8:
        # Cerca nelle farmacie (confronto senza zeri iniziali)
        # v6.2: Include provincia per indirizzo concatenato
        farmacie = db.execute("""
            SELECT id_farmacia, min_id, cap, citta, indirizzo, ragione_sociale, provincia
            FROM ANAGRAFICA_FARMACIE
            WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = ?
            AND attiva = TRUE
        """, (piva,)).fetchall()
        
        if len(farmacie) == 1:
            return farmacie[0]['id_farmacia'], None, 'PIVA', 'FARMACIA', 100
        
        if len(farmacie) > 1:
            # P.IVA multipunto → disambiguazione fuzzy con indirizzo concatenato (v6.2)
            best_match, best_score = _disambiguate_multipunto(
                farmacie, citta, indirizzo, 'id_farmacia', cap, provincia
            )

            if best_match and best_score >= FUZZY_THRESHOLD:
                return best_match['id_farmacia'], None, 'PIVA+FUZZY', 'FARMACIA', best_score
            elif best_match:
                # Score sotto soglia ma abbiamo match
                return farmacie[0]['id_farmacia'], None, 'PIVA_AMBIGUA', 'FARMACIA', best_score
        
        # Cerca nelle parafarmacie
        # v6.2: Include provincia per indirizzo concatenato
        parafarmacie = db.execute("""
            SELECT id_parafarmacia, codice_sito, cap, citta, indirizzo, sito_logistico as ragione_sociale, provincia
            FROM ANAGRAFICA_PARAFARMACIE
            WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = ?
            AND attiva = TRUE
        """, (piva,)).fetchall()
        
        if len(parafarmacie) == 1:
            return None, parafarmacie[0]['id_parafarmacia'], 'PIVA', 'PARAFARMACIA', 100
        
        if len(parafarmacie) > 1:
            # v6.2: Usa indirizzo concatenato
            best_match, best_score = _disambiguate_multipunto(
                parafarmacie, citta, indirizzo, 'id_parafarmacia', cap, provincia
            )

            if best_match and best_score >= FUZZY_THRESHOLD:
                return None, best_match['id_parafarmacia'], 'PIVA+FUZZY', 'PARAFARMACIA', best_score
            elif best_match:
                return None, parafarmacie[0]['id_parafarmacia'], 'PIVA_AMBIGUA', 'PARAFARMACIA', best_score
    
    # =========================================================================
    # 2. FALLBACK: FUZZY SU INDIRIZZO CONCATENATO (v6.2)
    # =========================================================================
    if FUZZY_AVAILABLE and (ragione_sociale or citta):
        # Cerca farmacie nella stessa città (o simile) o per CAP
        search_patterns = []
        if citta and len(citta) >= 3:
            search_patterns.extend([f"%{citta[:4]}%", f"%{citta}%"])
        if cap:
            search_patterns.append(f"{cap}%")

        candidates = []
        if search_patterns:
            # Costruisci query dinamica
            citta_clause = "(citta LIKE ? OR citta LIKE ?)" if citta and len(citta) >= 3 else "1=0"
            cap_clause = "cap LIKE ?" if cap else "1=0"
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
            # v6.2: Usa fuzzy_match_full con indirizzo concatenato
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
    Disambigua match multipunto usando fuzzy su indirizzo concatenato (v6.2).

    Args:
        records: Lista di record candidati
        citta: Città estratta
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
        # v6.2: Usa indirizzo concatenato
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
        LIMIT ?
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
                SET id_farmacia_lookup = ?,
                    id_parafarmacia_lookup = ?,
                    lookup_method = ?,
                    lookup_source = ?,
                    lookup_score = ?,
                    stato = CASE WHEN stato = 'ANOMALIA' THEN 'ESTRATTO' ELSE stato END
                WHERE id_testata = ?
            """, (id_farm, id_parafarm, method, source, score, ordine['id_testata']))
            
            # Risolvi anomalia lookup se presente
            db.execute("""
                UPDATE ANOMALIE 
                SET stato = 'RISOLTA', data_risoluzione = datetime('now')
                WHERE id_testata = ? AND tipo_anomalia = 'LOOKUP' AND stato = 'APERTA'
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
        min_id_manuale: Codice ministeriale inserito manualmente (opzionale, v6.2)

    Returns:
        True se successo
    """
    db = get_db()

    # v6.2: Supporto MIN_ID manuale
    if min_id_manuale:
        # Normalizza MIN_ID a 9 cifre
        min_id_norm = min_id_manuale.strip().zfill(9)

        db.execute("""
            UPDATE ORDINI_TESTATA
            SET codice_ministeriale_estratto = ?,
                id_farmacia_lookup = NULL,
                id_parafarmacia_lookup = NULL,
                lookup_method = 'MANUALE',
                lookup_source = 'MANUALE',
                lookup_score = 100,
                stato = CASE WHEN stato = 'ANOMALIA' THEN 'ESTRATTO' ELSE stato END
            WHERE id_testata = ?
        """, (min_id_norm, id_testata))

        # Risolvi anomalia lookup
        db.execute("""
            UPDATE ANOMALIE
            SET stato = 'RISOLTA',
                data_risoluzione = datetime('now'),
                note_risoluzione = ?
            WHERE id_testata = ? AND tipo_anomalia = 'LOOKUP' AND stato = 'APERTA'
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
        SET id_farmacia_lookup = ?,
            id_parafarmacia_lookup = ?,
            lookup_method = 'MANUALE',
            lookup_source = ?,
            lookup_score = 100,
            stato = CASE WHEN stato = 'ANOMALIA' THEN 'ESTRATTO' ELSE stato END
        WHERE id_testata = ?
    """, (id_farmacia, id_parafarmacia, source, id_testata))

    # Risolvi anomalia lookup
    db.execute("""
        UPDATE ANOMALIE
        SET stato = 'RISOLTA',
            data_risoluzione = datetime('now'),
            note_risoluzione = 'Assegnazione manuale da database'
        WHERE id_testata = ? AND tipo_anomalia = 'LOOKUP' AND stato = 'APERTA'
    """, (id_testata,))

    db.commit()

    # v6.2.4: Popola header con dati anagrafica
    popola_header_da_anagrafica(id_testata)

    # v6.2.4: Sblocca ordine se tutte le anomalie sono risolte
    from .ordini import _sblocca_ordine_se_anomalie_risolte
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
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# RICERCA ANAGRAFICA
# =============================================================================

def search_farmacie(query: str, limit: int = 20) -> List[Dict]:
    """Cerca farmacie per ragione sociale, città, indirizzo, CAP, provincia, P.IVA o MIN_ID."""
    db = get_db()
    query_like = f"%{query}%"

    rows = db.execute("""
        SELECT id_farmacia, min_id, partita_iva, ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_FARMACIE
        WHERE attiva = TRUE
        AND (
            ragione_sociale ILIKE ?
            OR citta ILIKE ?
            OR indirizzo ILIKE ?
            OR cap ILIKE ?
            OR provincia ILIKE ?
            OR partita_iva ILIKE ?
            OR min_id ILIKE ?
        )
        ORDER BY
            CASE WHEN citta ILIKE ? THEN 0 ELSE 1 END,
            ragione_sociale
        LIMIT ?
    """, (query_like, query_like, query_like, query_like, query_like, query_like, query_like,
          query_like, limit)).fetchall()

    return [dict(row) for row in rows]


def search_parafarmacie(query: str, limit: int = 20) -> List[Dict]:
    """Cerca parafarmacie per ragione sociale, città, indirizzo, CAP, provincia, P.IVA o codice_sito."""
    db = get_db()
    query_like = f"%{query}%"

    rows = db.execute("""
        SELECT id_parafarmacia, codice_sito, partita_iva, sito_logistico as ragione_sociale,
               indirizzo, cap, citta, provincia
        FROM ANAGRAFICA_PARAFARMACIE
        WHERE attiva = TRUE
        AND (
            sito_logistico ILIKE ?
            OR citta ILIKE ?
            OR indirizzo ILIKE ?
            OR cap ILIKE ?
            OR provincia ILIKE ?
            OR partita_iva ILIKE ?
            OR codice_sito ILIKE ?
        )
        ORDER BY
            CASE WHEN citta ILIKE ? THEN 0 ELSE 1 END,
            sito_logistico
        LIMIT ?
    """, (query_like, query_like, query_like, query_like, query_like, query_like, query_like,
          query_like, limit)).fetchall()

    return [dict(row) for row in rows]


# =============================================================================
# v6.2.5: ALTERNATIVE LOOKUP PER P.IVA
# =============================================================================

def get_alternative_lookup_by_piva(id_testata: int) -> Dict[str, Any]:
    """
    Restituisce le alternative di lookup per un ordine con P.IVA ambigua.

    Quando la P.IVA è stata rilevata correttamente ma corrisponde a più
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
        WHERE id_testata = ?
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
        WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = ?
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
        WHERE LTRIM(REPLACE(COALESCE(partita_iva,''), ' ', ''), '0') = ?
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
        'piva_bloccata': piva_raw  # v6.2.5: Mostra P.IVA bloccata per conferma
    }
