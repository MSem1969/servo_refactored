# =============================================================================
# TO_EXTRACTOR v6.2 - CONFIGURAZIONE (PostgreSQL)
# =============================================================================
# Migrazione da SQLite a PostgreSQL per supporto multiutenza
# =============================================================================

import os
from typing import Dict

# Carica variabili ambiente da .env se presente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv non installato, usa solo os.getenv

# =============================================================================
# CONFIGURAZIONE PRINCIPALE
# =============================================================================

class Settings:
    """Configurazione globale dell'applicazione."""

    # Database PostgreSQL
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_DATABASE: str = os.getenv("PG_DATABASE", "to_extractor")
    PG_USER: str = os.getenv("PG_USER", "to_extractor_user")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "")

    # SQLite (mantenuto per compatibilita/migrazione)
    DB_PATH: str = os.getenv("DB_PATH", "extractor_to.db")

    # Selettore database: "postgresql" o "sqlite"
    DB_TYPE: str = os.getenv("DB_TYPE", "postgresql")

    # Parametri default
    GG_DILAZIONE_DEFAULT: int = 90
    FUZZY_THRESHOLD: int = 60  # Soglia minima per match fuzzy

    # Tracciati
    TO_T_LENGTH: int = 477  # Lunghezza riga TO_T (testata)
    TO_D_LENGTH: int = 405  # Lunghezza riga TO_D (dettaglio)
    ENCODING: str = "utf-8"

    # Directory
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")

    # Limiti
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # Alias per compatibilita

    # Versione
    VERSION: str = "6.2.0-pg"
    APP_NAME: str = "TO_EXTRACTOR"


# Istanza singleton
config = Settings()


# =============================================================================
# MAPPING PROVINCE ITALIANE
# =============================================================================

PROVINCE_MAP: Dict[str, str] = {
    # A
    'AGRIGENTO': 'AG', 'ALESSANDRIA': 'AL', 'ANCONA': 'AN', 'AOSTA': 'AO',
    'AREZZO': 'AR', 'ASCOLI PICENO': 'AP', 'ASTI': 'AT', 'AVELLINO': 'AV',
    # B
    'BARI': 'BA', 'BARLETTA': 'BT', 'BARLETTA-ANDRIA-TRANI': 'BT',
    'BELLUNO': 'BL', 'BENEVENTO': 'BN', 'BERGAMO': 'BG', 'BIELLA': 'BI',
    'BOLOGNA': 'BO', 'BOLZANO': 'BZ', 'BRESCIA': 'BS', 'BRINDISI': 'BR',
    # C
    'CAGLIARI': 'CA', 'CALTANISSETTA': 'CL', 'CAMPOBASSO': 'CB',
    'CASERTA': 'CE', 'CATANIA': 'CT', 'CATANZARO': 'CZ', 'CHIETI': 'CH',
    'COMO': 'CO', 'COSENZA': 'CS', 'CREMONA': 'CR', 'CROTONE': 'KR',
    'CUNEO': 'CN',
    # E
    'ENNA': 'EN',
    # F
    'FERMO': 'FM', 'FERRARA': 'FE', 'FIRENZE': 'FI', 'FOGGIA': 'FG',
    'FORLI': 'FC', 'FORLI-CESENA': 'FC', 'FROSINONE': 'FR',
    # G
    'GENOVA': 'GE', 'GORIZIA': 'GO', 'GROSSETO': 'GR',
    # I
    'IMPERIA': 'IM', 'ISERNIA': 'IS',
    # L
    "L'AQUILA": 'AQ', 'AQUILA': 'AQ', 'LA SPEZIA': 'SP', 'LATINA': 'LT',
    'LECCE': 'LE', 'LECCO': 'LC', 'LIVORNO': 'LI', 'LODI': 'LO',
    'LUCCA': 'LU',
    # M
    'MACERATA': 'MC', 'MANTOVA': 'MN', 'MASSA': 'MS', 'MASSA-CARRARA': 'MS',
    'MATERA': 'MT', 'MESSINA': 'ME', 'MILANO': 'MI', 'MODENA': 'MO',
    'MONZA': 'MB', 'MONZA E BRIANZA': 'MB',
    # N
    'NAPOLI': 'NA', 'NOVARA': 'NO', 'NUORO': 'NU',
    # O
    'ORISTANO': 'OR',
    # P
    'PADOVA': 'PD', 'PALERMO': 'PA', 'PARMA': 'PR', 'PAVIA': 'PV',
    'PERUGIA': 'PG', 'PESARO': 'PU', 'PESARO E URBINO': 'PU',
    'PESCARA': 'PE', 'PIACENZA': 'PC', 'PISA': 'PI', 'PISTOIA': 'PT',
    'PORDENONE': 'PN', 'POTENZA': 'PZ', 'PRATO': 'PO',
    # R
    'RAGUSA': 'RG', 'RAVENNA': 'RA', 'REGGIO CALABRIA': 'RC',
    'REGGIO EMILIA': 'RE', 'RIETI': 'RI', 'RIMINI': 'RN', 'ROMA': 'RM',
    'ROVIGO': 'RO',
    # S
    'SALERNO': 'SA', 'SASSARI': 'SS', 'SAVONA': 'SV', 'SIENA': 'SI',
    'SIRACUSA': 'SR', 'SONDRIO': 'SO', 'SUD SARDEGNA': 'SU',
    # T
    'TARANTO': 'TA', 'TERAMO': 'TE', 'TERNI': 'TR', 'TORINO': 'TO',
    'TRAPANI': 'TP', 'TRENTO': 'TN', 'TREVISO': 'TV', 'TRIESTE': 'TS',
    # U
    'UDINE': 'UD',
    # V
    'VARESE': 'VA', 'VENEZIA': 'VE', 'VERBANIA': 'VB',
    'VERBANO-CUSIO-OSSOLA': 'VB', 'VERCELLI': 'VC', 'VERONA': 'VR',
    'VIBO VALENTIA': 'VV', 'VICENZA': 'VI', 'VITERBO': 'VT',
}


