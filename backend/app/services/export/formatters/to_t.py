# =============================================================================
# SERV.O v11.3 - TO_T LINE FORMATTER
# =============================================================================
# Generazione riga TO_T (testata) secondo formato EDI
# v11.3: Corretto schema 869 char, UPPERCASE, formato pagamenti
# =============================================================================

import re
from datetime import date
from typing import Dict, Any

from .common import (
    TO_T_LENGTH,
    DEFAULT_VENDOR_CODE,
    format_date_edi,
    get_vendor_code,
)


def _format_importo_7_2(value: float = 0) -> str:
    """
    Formatta importo con formato 7.2 = 10 caratteri totali.
    7 interi + "." + 2 decimali = "0000000.00"
    """
    if value is None:
        value = 0.0
    try:
        value = float(value)
    except:
        value = 0.0
    # Formato: 7 cifre intere, punto, 2 decimali = 10 char totali
    return f"{value:010.2f}"


def _format_gg_dilazione(value: int = 0) -> str:
    """
    Formatta giorni dilazione: 3 cifre con zeri a sinistra.
    Es: 90 -> "090"
    """
    if value is None:
        value = 0
    try:
        value = int(value)
    except:
        value = 0
    return str(value).zfill(3)[:3]


def _strip_leading_zeros(value: str) -> str:
    """
    Rimuove zeri iniziali da un codice.
    Es: "000010905" -> "10905"
    """
    if not value:
        return ''
    stripped = value.lstrip('0')
    return stripped if stripped else '0'


