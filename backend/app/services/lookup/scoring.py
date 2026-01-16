# =============================================================================
# SERV.O v8.1 - LOOKUP SCORING
# =============================================================================
# Funzioni di scoring e fuzzy matching per lookup farmacia
# =============================================================================

# Fuzzy matching (opzionale)
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("Warning: fuzzywuzzy non disponibile - fuzzy matching disabilitato")


# =============================================================================
# NORMALIZZAZIONE INDIRIZZO
# =============================================================================

def build_indirizzo_concatenato(indirizzo: str, cap: str, citta: str, provincia: str) -> str:
    """
    Costruisce indirizzo concatenato per lookup.

    Formato: {Indirizzo} {CAP} {Citta} {Provincia}
    Esempio: "VIA ROMA 123 00100 ROMA RM"

    Args:
        indirizzo: Indirizzo (include numero civico)
        cap: CAP (5 cifre)
        citta: Localita
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


# =============================================================================
# FUNZIONI FUZZY MATCHING
# =============================================================================

def fuzzy_match_address(citta_estratta: str, indirizzo_estratto: str,
                        citta_db: str, indirizzo_db: str,
                        cap_estratto: str = '', cap_db: str = '',
                        provincia_estratta: str = '', provincia_db: str = '') -> int:
    """
    Calcola score fuzzy su indirizzo concatenato.

    Args:
        citta_estratta: Citta dal PDF
        indirizzo_estratto: Indirizzo dal PDF
        citta_db: Citta da anagrafica
        indirizzo_db: Indirizzo da anagrafica
        cap_estratto: CAP dal PDF
        cap_db: CAP da anagrafica
        provincia_estratta: Provincia dal PDF
        provincia_db: Provincia da anagrafica

    Returns:
        Score 0-100
    """
    if not FUZZY_AVAILABLE:
        # Fallback: match esatto citta + CAP
        citta_ok = (citta_estratta and citta_db and
                   citta_estratta.upper().strip() == citta_db.upper().strip())
        cap_ok = (cap_estratto and cap_db and cap_estratto.strip() == cap_db.strip())
        if citta_ok and cap_ok:
            return 100
        elif citta_ok:
            return 70
        return 0

    # Usa indirizzo concatenato per match piu preciso
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
    Calcola score fuzzy combinato su ragione sociale e indirizzo concatenato.
    Ragione sociale ha peso 40%, indirizzo concatenato ha peso 60%.

    Args:
        ragione_sociale_e/db: Ragione sociale estratta/da anagrafica
        citta_e/db: Citta estratta/da anagrafica
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
        # Fallback: citta + indirizzo separati
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