# =============================================================================
# VENDOR SUPPORTATI
# =============================================================================

SUPPORTED_VENDORS = [
    'ANGELINI',
    'BAYER', 
    'CHIESI',
    'CODIFI',
    'MENARINI',
    'OPELLA',
]


# =============================================================================
# P.IVA VENDOR DA ESCLUDERE
# =============================================================================

VENDOR_PIVA_EXCLUDE = {
    'CHIESI': '02944970348',  # P.IVA Chiesi - non è del cliente!
}


# =============================================================================
# STATI ORDINI E ANOMALIE (v6.2 - Centralized Constants)
# =============================================================================

ORDINE_STATI = ['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO', 'PENDING_REVIEW']
ANOMALIA_STATI = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
SUPERVISIONE_STATI = ['PENDING', 'APPROVED', 'REJECTED', 'MODIFIED']
RIGA_STATI = ['ESTRATTO', 'CONFERMATO', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO', 'IN_SUPERVISIONE', 'SUPERVISIONATO']

ANOMALIA_TIPI = [
    'LOOKUP', 'ESPOSITORE', 'CHILD', 'NO_AIC', 'PIVA_MULTIPUNTO',
    'VALIDAZIONE', 'DUPLICATO_PDF', 'DUPLICATO_ORDINE', 'ALTRO'
]
ANOMALIA_LIVELLI = ['INFO', 'ATTENZIONE', 'ERRORE', 'CRITICO']

# Fasce scostamento espositore che richiedono supervisione
FASCE_SUPERVISIONE_OBBLIGATORIA = ['MANCANTE', 'ECCESSO_GRAVE', 'DEFICIT_GRAVE']


# =============================================================================
# CODICI ANOMALIA ESPOSITORE
# =============================================================================

CODICI_ANOMALIA_ESPOSITORE = {
    'ESP-A01': 'Espositore incompleto - pezzi mancanti',
    'ESP-A02': 'Espositore con pezzi in eccesso',
    'ESP-A03': 'Espositore senza righe child',
    'ESP-A04': 'Espositore chiuso per nuovo parent',
    'ESP-A05': 'Espositore chiuso forzatamente',
}
