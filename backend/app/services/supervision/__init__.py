# =============================================================================
# SERV.O v11.0 - SUPERVISION SERVICE PACKAGE
# =============================================================================
# Servizio supervisione decomposto in moduli:
#   supervision/constants.py      - Costanti e soglie
#   supervision/patterns.py       - Pattern signature e fasce
#   supervision/requests.py       - Gestione richieste supervisione
#   supervision/decisions.py      - Decisioni (approve/reject/modify)
#   supervision/ml.py             - Machine learning e criteri ordinari
#   supervision/queries.py        - Query e ricerche
#   supervision/aic_unified.py    - [v11] Servizio AIC unificato
#
# Re-export per retrocompatibilita con supervisione.py
# =============================================================================

# Costanti
from .constants import SOGLIA_PROMOZIONE, SOGLIA_PROMOZIONE_ORDINARIA, FASCE_NORMALIZZATE

# Pattern
from .patterns import (
    calcola_pattern_signature,
    normalizza_fascia_scostamento,
    genera_descrizione_pattern,
)

# Requests
from .requests import (
    crea_richiesta_supervisione,
    blocca_ordine_per_supervisione,
    sblocca_ordine_se_completo,
)

# Decisions
from .decisions import (
    approva_supervisione,
    rifiuta_supervisione,
    modifica_supervisione,
)

# Machine Learning
from .ml import (
    _assicura_pattern_esistente,
    registra_approvazione_pattern,
    registra_rifiuto_pattern,
    verifica_pattern_ordinario,
    valuta_anomalia_con_apprendimento,
    log_criterio_applicato,
    # Listino ML
    verifica_pattern_listino_ordinario,
    registra_approvazione_pattern_listino,
)

# Queries
from .queries import (
    può_emettere_tracciato,
    get_supervisioni_per_ordine,
    get_storico_criteri_applicati,
)

# v11.4 - AIC Unified Service (centralizza propagazione_aic.py e aic.py - REFACTORING)
from .aic_unified import (
    # Classe principale
    AICPropagator,
    # Enums e dataclass
    LivelloPropagazione,
    PropagationResult,
    ResolutionResult,
    # Funzioni di utilità
    valida_codice_aic,
    normalizza_descrizione,
    calcola_pattern_signature as calcola_pattern_signature_aic,
    # Wrapper retrocompatibili
    propaga_aic,
    propaga_aic_da_anomalia,  # v11.4: migrato da propagazione_aic.py
    risolvi_anomalia_aic,
    approva_supervisione_aic,
    approva_bulk_pattern_aic,
    rifiuta_supervisione_aic,  # v11.4: migrato da aic.py
    search_aic_suggestions,  # v11.4: migrato da aic.py
    # Correzione errori AIC
    correggi_aic_errato,  # v11.4: migrato da propagazione_aic.py
    get_storico_modifiche_aic,  # v11.4: migrato da propagazione_aic.py
    # Contatori
    conta_anomalie_aic_aperte,
    conta_supervisioni_aic_pending,
)


__all__ = [
    # Costanti
    'SOGLIA_PROMOZIONE',
    'SOGLIA_PROMOZIONE_ORDINARIA',
    'FASCE_NORMALIZZATE',
    # Pattern
    'calcola_pattern_signature',
    'normalizza_fascia_scostamento',
    'genera_descrizione_pattern',
    # Requests
    'crea_richiesta_supervisione',
    'blocca_ordine_per_supervisione',
    'sblocca_ordine_se_completo',
    # Decisions
    'approva_supervisione',
    'rifiuta_supervisione',
    'modifica_supervisione',
    # ML
    '_assicura_pattern_esistente',
    'registra_approvazione_pattern',
    'registra_rifiuto_pattern',
    'verifica_pattern_ordinario',
    'valuta_anomalia_con_apprendimento',
    'log_criterio_applicato',
    # Listino ML
    'verifica_pattern_listino_ordinario',
    'registra_approvazione_pattern_listino',
    # Queries
    'può_emettere_tracciato',
    'get_supervisioni_per_ordine',
    'get_storico_criteri_applicati',
    # v11.4 - AIC Unified (refactoring completo)
    'AICPropagator',
    'LivelloPropagazione',
    'PropagationResult',
    'ResolutionResult',
    'valida_codice_aic',
    'normalizza_descrizione',
    'calcola_pattern_signature_aic',
    'propaga_aic',
    'propaga_aic_da_anomalia',
    'risolvi_anomalia_aic',
    'approva_supervisione_aic',
    'approva_bulk_pattern_aic',
    'rifiuta_supervisione_aic',
    'search_aic_suggestions',
    'correggi_aic_errato',
    'get_storico_modifiche_aic',
    'conta_anomalie_aic_aperte',
    'conta_supervisioni_aic_pending',
]
