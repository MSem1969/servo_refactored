# =============================================================================
# TO_EXTRACTOR v6.0 - FUNZIONI UTILITÀ
# =============================================================================
# Convertito da notebook Colab - Celle 5-6
# =============================================================================

import re
import hashlib
from decimal import Decimal, InvalidOperation
from typing import Tuple, Optional

from .config import PROVINCE_MAP, VENDOR_PIVA_EXCLUDE


# =============================================================================
# PARSING DATE
# =============================================================================

def parse_date(date_str: str) -> str:
    """
    Normalizza date in formato GG/MM/AAAA.
    
    Formati supportati:
    - DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
    - DD/MM/YY (aggiunge 20)
    - YYYY-MM-DD (ISO)
    - "1 Dec 2025" (testuale)
    
    Returns:
        Data in formato DD/MM/YYYY o stringa vuota se non parsabile
    """
    if not date_str:
        return ''
    
    date_str = str(date_str).strip()
    
    # Già nel formato corretto
    if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        return date_str
    
    # DD.MM.YYYY o DD-MM-YYYY
    m = re.match(r'^(\d{2})[.\-](\d{2})[.\-](\d{4})$', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    
    # DD/MM/YY
    m = re.match(r'^(\d{2})[/.\-](\d{2})[/.\-](\d{2})$', date_str)
    if m:
        year = int(m.group(3))
        year = 2000 + year if year < 50 else 1900 + year
        return f"{m.group(1)}/{m.group(2)}/{year}"
    
    # YYYY-MM-DD (ISO)
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    
    # Formato testuale "1 Dec 2025" o "01 Dic 2025"
    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 
        'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08', 
        'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12',
        'GEN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 
        'MAG': '05', 'GIU': '06', 'LUG': '07', 'AGO': '08', 
        'SET': '09', 'OTT': '10', 'NOV': '11', 'DIC': '12',
    }
    m = re.match(r'^(\d{1,2})\s+(\w{3})\s+(\d{4})$', date_str)
    if m:
        day = int(m.group(1))
        mon = months.get(m.group(2).upper()[:3], '01')
        year = m.group(3)
        return f"{day:02d}/{mon}/{year}"
    
    # Non riconosciuto, ritorna originale
    return date_str


def format_date_for_tracciato(date_str: str) -> str:
    """
    Converte data in formato YYYYMMDD per tracciati.
    
    Args:
        date_str: Data in formato DD/MM/YYYY
        
    Returns:
        Data in formato YYYYMMDD
    """
    if not date_str:
        return ''
    
    # Normalizza prima
    date_str = parse_date(date_str)
    
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    
    return ''


# =============================================================================
# PARSING NUMERI
# =============================================================================

def parse_decimal(value: str) -> Decimal:
    """
    Converte stringa in Decimal.
    
    Gestisce:
    - Virgola come separatore decimale (italiano)
    - Punto come separatore migliaia
    - Simboli € e EUR
    """
    if not value:
        return Decimal('0')
    
    value = str(value).strip()
    
    # Rimuovi simboli valuta e spazi
    value = value.replace('€', '').replace('EUR', '').replace(' ', '')
    
    # Rimuovi caratteri non numerici eccetto , . -
    value = re.sub(r'[^\d,.\-]', '', value)
    
    if not value:
        return Decimal('0')
    
    # Gestisci formato italiano (1.234,56) vs americano (1,234.56)
    if ',' in value and '.' in value:
        # Se virgola dopo punto → italiano (1.234,56)
        if value.rfind(',') > value.rfind('.'):
            value = value.replace('.', '').replace(',', '.')
        else:
            # Americano (1,234.56)
            value = value.replace(',', '')
    elif ',' in value:
        # Solo virgola → italiano
        value = value.replace(',', '.')
    
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal('0')


def parse_int(value: str) -> int:
    """
    Converte stringa in intero.
    Rimuove tutti i caratteri non numerici.
    """
    if not value:
        return 0
    
    value = re.sub(r'[^\d]', '', str(value))
    return int(value) if value else 0


def parse_float(value: str) -> float:
    """Converte stringa in float usando parse_decimal."""
    return float(parse_decimal(value))


# =============================================================================
# NORMALIZZAZIONE CODICI
# =============================================================================

