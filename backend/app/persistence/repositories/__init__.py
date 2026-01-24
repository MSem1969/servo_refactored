# =============================================================================
# SERV.O v11.0 - REPOSITORIES PACKAGE
# =============================================================================
# Repository pattern per accesso database
# v11.0: TIER 3.3 - Unified criteri_ordinari repository
#
# Struttura:
#   - base.py: BaseRepository con CRUD generici
#   - ordini.py: OrdiniRepository
#   - supervisione.py: SupervisioneEspositoreRepository, etc.
#   - anomalie.py: AnomalieRepository
#   - lookup.py: FarmacieRepository, ParafarmacieRepository
#   - criteri.py: CriteriOrdinariBase, CriteriOrdinariFactory (v11.0)
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
    CriteriOrdinariRepository,  # v11.0: Alias for CriteriOrdinariBase
    farmacie_repository,
    parafarmacie_repository,
    criteri_espositore_repository,
    criteri_listino_repository,
    criteri_lookup_repository,
)

# Criteri Ordinari (v11.0 - unified)
from .criteri import (
    CriteriOrdinariBase,
    CriteriOrdinariFactory,
    CriteriEspositoreRepository,
    CriteriListinoRepository,
    CriteriLookupRepository,
    CriteriAicRepository,
    get_criteri_espositore_repo,
    get_criteri_listino_repo,
    get_criteri_lookup_repo,
    get_criteri_aic_repo,
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
    'CriteriOrdinariRepository',  # v11.0: Alias
    'farmacie_repository',
    'parafarmacie_repository',
    'criteri_espositore_repository',
    'criteri_listino_repository',
    'criteri_lookup_repository',
    # Criteri (v11.0)
    'CriteriOrdinariBase',
    'CriteriOrdinariFactory',
    'CriteriEspositoreRepository',
    'CriteriListinoRepository',
    'CriteriLookupRepository',
    'CriteriAicRepository',
    'get_criteri_espositore_repo',
    'get_criteri_listino_repo',
    'get_criteri_lookup_repo',
    'get_criteri_aic_repo',
]