def generate_to_t_line(data: Dict[str, Any]) -> str:
    """
    Genera una riga TO_T (testata) secondo formato EDI - 869 caratteri.

    Schema v11.3 (verificato su tracciati produzione):

    Pos       Campo                    Lung.  Formato
    1-10      Vendor                   10     String
    11-40     VendorOrderNumber        30     String
    41-60     CustomerTraceabilityCode 20     String (spazio + MIN_ID 5 cifre zfill + ljust)
    61-76     VAT code                 16     String
    77-126    CustomerName1            50     String UPPERCASE
    127-176   CustomerName2            50     String UPPERCASE
    177-226   Address                  50     String UPPERCASE
    227-236   CodeCity                 10     String
    237-286   City                     50     String UPPERCASE
    287-289   Province                 3      String UPPERCASE
    290-299   OrderDate                10     GG/MM/AAAA
    300-309   EstDeliveryDate          10     GG/MM/AAAA
    310-359   AgentName                50     String UPPERCASE
    360-369   DataPagamento1           10     Date o spazi
    370-379   ImportoPagamento1        10     Float 7.2 (0000000.00)
    380-382   GgDilazionePagamento1    3      Int (090)
    383-392   DataPagamento2           10     Date o spazi
    393-402   ImportoPagamento2        10     Float 7.2
    403-405   GgDilazionePagamento2    3      Int
    406-415   DataPagamento3           10     Date o spazi
    416-425   ImportoPagamento3        10     Float 7.2
    426-428   GgDilazionePagamento3    3      Int
    429-448   CodOffertaCliente        20     String
    449-468   CodOffertaVendor         20     String (1000 rjust)
    469       ForceCheck               1      Spazio o S/N
    470-669   OrderAnnotation          200    String (STANDARD)
    670-869   BOT_Annotation           200    String
    """
    # Estrai dati
    vendor = data.get('vendor') or ''
    deposito = data.get('deposito_riferimento') or data.get('deposito') or ''
    vendor_code = get_vendor_code(vendor, deposito)

    # MIN_ID con padding a 5 cifre (zfill)
    min_id_raw = str(data.get('min_id') or data.get('anag_min_id') or '').strip()
    # Rimuovi eventuali zeri iniziali e poi riformatta a 5 cifre
    min_id_clean = min_id_raw.lstrip('0') or '0'
    min_id = min_id_clean.zfill(5)  # Es: 100 -> 00100, 10905 -> 10905

    # Date in formato GG/MM/AAAA
    data_ordine = format_date_edi(data.get('data_ordine', ''))
    data_consegna = format_date_edi(data.get('data_consegna', ''))

    # Se data consegna vuota, usa data odierna
    if not data_consegna or data_consegna.strip() == '':
        data_consegna = date.today().strftime('%d/%m/%Y')

    # Dilazione pagamento (default 90 gg)
    dilazione = data.get('gg_dilazione_1') or data.get('condizioni_pagamento') or 90
    try:
        if isinstance(dilazione, str):
            m = re.search(r'(\d+)', dilazione)
            dilazione = int(m.group(1)) if m else 90
        else:
            dilazione = int(dilazione)
    except:
        dilazione = 90

    # Costruisci la riga - TUTTI I TESTI IN UPPERCASE
    line = ""

    # Pos 1-10: Vendor (10)
    line += vendor_code.upper().ljust(10)[:10]

    # Pos 11-40: VendorOrderNumber (30)
    line += str(data.get('numero_ordine') or data.get('numero_ordine_vendor') or '').ljust(30)[:30]

    # Pos 41-60: CustomerTraceabilityCode/MIN_ID (20)
    # Pos 41: spazio, Pos 42-46: MIN_ID 5 cifre zfill, Pos 47-60: spazi
    line += ' ' + min_id.ljust(19)[:19]

    # Pos 61-76: VAT code/P.IVA (16)
    line += str(data.get('partita_iva') or '').ljust(16)[:16]

    # Pos 77-126: CustomerName1/ragione_sociale (50) - UPPERCASE
    line += str(data.get('ragione_sociale') or '').upper().ljust(50)[:50]

    # Pos 127-176: CustomerName2 (50) - UPPERCASE
    line += str(data.get('ragione_sociale_2') or '').upper().ljust(50)[:50]

    # Pos 177-226: Address (50) - UPPERCASE
    line += str(data.get('indirizzo') or '').upper().ljust(50)[:50]

    # Pos 227-236: CodeCity/CAP (10)
    line += str(data.get('cap') or '').ljust(10)[:10]

    # Pos 237-286: City (50) - UPPERCASE
    line += str(data.get('citta') or '').upper().ljust(50)[:50]

    # Pos 287-289: Province (3) - UPPERCASE
    line += str(data.get('provincia') or '').upper().ljust(3)[:3]

    # Pos 290-299: OrderDate GG/MM/AAAA (10)
    line += data_ordine

    # Pos 300-309: EstDeliveryDate GG/MM/AAAA (10)
    line += data_consegna

    # Pos 310-359: AgentName (50) - UPPERCASE
    line += str(data.get('nome_agente') or '').upper().ljust(50)[:50]

    # === SEZIONE PAGAMENTI (pos 360-428) ===

    # Pos 360-369: DataPagamento1 (10) - vuoto
    line += ' ' * 10

    # Pos 370-379: ImportoPagamento1 (10) - formato 7.2 = "0000000.00"
    line += _format_importo_7_2(0)

    # Pos 380-382: GgDilazionePagamento1 (3) - es: "090"
    line += _format_gg_dilazione(dilazione)

    # Pos 383-392: DataPagamento2 (10) - vuoto
    line += ' ' * 10

    # Pos 393-402: ImportoPagamento2 (10) - formato 7.2
    line += _format_importo_7_2(0)

    # Pos 403-405: GgDilazionePagamento2 (3)
    line += _format_gg_dilazione(0)

    # Pos 406-415: DataPagamento3 (10) - vuoto
    line += ' ' * 10

    # Pos 416-425: ImportoPagamento3 (10) - formato 7.2
    line += _format_importo_7_2(0)

    # Pos 426-428: GgDilazionePagamento3 (3)
    line += _format_gg_dilazione(0)

    # === FINE SEZIONE PAGAMENTI ===

    # Pos 429-448: CodOffertaCliente (20) - vuoto
    line += ' ' * 20

    # Pos 449-468: CodOffertaVendor (20) - "1000" con zeri anteposti
    cod_offerta = data.get('cod_offerta_vendor') or '1000'
    line += str(cod_offerta).zfill(20)[:20]

    # Pos 469: ForceCheck (1) - default spazio
    force_check = data.get('forza_controllo', '')
    if force_check in ('S', 'N'):
        line += force_check
    else:
        line += ' '

    # Pos 470-669: OrderAnnotation (200) - "STANDARD"
    note_ordine = data.get('note_ordine') or 'STANDARD'
    line += str(note_ordine).upper().ljust(200)[:200]

    # Pos 670-869: BOT_Annotation (200)
    line += str(data.get('note_ddt') or '').upper().ljust(200)[:200]

    # Verifica e aggiusta lunghezza finale (869 char)
    if len(line) < TO_T_LENGTH:
        line = line.ljust(TO_T_LENGTH)
    elif len(line) > TO_T_LENGTH:
        line = line[:TO_T_LENGTH]

    return line
