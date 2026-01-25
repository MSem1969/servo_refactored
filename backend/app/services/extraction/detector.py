# =============================================================================
# SERV.O v7.0 - VENDOR DETECTOR
# =============================================================================
# Funzioni per rilevare il vendor da contenuto PDF
# Estratto da utils.py per modularità
# =============================================================================

import re
from typing import Tuple


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

    # COOPER - v11.2
    if "COOPER CONSUMER HEALTH" in t:
        return "COOPER", 0.95
    if "DE SALUTE SRL" in t and "DATI SPEDIZIONE" in t:
        return "COOPER", 0.90

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


# =============================================================================
# LISTA VENDOR SUPPORTATI
# =============================================================================

SUPPORTED_VENDORS = [
    'ANGELINI',
    'BAYER',
    'CHIESI',
    'CODIFI',
    'COOPER',
    'DOC_GENERICI',
    'MENARINI',
    'OPELLA',
]

def get_supported_vendors() -> list:
    """Ritorna lista vendor supportati."""
    return SUPPORTED_VENDORS.copy()
