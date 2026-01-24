# =============================================================================
# SERV.O v8.1 - TEST FACTORIES
# =============================================================================
# Factory Boy factories per generazione dati di test
# =============================================================================

from .ordini import OrdineFactory, RigaOrdineFactory
from .utenti import UtenteFactory

__all__ = [
    "OrdineFactory",
    "RigaOrdineFactory",
    "UtenteFactory",
]
