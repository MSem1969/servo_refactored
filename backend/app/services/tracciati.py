# =============================================================================
# SERV.O v7.0 - TRACCIATI SERVICE (DEPRECATO)
# =============================================================================
# DEPRECATO: Usare app.services.export invece
#
# Questo modulo e mantenuto per retrocompatibilita.
# Verra rimosso nella versione 8.0.
# =============================================================================

import warnings

warnings.warn(
    "Il modulo app.services.tracciati e deprecato. "
    "Usare app.services.export invece.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export dalla nuova posizione
from .export import (
    # Costanti
    TO_T_LENGTH,
    TO_D_LENGTH,
    DEFAULT_VENDOR_CODE,
    # Formattazione
    format_date_edi,
    format_float_edi,
    format_int_edi,
    generate_to_t_line,
    generate_to_d_line,
    # Validazione
    valida_campi_tracciato,
    # Generazione
    generate_tracciati_per_ordine,
    valida_e_genera_tracciato,
    # Query
    get_tracciato_preview,
    get_ordini_pronti_export,
    get_esportazioni_storico,
    get_file_tracciato,
)


__all__ = [
    'TO_T_LENGTH',
    'TO_D_LENGTH',
    'DEFAULT_VENDOR_CODE',
    'format_date_edi',
    'format_float_edi',
    'format_int_edi',
    'generate_to_t_line',
    'generate_to_d_line',
    'valida_campi_tracciato',
    'generate_tracciati_per_ordine',
    'valida_e_genera_tracciato',
    'get_tracciato_preview',
    'get_ordini_pronti_export',
    'get_esportazioni_storico',
    'get_file_tracciato',
]
