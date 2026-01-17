# =============================================================================
# SERV.O v7.0 - ORDERS SERVICE PACKAGE
# =============================================================================
# Servizio ordini decomposto in moduli:
#   orders/queries.py     - Funzioni di lettura (get_*)
#   orders/commands.py    - Funzioni di modifica (update_*, delete_*, create_*)
#   orders/fulfillment.py - Conferma righe, evasioni, supervisione
#
# Re-export per retrocompatibilità con ordini.py
# =============================================================================

# Query functions
from .queries import (
    get_ordini,
    get_ordine_detail,
    get_ordine_righe,
    get_riga_dettaglio,
    get_stato_righe_ordine,
    get_ordini_recenti,
    get_anomalie,
    get_anomalie_by_ordine,
    get_anomalie_critiche,
    get_dashboard_stats,
)

# Command functions
from .commands import (
    update_ordine_stato,
    delete_ordine,
    modifica_riga_dettaglio,
    update_anomalia_stato,
    create_anomalia,
)

# Fulfillment functions
from .fulfillment import (
    conferma_singola_riga,
    conferma_ordine_completo,
    registra_evasione,
    ripristina_riga,
    ripristina_ordine,
    crea_o_recupera_supervisione,
    fix_stati_righe,
)

# Upload functions
from .uploads import (
    get_recent_uploads,
    get_upload_stats,
    get_vendors,
)


__all__ = [
    # Queries
    'get_ordini',
    'get_ordine_detail',
    'get_ordine_righe',
    'get_riga_dettaglio',
    'get_stato_righe_ordine',
    'get_ordini_recenti',
    'get_anomalie',
    'get_anomalie_by_ordine',
    'get_anomalie_critiche',
    'get_dashboard_stats',
    # Commands
    'update_ordine_stato',
    'delete_ordine',
    'modifica_riga_dettaglio',
    'update_anomalia_stato',
    'create_anomalia',
    # Fulfillment
    'conferma_singola_riga',
    'conferma_ordine_completo',
    'registra_evasione',
    'ripristina_riga',
    'ripristina_ordine',
    'crea_o_recupera_supervisione',
    'fix_stati_righe',
    # Uploads
    'get_recent_uploads',
    'get_upload_stats',
    'get_vendors',
]
