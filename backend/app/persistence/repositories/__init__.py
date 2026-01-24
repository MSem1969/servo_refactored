# =============================================================================
# SERV.O v8.1 - REPOSITORIES PACKAGE
# =============================================================================
# Repository pattern per accesso database
#
# Struttura:
#   - base.py: BaseRepository con CRUD generici
#   - ordini.py: OrdiniRepository
#   - supervisione.py: SupervisioneEspositoreRepository, etc.
#   - anomalie.py: AnomalieRepository
#   - lookup.py: FarmacieRepository, ParafarmacieRepository
# =============================================================================

# Base
from .base import BaseRepository

# Ordini
from .ordini import (
    OrdiniRepository,
    ordini_repository,
)

# Supervisione
from .supervisione import (
    SupervisioneEspositoreRepository,
    SupervisioneListinoRepository,
    SupervisioneLookupRepository,
    supervisione_espositore_repository,
    supervisione_listino_repository,
    supervisione_lookup_repository,
)

# Anomalie
from .anomalie import (
    AnomalieRepository,
    anomalie_repository,
)

# Lookup (Anagrafica)
from .lookup import (
    FarmacieRepository,
    ParafarmacieRepository,
    CriteriOrdinariRepository,
    farmacie_repository,
    parafarmacie_repository,
    criteri_espositore_repository,
    criteri_listino_repository,
    criteri_lookup_repository,
)


__all__ = [
    # Base
    'BaseRepository',
    # Ordini
    'OrdiniRepository',
    'ordini_repository',
    # Supervisione
    'SupervisioneEspositoreRepository',
    'SupervisioneListinoRepository',
    'SupervisioneLookupRepository',
    'supervisione_espositore_repository',
    'supervisione_listino_repository',
    'supervisione_lookup_repository',
    # Anomalie
    'AnomalieRepository',
    'anomalie_repository',
    # Lookup
    'FarmacieRepository',
    'ParafarmacieRepository',
    'CriteriOrdinariRepository',
    'farmacie_repository',
    'parafarmacie_repository',
    'criteri_espositore_repository',
    'criteri_listino_repository',
    'criteri_lookup_repository',
]
