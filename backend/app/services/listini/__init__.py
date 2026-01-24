# =============================================================================
# SERV.O v10.1 - LISTINI SERVICE PACKAGE
# =============================================================================
# Gestione listini prezzi per vendor
# =============================================================================

from .parsing import (
    parse_decimal_it,
    parse_prezzo_intero,
    parse_data_yyyymmdd,
    normalizza_codice_aic,
    ceil_decimal,
    scorporo_iva,
    calcola_prezzo_netto,
    arrotonda_per_ordine,
)

from .queries import (
    get_prezzo_listino,
    get_listino_vendor,
    get_listino_stats,
    search_listino,
)

from .import_csv import (
    import_listino_csv,
    aggiorna_prezzi_netti,
    VENDOR_CSV_MAPPINGS,
)

from .enrichment import (
    arricchisci_riga_con_listino,
    arricchisci_ordine_con_listino,
)

__all__ = [
    # Parsing
    'parse_decimal_it',
    'parse_prezzo_intero',
    'parse_data_yyyymmdd',
    'normalizza_codice_aic',
    'ceil_decimal',
    'scorporo_iva',
    'calcola_prezzo_netto',
    'arrotonda_per_ordine',
    # Queries
    'get_prezzo_listino',
    'get_listino_vendor',
    'get_listino_stats',
    'search_listino',
    # Import
    'import_listino_csv',
    'aggiorna_prezzi_netti',
    'VENDOR_CSV_MAPPINGS',
    # Enrichment
    'arricchisci_riga_con_listino',
    'arricchisci_ordine_con_listino',
]
