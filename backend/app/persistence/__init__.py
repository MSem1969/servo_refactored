# =============================================================================
# SERV.O v7.0 - PERSISTENCE PACKAGE
# =============================================================================
# Layer di persistenza unificato
#
# Nuova struttura (v7.0):
#   persistence/connection.py    - Pool e connessioni PostgreSQL
#   persistence/repositories/    - Repository pattern per entità
#
# NOTA: database_pg.py rimane per retrocompatibilità
# =============================================================================

# Re-export from database_pg per retrocompatibilità
from ..database_pg import (
    init_pool,
    close_pool,
    get_db,
    get_vendor_id,
    get_stats,
    log_operation,
    init_database,
)

__all__ = [
    'init_pool',
    'close_pool',
    'get_db',
    'get_vendor_id',
    'get_stats',
    'log_operation',
    'init_database',
]
