# =============================================================================
# SERV.O v11.0 - ANOMALIES SERVICE PACKAGE
# =============================================================================
# Servizio gestione anomalie centralizzato
# v11.0: Aggiunto AnomaliaResolver (TIER 2.4)
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

# v11.0: Resolver centralizzato (TIER 2.4)
from .resolver import (
    AnomaliaResolver,
    ResolutionParams,
    ResolutionResult,
    TipoRisoluzione,
    risolvi_anomalia,
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
    # Resolver (v11.0)
    'AnomaliaResolver',
    'ResolutionParams',
    'ResolutionResult',
    'TipoRisoluzione',
    'risolvi_anomalia',
]
