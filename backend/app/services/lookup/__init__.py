# =============================================================================
# SERV.O v11.2 - LOOKUP SERVICE
# =============================================================================
# Ricerca farmacia/parafarmacia con fuzzy matching
#
# Struttura modulare:
# - scoring.py: Funzioni di scoring e fuzzy matching
# - matching.py: Logica principale di lookup
# - queries.py: Query database e operazioni batch
#
# v11.2: Aggiunta integrazione anagrafica_clienti per lookup MIN_ID
# =============================================================================

# Scoring
from .scoring import (
    FUZZY_AVAILABLE,
    build_indirizzo_concatenato,
    fuzzy_match_address,
    fuzzy_match_full,
)

# Matching
from .matching import (
    FUZZY_THRESHOLD,
    lookup_farmacia,
    lookup_farmacia_extended,
    lookup_cliente_by_piva,
    _disambiguate_multipunto,
)

# Queries
from .queries import (
    popola_header_da_anagrafica,
    run_lookup_batch,
    lookup_manuale,
    get_pending_lookup,
    search_farmacie,
    search_parafarmacie,
    get_alternative_lookup_by_piva,
)


__all__ = [
    # Scoring
    'FUZZY_AVAILABLE',
    'build_indirizzo_concatenato',
    'fuzzy_match_address',
    'fuzzy_match_full',
    # Matching
    'FUZZY_THRESHOLD',
    'lookup_farmacia',
    'lookup_farmacia_extended',
    'lookup_cliente_by_piva',
    '_disambiguate_multipunto',
    # Queries
    'popola_header_da_anagrafica',
    'run_lookup_batch',
    'lookup_manuale',
    'get_pending_lookup',
    'search_farmacie',
    'search_parafarmacie',
    'get_alternative_lookup_by_piva',
]
