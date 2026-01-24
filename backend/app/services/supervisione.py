# =============================================================================
# SERV.O v7.0 - SUPERVISIONE SERVICE (DEPRECATO)
# =============================================================================
# DEPRECATO: Usare app.services.supervision invece
#
# Questo modulo e mantenuto per retrocompatibilita.
# Verra rimosso nella versione 8.0.
# =============================================================================

import warnings

warnings.warn(
    "Il modulo app.services.supervisione e deprecato. "
    "Usare app.services.supervision invece.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export dalla nuova posizione
from .supervision import (
    # Costanti
    SOGLIA_PROMOZIONE,
    FASCE_NORMALIZZATE,
    # Pattern
    calcola_pattern_signature,
    normalizza_fascia_scostamento,
    genera_descrizione_pattern,
    # Requests
    crea_richiesta_supervisione,
    blocca_ordine_per_supervisione,
    sblocca_ordine_se_completo,
    # Decisions
    approva_supervisione,
    rifiuta_supervisione,
    modifica_supervisione,
    # ML
    _assicura_pattern_esistente,
    registra_approvazione_pattern,
    registra_rifiuto_pattern,
    verifica_pattern_ordinario,
    valuta_anomalia_con_apprendimento,
    log_criterio_applicato,
    # Queries
    può_emettere_tracciato,
    get_supervisioni_per_ordine,
    get_storico_criteri_applicati,
)


__all__ = [
    'SOGLIA_PROMOZIONE',
    'FASCE_NORMALIZZATE',
    'calcola_pattern_signature',
    'normalizza_fascia_scostamento',
    'genera_descrizione_pattern',
    'crea_richiesta_supervisione',
    'blocca_ordine_per_supervisione',
    'sblocca_ordine_se_completo',
    'approva_supervisione',
    'rifiuta_supervisione',
    'modifica_supervisione',
    '_assicura_pattern_esistente',
    'registra_approvazione_pattern',
    'registra_rifiuto_pattern',
    'verifica_pattern_ordinario',
    'valuta_anomalia_con_apprendimento',
    'log_criterio_applicato',
    'può_emettere_tracciato',
    'get_supervisioni_per_ordine',
    'get_storico_criteri_applicati',
]
