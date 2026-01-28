# =============================================================================
# SERV.O v8.2 - ANAGRAFICA SERVICES
# =============================================================================
# Unifica funzioni legacy (import CSV) e nuove (sync Ministero)
# =============================================================================

# ---- Funzioni Legacy (import CSV) ----
from .legacy import (
    import_anagrafica_farmacie,
    import_anagrafica_parafarmacie,
    get_anagrafica_stats,
    search_anagrafica,
    get_farmacia_by_id,
    get_parafarmacia_by_id,
    get_farmacia_by_min_id,
    get_farmacia_by_piva,
    clear_anagrafica_farmacie,
    clear_anagrafica_parafarmacie,
    import_anagrafica_clienti,
    get_clienti_stats,
    clear_anagrafica_clienti,
    # v11.4: Revisione automatica depositi
    revisiona_ordini_deposito_mancante,
)

# ---- Funzioni Sync Ministero (v8.2) ----
from .sync_ministero import (
    # Tipi
    TipoAnagrafica,
    SyncResult,
    SyncAllResult,
    # Funzioni sync
    sync_farmacie,
    sync_parafarmacie,
    sync_all,
    # Utilities
    check_sync_status,
    get_subentri_recenti,
    get_url_for_date,
    find_latest_available_url,
)

__all__ = [
    # Legacy - Import CSV
    'import_anagrafica_farmacie',
    'import_anagrafica_parafarmacie',
    'get_anagrafica_stats',
    'search_anagrafica',
    'get_farmacia_by_id',
    'get_parafarmacia_by_id',
    'get_farmacia_by_min_id',
    'get_farmacia_by_piva',
    'clear_anagrafica_farmacie',
    'clear_anagrafica_parafarmacie',
    'import_anagrafica_clienti',
    'get_clienti_stats',
    'clear_anagrafica_clienti',
    # v11.4: Revisione automatica depositi
    'revisiona_ordini_deposito_mancante',
    # Sync Ministero (v8.2)
    'TipoAnagrafica',
    'SyncResult',
    'SyncAllResult',
    'sync_farmacie',
    'sync_parafarmacie',
    'sync_all',
    'check_sync_status',
    'get_subentri_recenti',
    'get_url_for_date',
    'find_latest_available_url',
]
