# =============================================================================
# TO_EXTRACTOR v6.0 - Package principale
# =============================================================================

from .config import config, PROVINCE_MAP, SUPPORTED_VENDORS
from .database_pg import init_database, get_db, get_stats, get_vendor_id
from .utils import (
    parse_date,
    parse_decimal,
    parse_int,
    normalize_aic,
    normalize_piva,
    provincia_nome_to_sigla,
    compute_file_hash,
    detect_vendor,
)

__version__ = "6.0.0"
__all__ = [
    'config',
    'PROVINCE_MAP',
    'SUPPORTED_VENDORS',
    'init_database',
    'get_db',
    'get_stats',
    'get_vendor_id',
    'parse_date',
    'parse_decimal',
    'parse_int',
    'normalize_aic',
    'normalize_piva',
    'provincia_nome_to_sigla',
    'compute_file_hash',
    'detect_vendor',
]
