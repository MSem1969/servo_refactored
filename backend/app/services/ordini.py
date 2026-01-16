# =============================================================================
# SERV.O v7.0 - ORDINI SERVICE (DEPRECATO)
# =============================================================================
# DEPRECATO: Usare app.services.orders invece
#
# Questo modulo è mantenuto per retrocompatibilità.
# Verrà rimosso nella versione 8.0.
# =============================================================================

import warnings

warnings.warn(
    "Il modulo app.services.ordini è deprecato. "
    "Usare app.services.orders invece.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export dalla nuova posizione
from .orders import (
    # Queries
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
    # Commands
    update_ordine_stato,
    delete_ordine,
    modifica_riga_dettaglio,
    update_anomalia_stato,
    create_anomalia,
    # Fulfillment
    conferma_singola_riga,
    conferma_ordine_completo,
    registra_evasione,
    ripristina_riga,
    ripristina_ordine,
    crea_o_recupera_supervisione,
    fix_stati_righe,
)

# Helper interno (non documentato, usato da vecchio codice)
from .orders.fulfillment import _aggiorna_contatori_ordine

# JSON serializer (usato da vecchio codice)
from .orders.commands import _json_serializer


__all__ = [
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
    'update_ordine_stato',
    'delete_ordine',
    'modifica_riga_dettaglio',
    'update_anomalia_stato',
    'create_anomalia',
    'conferma_singola_riga',
    'conferma_ordine_completo',
    'registra_evasione',
    'ripristina_riga',
    'ripristina_ordine',
    'crea_o_recupera_supervisione',
    'fix_stati_righe',
    '_aggiorna_contatori_ordine',
    '_json_serializer',
]