def normalize_aic_simple(codice: str) -> str:
    """
    Normalizza codice AIC a 9 cifre (versione semplice).

    Args:
        codice: Codice AIC originale

    Returns:
        AIC normalizzato a 9 cifre
    """
    codice = str(codice).strip() if codice else ''
    codice_num = re.sub(r'[^\d]', '', codice)

    if not codice_num:
        return ''

    # Normalizza a 9 cifre
    if len(codice_num) < 9:
        return codice_num.zfill(9)
    else:
        return codice_num[:9]


def normalize_aic(codice: str, descrizione: str = '') -> Tuple[str, str, bool, bool]:
    """
    Normalizza codice AIC a 9 cifre con rilevamento espositore.

    Args:
        codice: Codice AIC originale
        descrizione: Descrizione prodotto (per rilevare espositore)

    Returns:
        Tuple (aic_normalizzato, aic_originale, is_espositore, is_child)
    """
    codice = str(codice).strip() if codice else ''
    aic_orig = codice
    is_espositore = False
    is_child = False

    # Rileva espositore da codice o descrizione
    esp_pattern = r'(ESP|EXP|BANCO|EXPO)'
    if re.search(esp_pattern, codice.upper()) or \
       re.search(esp_pattern, descrizione.upper()):
        is_espositore = True

    # Usa normalize_aic_simple per la normalizzazione
    aic_norm = normalize_aic_simple(codice)

    return aic_norm, aic_orig, is_espositore, is_child


def normalize_piva(piva: str) -> str:
    """
    Normalizza P.IVA rimuovendo zeri iniziali per confronto robusto.

    Args:
        piva: P.IVA originale

    Returns:
        P.IVA senza zeri iniziali (o '0' se solo zeri)
    """
    if not piva:
        return ''

    # Rimuovi caratteri non numerici
    piva_clean = re.sub(r'[^\d]', '', str(piva).strip())

    if not piva_clean:
        return ''

    # Rimuovi zeri iniziali per confronto robusto
    return piva_clean.lstrip('0') or '0'


def format_piva(piva: str) -> str:
    """
    Formatta P.IVA come stringa di 11 caratteri con zeri iniziali.

    Se la P.IVA è più corta di 11 cifre, aggiunge zeri iniziali.
    Se più lunga, tronca a 11 cifre.
    Preserva gli zeri iniziali presenti nel documento.

    Args:
        piva: P.IVA originale (può essere con o senza zeri iniziali)

    Returns:
        P.IVA formattata a 11 cifre con padding di zeri iniziali
    """
    if not piva:
        return ''

    # Rimuovi caratteri non numerici
    piva_clean = re.sub(r'[^\d]', '', str(piva).strip())

    if not piva_clean:
        return ''

    # Normalizza a 11 cifre con padding di zeri iniziali
    if len(piva_clean) < 11:
        return piva_clean.zfill(11)
    elif len(piva_clean) > 11:
        return piva_clean[:11]

    return piva_clean


def is_valid_piva(piva: str) -> bool:
    """Verifica se P.IVA ha formato valido (11 cifre)."""
    if not piva:
        return False
    piva_clean = re.sub(r'[^\d]', '', str(piva))
    return len(piva_clean) == 11


def is_valid_aic(aic: str) -> bool:
    """Verifica se codice AIC ha formato valido (9 cifre)."""
    if not aic:
        return False
    aic_clean = re.sub(r'[^\d]', '', str(aic))
    return len(aic_clean) == 9


# =============================================================================
# NORMALIZZAZIONE PROVINCE
# =============================================================================

def provincia_nome_to_sigla(nome: str) -> str:
    """
    Converte nome provincia in sigla (2 lettere).
    
    Args:
        nome: Nome provincia (es: "Milano", "ROMA", "Pordenone")
        
    Returns:
        Sigla provincia (es: "MI", "RM", "PN")
    """
    if not nome:
        return ''
    
    nome = nome.strip().upper()
    
    # Se già sigla (2 lettere)
    if len(nome) == 2 and nome.isalpha():
        return nome
    
    # Cerca nel mapping
    sigla = PROVINCE_MAP.get(nome)
    if sigla:
        return sigla
    
    # Prova match parziale
    for prov_nome, prov_sigla in PROVINCE_MAP.items():
        if prov_nome.startswith(nome) or nome.startswith(prov_nome):
            return prov_sigla
    
    # Fallback: prime 2 lettere
    return nome[:2] if len(nome) >= 2 else ''


