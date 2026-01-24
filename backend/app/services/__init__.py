# =============================================================================
# SERV.O v10.1 - SERVICES PACKAGE
# =============================================================================
# Export principali servizi con architettura modulare
# =============================================================================

from .pdf_processor import (
    process_pdf,
    get_recent_uploads,
    get_upload_stats,
)

from .lookup import (
    lookup_farmacia,
    run_lookup_batch,
    lookup_manuale,
    get_pending_lookup,
    search_farmacie,
    search_parafarmacie,
    fuzzy_match_address,
    fuzzy_match_full,
)

from .tracciati import (
    generate_tracciati_per_ordine,
    get_tracciato_preview,
    get_ordini_pronti_export,
    get_esportazioni_storico,
    get_file_tracciato,
    generate_to_t_line,
    generate_to_d_line,
)

from .anagrafica import (
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
)

from .ordini import (
    get_ordini,
    get_ordine_detail,
    get_ordine_righe,
    update_ordine_stato,
    delete_ordine,
    get_anomalie,
    get_anomalie_by_ordine,
    update_anomalia_stato,
    get_dashboard_stats,
)

# v10.1: Service Registry with dependency injection
from .registry import (
    registry,
    ServiceRegistry,
    inject,
    get_orders_service,
    get_anomalies_service,
    get_supervision_service,
    get_extraction_service,
    get_export_service,
    get_lookup_service,
    get_listini_service,
    get_espositori_service,
)

# v10.1: Modular service packages
from . import anomalies
from . import espositori
from . import listini

__all__ = [
    # PDF Processor
    'process_pdf',
    'get_recent_uploads',
    'get_upload_stats',

    # Lookup
    'lookup_farmacia',
    'run_lookup_batch',
    'lookup_manuale',
    'get_pending_lookup',
    'search_farmacie',
    'search_parafarmacie',
    'fuzzy_match_address',
    'fuzzy_match_full',

    # Tracciati
    'generate_tracciati_per_ordine',
    'get_tracciato_preview',
    'get_ordini_pronti_export',
    'get_esportazioni_storico',
    'get_file_tracciato',
    'generate_to_t_line',
    'generate_to_d_line',

    # Anagrafica
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

    # Ordini
    'get_ordini',
    'get_ordine_detail',
    'get_ordine_righe',
    'update_ordine_stato',
    'delete_ordine',
    'get_anomalie',
    'get_anomalie_by_ordine',
    'update_anomalia_stato',
    'get_dashboard_stats',

    # Service Registry (v10.1)
    'registry',
    'ServiceRegistry',
    'inject',
    'get_orders_service',
    'get_anomalies_service',
    'get_supervision_service',
    'get_extraction_service',
    'get_export_service',
    'get_lookup_service',
    'get_listini_service',
    'get_espositori_service',

    # Modular packages (v10.1)
    'anomalies',
    'espositori',
    'listini',
]
