# =============================================================================
# SERV.O v7.0 - UTILS PACKAGE
# =============================================================================
# Re-export di tutte le funzioni per retrocompatibilità
#
# Nuova struttura:
#   utils/dates.py       - parse_date, format_date_for_tracciato
#   utils/conversions.py - parse_decimal, parse_int, parse_float
#   utils/codes.py       - normalize_aic, normalize_piva, format_piva, etc.
#   utils/province.py    - provincia_nome_to_sigla, sigla_to_provincia_nome
#   utils/hashing.py     - compute_file_hash, compute_string_hash
#   utils/text.py        - clean_text, extract_cap, extract_piva
#   utils/keys.py        - generate_order_key
#   utils/quantities.py  - calcola_q_totale
#   utils/response.py    - success_response, error_response, etc.
#   utils/db_helpers.py  - rows_to_dicts, row_to_dict
#   utils/validation.py  - validate_stato, validate_file_extension
#   utils/vendor.py      - is_vendor_piva
# =============================================================================

# Date functions
from .dates import (
    parse_date,
    format_date_for_tracciato,
)

# Conversion functions
from .conversions import (
    parse_decimal,
    parse_int,
    parse_float,
)

# Code normalization functions
from .codes import (
    normalize_aic_simple,
    normalize_aic,
    normalize_piva,
    format_piva,
    is_valid_piva,
    is_valid_aic,
)

# Province functions
from .province import (
    provincia_nome_to_sigla,
    sigla_to_provincia_nome,
)

# Hashing functions
from .hashing import (
    compute_file_hash,
    compute_string_hash,
)

# Text functions
from .text import (
    clean_text,
    extract_cap,
    extract_piva,
)

# Key generation
from .keys import (
    generate_order_key,
)

# Quantity calculation
from .quantities import (
    calcola_q_totale,
)

# Response builders
from .response import (
    success_response,
    error_response,
    paginated_response,
    batch_result,
)

# DB helpers
from .db_helpers import (
    rows_to_dicts,
    row_to_dict,
)

# Validation
from .validation import (
    validate_stato,
    validate_file_extension,
)

# Vendor helpers
from .vendor import (
    is_vendor_piva,
)

# DEPRECATO: detect_vendor è ora in services.extraction.detector
# Mantenuto per retrocompatibilità
def detect_vendor(text: str, filename: str = ""):
    """
    DEPRECATO: Usare app.services.extraction.detect_vendor
    """
    import warnings
    warnings.warn(
        "detect_vendor in utils è deprecato. "
        "Usare app.services.extraction.detect_vendor",
        DeprecationWarning,
        stacklevel=2
    )
    from ..services.extraction import detect_vendor as _detect_vendor
    return _detect_vendor(text, filename)


__all__ = [
    # Dates
    'parse_date',
    'format_date_for_tracciato',
    # Conversions
    'parse_decimal',
    'parse_int',
    'parse_float',
    # Codes
    'normalize_aic_simple',
    'normalize_aic',
    'normalize_piva',
    'format_piva',
    'is_valid_piva',
    'is_valid_aic',
    # Province
    'provincia_nome_to_sigla',
    'sigla_to_provincia_nome',
    # Hashing
    'compute_file_hash',
    'compute_string_hash',
    # Text
    'clean_text',
    'extract_cap',
    'extract_piva',
    # Keys
    'generate_order_key',
    # Quantities
    'calcola_q_totale',
    # Response
    'success_response',
    'error_response',
    'paginated_response',
    'batch_result',
    # DB helpers
    'rows_to_dicts',
    'row_to_dict',
    # Validation
    'validate_stato',
    'validate_file_extension',
    # Vendor
    'is_vendor_piva',
    # DEPRECATO
    'detect_vendor',
]