def sigla_to_provincia_nome(sigla: str) -> str:
    """Converte sigla provincia in nome completo."""
    if not sigla:
        return ''
    
    sigla = sigla.strip().upper()
    
    # Cerca nel mapping inverso
    for nome, sig in PROVINCE_MAP.items():
        if sig == sigla:
            return nome.title()
    
    return sigla


# =============================================================================
# HASH E FILE
# =============================================================================

def compute_file_hash(file_content: bytes) -> str:
    """
    Calcola SHA-256 del contenuto file.
    
    Args:
        file_content: Contenuto binario del file
        
    Returns:
        Hash SHA-256 in formato esadecimale
    """
    return hashlib.sha256(file_content).hexdigest()


def compute_string_hash(text: str) -> str:
    """Calcola SHA-256 di una stringa."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# =============================================================================
# VENDOR DETECTION
# =============================================================================

def detect_vendor(text: str, filename: str = "") -> Tuple[str, float]:
    """
    Rileva il vendor dal testo PDF.

    v6.2: Detection basata ESCLUSIVAMENTE su contenuto PDF.
    Il nome file viene IGNORATO per tutti i vendor.

    Args:
        text: Testo estratto dal PDF
        filename: Nome file PDF (IGNORATO - mantenuto per retrocompatibilità)

    Returns:
        Tuple (vendor_code, confidence)
        confidence: 0.0-1.0
    """
    # Normalizza per ricerca - SOLO contenuto PDF
    t = text.upper()[:5000] if text else ""
    # NOTA: filename NON viene più usato per detection (v6.2)

    # ANGELINI (ACRAF) - v6.2: Aggiunto pattern "Tipo ZT01 TransferOrder" + "Area vendite"
    if "ANGELINI" in t or "ACRAF" in t:
        return "ANGELINI", 0.95
    # Pattern specifico per T.O. ACRAF: "Tipo ZT01" + "Area vendite"
    if "TIPO ZT" in t and "AREA VENDITE" in t:
        return "ANGELINI", 0.95
    # Pattern alternativo: "Tipo ZT01 TransferOrder"
    if "ZT01" in t and "TRANSFERORDER" in t.replace(" ", ""):
        return "ANGELINI", 0.90

    # CHIESI - Pattern specifici
    if "CHIESI ITALIA" in t or "@CHIESI.COM" in t:
        return "CHIESI", 0.95
    if "02944970348" in t:  # P.IVA Chiesi
        return "CHIESI", 0.90

    # OPELLA
    if "INFORMAZIONI SULL'ORDINE" in t or "OPELLA" in t:
        return "OPELLA", 0.95

    # MENARINI
    if "MENARINI" in t or "A. MENARINI" in t:
        return "MENARINI", 0.95

    # DOC_GENERICI - Transfer Order via Grossisti (v6.2)
    # Deve essere testato PRIMA di BAYER perché entrambi usano "TRANSFER ORDER"
    doc_generici_score = _detect_doc_generici(t)
    if doc_generici_score >= 0.70:
        return "DOC_GENERICI", doc_generici_score

    # BAYER - v6.2: Detection basata su contenuto specifico
    # Pattern 1: Parola "BAYER" esplicita
    if "BAYER" in t:
        return "BAYER", 0.95

    # Pattern 2: Formato specifico BAYER Transfer Order (senza parola BAYER)
    # - "NUM. PROP. D'ORDINE" con formato IT##O-#####
    # - Blocco "COOPERATIVA/GROSSISTA" + "(SAP:"
    if "NUM" in t and "PROP" in t and "ORDINE" in t:
        # Verifica formato numero ordine BAYER: IT##O-#####
        if re.search(r'IT\d{2}O-\d+', t):
            return "BAYER", 0.95

    # Pattern 3: Combinazione "COOPERATIVA/ GROSSISTA" + SAP (tipico BAYER)
    # Formato esatto nel PDF: "COOPERATIVA/ GROSSISTA" (con spazio prima dello slash)
    if "COOPERATIVA/ GROSSISTA" in t and "(SAP:" in t:
        return "BAYER", 0.90
    # Fallback: anche senza spazio
    if "COOPERATIVA/GROSSISTA" in t and "(SAP:" in t:
        return "BAYER", 0.90

    # Pattern 4: Solo codici SAP multipli (fallback)
    if t.count("(SAP:") >= 2:
        return "BAYER", 0.85

    # CODIFI / altri con "Transfer Order"
    if "TRANSFER ORDER" in t:
        if "CODIFI" in t:
            return "CODIFI", 0.95
        # Transfer Order generico senza pattern specifici
        return "UNKNOWN", 0.50

    # v6.2: RIMOSSO fallback su filename per tutti i vendor
    # La detection deve basarsi SOLO sul contenuto del PDF

    # Non riconosciuto
    return "UNKNOWN", 0.0


def _detect_doc_generici(text: str) -> float:
    """
    Rileva Transfer Order DOC Generici (v6.2).

    Criteri cumulativi basati SOLO su contenuto PDF:
    - "TRANSFER ORDER" + "Num." (10 cifre) = +0.25
    - "Grossista" nelle prime 500 caratteri = +0.15
    - "Agente" con codice numerico = +0.15
    - "Ind.Fiscale Via" + "Ind.Consegna Merce Via" = +0.20
    - "COD. A.I.C." presente = +0.15
    - 5+ prodotti con "DOC" = +0.10

    Threshold: score >= 0.70 → DOC_GENERICI

    Args:
        text: Testo PDF uppercase

    Returns:
        Score di confidence (0.0-1.0)
    """
    score = 0.0

    # Check TRANSFER ORDER con numero 10 cifre
    if re.search(r'TRANSFER\s+ORDER\s+NUM\.\s*\d{10}', text):
        score += 0.25

    # Check Grossista (caratteristica distintiva) - nelle prime 500 char
    if re.search(r'GROSSISTA\s+[A-Z]', text[:500]):
        score += 0.15

    # Check Agente con codice 5 cifre
    if re.search(r'AGENTE\s+\d{5}', text):
        score += 0.15

    # Check indirizzi separati (CARATTERISTICA CHIAVE DOC GENERICI)
    if 'IND.FISCALE' in text and 'IND.CONSEGNA MERCE' in text:
        score += 0.20

    # Check header tabella COD. A.I.C.
    if 'COD. A.I.C.' in text:
        score += 0.15

    # Check prodotti "DOC" (frequenti nei generici)
    doc_count = len(re.findall(r'\bDOC\b', text))
    if doc_count >= 5:
        score += 0.10

    return score


def is_vendor_piva(vendor: str, piva: str) -> bool:
    """
    Verifica se una P.IVA appartiene al vendor (da escludere).
    
    Args:
        vendor: Codice vendor
        piva: P.IVA da verificare
        
    Returns:
        True se è P.IVA del vendor (non del cliente)
    """
    vendor_piva = VENDOR_PIVA_EXCLUDE.get(vendor.upper())
    if not vendor_piva:
        return False
    
    # Confronta normalizzate
    piva_norm = normalize_piva(piva)
    vendor_piva_norm = normalize_piva(vendor_piva)
    
    return piva_norm == vendor_piva_norm


# =============================================================================
# PULIZIA TESTO
# =============================================================================

def clean_text(text: str, max_length: int = None) -> str:
    """
    Pulisce e normalizza testo.
    
    - Rimuove spazi multipli
    - Rimuove caratteri di controllo
    - Tronca se necessario
    """
    if not text:
        return ''
    
    # Rimuovi caratteri di controllo
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))
    
    # Normalizza spazi
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Tronca se necessario
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def extract_cap(text: str) -> Optional[str]:
    """Estrae CAP (5 cifre) da una stringa."""
    m = re.search(r'\b(\d{5})\b', str(text))
    return m.group(1) if m else None


def extract_piva(text: str) -> Optional[str]:
    """Estrae P.IVA (11 cifre) da una stringa."""
    m = re.search(r'\b(\d{11})\b', str(text))
    return m.group(1) if m else None


# =============================================================================
# GENERAZIONE CHIAVI UNIVOCHE
# =============================================================================

def generate_order_key(vendor: str, numero_ordine: str, codice_ministeriale: str) -> str:
    """
    Genera chiave univoca per ordine.

    Format: VENDOR_NUMORDINE_CODMIN
    """
    vendor = (vendor or 'UNKNOWN').upper()
    numero = (numero_ordine or 'ND').strip()
    cod_min = (codice_ministeriale or 'NOMIN').strip()

    return f"{vendor}_{numero}_{cod_min}"


# =============================================================================
# RESPONSE BUILDERS (v6.2 - Centralized API Response Formatting)
# =============================================================================

from typing import Any, Dict, List

def success_response(data: Any = None, message: str = None, **kwargs) -> Dict[str, Any]:
    """
    Build standard success response.

    Args:
        data: Response payload
        message: Optional message
        **kwargs: Additional fields (count, pagination, etc.)

    Returns:
        Standardized success response dict
    """
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    response.update(kwargs)
    return response


def error_response(message: str, code: str = None) -> Dict[str, Any]:
    """
    Build standard error response.

    Args:
        message: Error message
        code: Optional error code

    Returns:
        Standardized error response dict
    """
    response = {"success": False, "error": message}
    if code:
        response["code"] = code
    return response


def paginated_response(
    items: List[Any],
    total: int,
    limit: int,
    offset: int
) -> Dict[str, Any]:
    """
    Build paginated response.

    Args:
        items: List of items
        total: Total count
        limit: Page size
        offset: Current offset

    Returns:
        Response with pagination metadata
    """
    pages = (total + limit - 1) // limit if limit > 0 else 1
    return {
        "success": True,
        "data": items,
        "pagination": {
            "totale": total,
            "limit": limit,
            "offset": offset,
            "pages": pages
        }
    }


def batch_result(success_count: int, total: int, errors: List[str] = None) -> Dict[str, Any]:
    """
    Build batch operation result.

    Args:
        success_count: Number of successful operations
        total: Total attempted
        errors: List of error messages

    Returns:
        Batch operation result dict
    """
    result = {
        "success": True,
        "data": {
            "completati": success_count,
            "totale": total,
            "falliti": total - success_count
        }
    }
    if errors:
        result["data"]["errori"] = errors
    return result


# =============================================================================
# DATABASE HELPERS (v6.2)
# =============================================================================

def rows_to_dicts(rows) -> List[Dict[str, Any]]:
    """
    Convert SQLite rows to list of dicts.

    Args:
        rows: SQLite cursor fetchall result

    Returns:
        List of dictionaries
    """
    if not rows:
        return []
    return [dict(row) for row in rows]


def row_to_dict(row) -> Optional[Dict[str, Any]]:
    """
    Convert single SQLite row to dict.

    Args:
        row: SQLite row object

    Returns:
        Dictionary or None
    """
    return dict(row) if row else None


# =============================================================================
# QUANTITY CALCULATION (v6.2 - Single Source of Truth)
# =============================================================================

def calcola_q_totale(riga: Dict[str, Any]) -> int:
    """
    Calcola quantità totale: venduta + sconto_merce + omaggio.

    Single source of truth per il calcolo quantità.
    Handles both dict access patterns safely.

    Args:
        riga: Dictionary con campi q_venduta, q_sconto_merce, q_omaggio

    Returns:
        Quantità totale come intero
    """
    return (
        int(riga.get('q_venduta') or 0) +
        int(riga.get('q_sconto_merce') or 0) +
        int(riga.get('q_omaggio') or 0)
    )


# =============================================================================
# VALIDATION HELPERS (v6.2)
# =============================================================================

def validate_stato(stato: str, stati_validi: List[str], nome_campo: str = "stato") -> Optional[str]:
    """
    Validate state value against allowed list.

    Args:
        stato: Value to validate
        stati_validi: List of valid values
        nome_campo: Field name for error message

    Returns:
        Error message if invalid, None if valid
    """
    if stato and stato not in stati_validi:
        return f"{nome_campo} non valido. Valori ammessi: {', '.join(stati_validi)}"
    return None


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> Optional[str]:
    """
    Validate file extension.

    Args:
        filename: File name to check
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.csv'])

    Returns:
        Error message if invalid, None if valid
    """
    if not filename:
        return "Nome file mancante"

    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    allowed = [e.lstrip('.').lower() for e in allowed_extensions]

    if ext not in allowed:
        return f"Formato non supportato. Formati ammessi: {', '.join(allowed_extensions)}"
    return None
