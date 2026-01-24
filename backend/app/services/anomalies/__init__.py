# =============================================================================
# SERV.O v10.1 - ANOMALIES SERVICE PACKAGE
# =============================================================================
# Servizio gestione anomalie centralizzato
# =============================================================================

from .queries import (
    get_anomalie,
    get_anomalie_by_ordine,
    get_anomalie_critiche,
    get_anomalia_detail,
    get_anomalie_stats,
)

from .commands import (
    create_anomalia,
    update_anomalia_stato,
    resolve_anomalia,
    ignore_anomalia,
    resolve_batch,
    ignore_batch,
)

from .detection import (
    detect_anomalies_for_order,
    create_lookup_anomaly,
    create_espositore_anomaly,
    create_listino_anomaly,
    ANOMALY_CODES,
    ANOMALY_LEVELS,
)

__all__ = [
    # Queries
    'get_anomalie',
    'get_anomalie_by_ordine',
    'get_anomalie_critiche',
    'get_anomalia_detail',
    'get_anomalie_stats',
    # Commands
    'create_anomalia',
    'update_anomalia_stato',
    'resolve_anomalia',
    'ignore_anomalia',
    'resolve_batch',
    'ignore_batch',
    # Detection
    'detect_anomalies_for_order',
    'create_lookup_anomaly',
    'create_espositore_anomaly',
    'create_listino_anomaly',
    'ANOMALY_CODES',
    'ANOMALY_LEVELS',
]
