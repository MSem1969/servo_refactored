# =============================================================================
# SERV.O v7.0 - EXPORT SERVICE PACKAGE
# =============================================================================
# Servizio esportazione tracciati EDI decomposto in moduli:
#   export/formatters/    - Formattazione righe TO_T e TO_D
#   export/validators.py  - Validazione campi obbligatori
#   export/generator.py   - Logica generazione tracciati
#   export/queries.py     - Query per preview e storico
#
# Re-export per retrocompatibilita con tracciati.py
# =============================================================================

# Costanti formato EDI
from .formatters import (
    TO_T_LENGTH,
    TO_D_LENGTH,
    DEFAULT_VENDOR_CODE,
)

# Funzioni formattazione
from .formatters import (
    format_date_edi,
    format_float_edi,
    format_int_edi,
    generate_to_t_line,
    generate_to_d_line,
)

# Validazione
from .validators import valida_campi_tracciato

# Generazione
from .generator import (
    generate_tracciati_per_ordine,
    valida_e_genera_tracciato,
)

# Query
from .queries import (
    get_tracciato_preview,
    get_ordini_pronti_export,
    get_esportazioni_storico,
    get_file_tracciato,
)


__all__ = [
    # Costanti
    'TO_T_LENGTH',
    'TO_D_LENGTH',
    'DEFAULT_VENDOR_CODE',
    # Formattazione
    'format_date_edi',
    'format_float_edi',
    'format_int_edi',
    'generate_to_t_line',
    'generate_to_d_line',
    # Validazione
    'valida_campi_tracciato',
    # Generazione
    'generate_tracciati_per_ordine',
    'valida_e_genera_tracciato',
    # Query
    'get_tracciato_preview',
    'get_ordini_pronti_export',
    'get_esportazioni_storico',
    'get_file_tracciato',
]
