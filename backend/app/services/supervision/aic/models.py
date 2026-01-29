# =============================================================================
# SERV.O v11.4 - AIC MODELS
# =============================================================================
# Enums e dataclass per il modulo AIC
# =============================================================================

from typing import Dict, List
from enum import Enum
from dataclasses import dataclass


class LivelloPropagazione(str, Enum):
    """
    Livelli di propagazione AIC.

    ORDINE: Propaga a tutte le righe dell'ordine con stessa descrizione
    GLOBALE: Propaga a tutte le anomalie aperte stesso vendor con stessa descrizione
    """
    ORDINE = 'ORDINE'
    GLOBALE = 'GLOBALE'


@dataclass
class PropagationResult:
    """Risultato di una propagazione AIC."""
    success: bool
    righe_aggiornate: int = 0
    ordini_coinvolti: List[int] = None
    descrizione_normalizzata: str = ''
    codice_aic: str = ''
    livello: str = ''
    error: str = ''

    def __post_init__(self):
        if self.ordini_coinvolti is None:
            self.ordini_coinvolti = []

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'righe_aggiornate': self.righe_aggiornate,
            'ordini_coinvolti': self.ordini_coinvolti,
            'descrizione_normalizzata': self.descrizione_normalizzata,
            'codice_aic': self.codice_aic,
            'livello': self.livello,
            'error': self.error
        }


@dataclass
class ResolutionResult(PropagationResult):
    """Risultato di una risoluzione anomalia/supervisione."""
    anomalia_risolta: bool = False
    id_anomalia: int = None
    supervisioni_approvate: int = 0
    ml_pattern_incrementato: bool = False

    def to_dict(self) -> Dict:
        result = super().to_dict()
        result.update({
            'anomalia_risolta': self.anomalia_risolta,
            'id_anomalia': self.id_anomalia,
            'supervisioni_approvate': self.supervisioni_approvate,
            'ml_pattern_incrementato': self.ml_pattern_incrementato
        })
        return result
