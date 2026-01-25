# =============================================================================
# SERV.O v7.0 - TO_T LINE FORMATTER
# =============================================================================
# Generazione riga TO_T (testata) secondo formato EDI
# =============================================================================

import re
from typing import Dict, Any

from .common import (
    TO_T_LENGTH,
    DEFAULT_VENDOR_CODE,
    format_date_edi,
    format_float_edi,
    format_int_edi,
    get_vendor_code,
)


def generate_to_t_line(data: Dict[str, Any]) -> str:
    """
    Genera una riga TO_T (testata) secondo formato EDI.

    Schema da Scheme_EDI_TO_T.csv:
    - Pos 1-10:    Vendor (10)
    - Pos 11-40:   VendorOrderNumber (30)
    - Pos 41-60:   CustomerTraceabilityCode/MIN_ID (20)
    - Pos 61-76:   VAT code/P.IVA (16)
    - Pos 77-126:  CustomerName1/ragione_sociale (50)
    - Pos 127-176: CustomerName2 (50)
    - Pos 177-226: Address (50)
    - Pos 227-236: CodeCity/CAP (10)
    - Pos 237-286: City (50)
    - Pos 287-289: Province (3)
    - Pos 290-299: OrderDate GG/MM/AAAA (10)
    - Pos 300-309: EstDeliveryDate GG/MM/AAAA (10)
    - Pos 310-359: AgentName (50)
    - Pos 360-369: PaymentDate1 (10)
    - Pos 370-372: DelayPaymentDays (3)
    - Pos 373-382: PaymentDate2 (10)
    - Pos 383-391: PaymentAmmount2 (9: 7+2dec)
    - Pos 392-394: DelayPaymentDays2 (3)
    - Pos 395-404: PaymentDate3 (10)
    - Pos 405-413: PaymentAmmount3 (9: 7+2dec)
    - Pos 414-416: DelayPaymentDays3 (3)
    - Pos 417-436: OfferCodeCustomer (20)
    - Pos 437-456: OfferCodeVendor (20)
    - Pos 457:     ForceCheck S/N (1)
    - Pos 458-657: OrderAnnotation (200)
    - Pos 658-857: BOT_Annotation (200)
    """
    # Estrai dati
    # v11.2: Genera codice vendor dinamico da vendor + deposito
    # Formato: {PREFIX_3CHAR}_{DISTRIBUTORE} (es: ANG_FARVI, BAY_SOFAD, MEN_SAFAR)
    vendor = data.get('vendor') or ''
    deposito = data.get('deposito_riferimento') or data.get('deposito') or ''
    vendor_code = get_vendor_code(vendor, deposito)

    min_id = str(data.get('min_id') or data.get('anag_min_id') or '').strip()

    # Date in formato GG/MM/AAAA
    data_ordine = format_date_edi(data.get('data_ordine', ''))
    data_consegna = format_date_edi(data.get('data_consegna', ''))

    # Dilazione pagamento (default 90 gg)
    dilazione = data.get('gg_dilazione_1') or data.get('condizioni_pagamento') or 90
    try:
        # Se è stringa tipo "90 gg", estrai il numero
        if isinstance(dilazione, str):
            m = re.search(r'(\d+)', dilazione)
            dilazione = int(m.group(1)) if m else 90
        else:
            dilazione = int(dilazione)
    except:
        dilazione = 90

    line = ""
    # Pos 1-10: Vendor (10)
    line += vendor_code.ljust(10)[:10]
    # Pos 11-40: VendorOrderNumber (30)
    line += str(data.get('numero_ordine') or data.get('numero_ordine_vendor') or '').ljust(30)[:30]
    # Pos 41-60: CustomerTraceabilityCode/MIN_ID (20)
    line += min_id.ljust(20)[:20]
    # Pos 61-76: VAT code/P.IVA (16)
    line += str(data.get('partita_iva') or '').ljust(16)[:16]
    # Pos 77-126: CustomerName1/ragione_sociale (50)
    line += str(data.get('ragione_sociale') or '').ljust(50)[:50]
    # Pos 127-176: CustomerName2 (50)
    line += str(data.get('ragione_sociale_2') or '').ljust(50)[:50]
    # Pos 177-226: Address (50)
    line += str(data.get('indirizzo') or '').ljust(50)[:50]
    # Pos 227-236: CodeCity/CAP (10)
    line += str(data.get('cap') or '').ljust(10)[:10]
    # Pos 237-286: City (50)
    line += str(data.get('citta') or '').ljust(50)[:50]
    # Pos 287-289: Province (3)
    line += str(data.get('provincia') or '').ljust(3)[:3]
    # Pos 290-299: OrderDate GG/MM/AAAA (10)
    line += data_ordine
    # Pos 300-309: EstDeliveryDate GG/MM/AAAA (10)
    line += data_consegna
    # Pos 310-359: AgentName (50)
    line += str(data.get('nome_agente') or '').ljust(50)[:50]
    # Pos 360-369: PaymentDate1 (10) - vuoto
    line += ' ' * 10
    # Pos 370-372: DelayPaymentDays (3)
    line += format_int_edi(dilazione, 3)
    # Pos 373-382: PaymentDate2 (10) - vuoto
    line += ' ' * 10
    # Pos 383-391: PaymentAmmount2 (9: 7+2dec)
    line += format_float_edi(0, 7, 2)
    # Pos 392-394: DelayPaymentDays2 (3)
    line += format_int_edi(0, 3)
    # Pos 395-404: PaymentDate3 (10) - vuoto
    line += ' ' * 10
    # Pos 405-413: PaymentAmmount3 (9: 7+2dec)
    line += format_float_edi(0, 7, 2)
    # Pos 414-416: DelayPaymentDays3 (3)
    line += format_int_edi(0, 3)
    # Pos 417-436: OfferCodeCustomer (20) - vuoto
    line += ' ' * 20
    # Pos 437-456: OfferCodeVendor (20) - vuoto
    line += ' ' * 20
    # Pos 457: ForceCheck S/N (1)
    line += 'N'
    # Pos 458-657: OrderAnnotation (200)
    line += str(data.get('note_ordine') or '').ljust(200)[:200]
    # Pos 658-857: BOT_Annotation (200)
    line += str(data.get('note_ddt') or '').ljust(200)[:200]

    # Verifica e aggiusta lunghezza
    if len(line) < TO_T_LENGTH:
        line = line.ljust(TO_T_LENGTH)
    elif len(line) > TO_T_LENGTH:
        line = line[:TO_T_LENGTH]

    return line
