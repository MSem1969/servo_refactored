# =============================================================================
# SERV.O v11.4 - AIC MODULE
# =============================================================================
# Modulo AIC rifattorizzato in sottomodouli:
#   aic/models.py       - Enum e dataclass
#   aic/validation.py   - Funzioni di validazione
#   aic/propagation.py  - Classe AICPropagator
#   aic/approval.py     - Approvazione/rifiuto supervisioni
#   aic/queries.py      - Query e contatori
#   aic/corrections.py  - Correzione errori AIC
#   aic/wrappers.py     - Wrapper retrocompatibili
#
# Re-export per retrocompatibilità con aic_unified.py
# =============================================================================

# Models
from .models import (
    LivelloPropagazione,
    PropagationResult,
    ResolutionResult,
)

# Validation
from .validation import (
    valida_codice_aic,
    normalizza_descrizione,
    calcola_pattern_signature,
)

# Propagation
from .propagation import AICPropagator

# Approval/Rejection
from .approval import (
    approva_supervisione_aic,
    approva_bulk_pattern_aic,
    rifiuta_supervisione_aic,
    _reset_pattern_aic,
)

# Queries
from .queries import (
    conta_anomalie_aic_aperte,
    conta_supervisioni_aic_pending,
    search_aic_suggestions,
    get_storico_modifiche_aic,
)

# Corrections
from .corrections import correggi_aic_errato

# Wrappers
from .wrappers import (
    propaga_aic,
    risolvi_anomalia_aic,
    propaga_aic_da_anomalia,
)


__all__ = [
    # Models
    'LivelloPropagazione',
    'PropagationResult',
    'ResolutionResult',
    # Validation
    'valida_codice_aic',
    'normalizza_descrizione',
    'calcola_pattern_signature',
    # Propagation
    'AICPropagator',
    # Approval
    'approva_supervisione_aic',
    'approva_bulk_pattern_aic',
    'rifiuta_supervisione_aic',
    '_reset_pattern_aic',
    # Queries
    'conta_anomalie_aic_aperte',
    'conta_supervisioni_aic_pending',
    'search_aic_suggestions',
    'get_storico_modifiche_aic',
    # Corrections
    'correggi_aic_errato',
    # Wrappers
    'propaga_aic',
    'risolvi_anomalia_aic',
    'propaga_aic_da_anomalia',
]
