# =============================================================================
# SERV.O v7.0 - SUPERVISION SERVICE PACKAGE
# =============================================================================
# Servizio supervisione decomposto in moduli:
#   supervision/constants.py  - Costanti e soglie
#   supervision/patterns.py   - Pattern signature e fasce
#   supervision/requests.py   - Gestione richieste supervisione
#   supervision/decisions.py  - Decisioni (approve/reject/modify)
#   supervision/ml.py         - Machine learning e criteri ordinari
#   supervision/queries.py    - Query e ricerche
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
]
