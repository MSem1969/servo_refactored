# =============================================================================
# TO_EXTRACTOR v6.2 - TRACCIATI SERVICE
# =============================================================================
# Generazione tracciati TO_T (testata) e TO_D (dettaglio)
# Formato conforme a Scheme_EDI (vedi CLAUDE.md)
# =============================================================================

import os
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from ..config import config
from ..database_pg import get_db, log_operation
from ..utils import compute_file_hash, calcola_q_totale
from .supervisione import può_emettere_tracciato


# =============================================================================
# FORMATO TRACCIATI EDI
# =============================================================================

# Lunghezza righe secondo schema EDI
TO_T_LENGTH = 857   # Testata (calcolato da schema)
TO_D_LENGTH = 344   # Dettaglio (calcolato da schema)

# Codice produttore default
DEFAULT_VENDOR_CODE = "HAL_FARVI"


def format_date_edi(date_val) -> str:
    """
    Formatta data per tracciato EDI: GG/MM/AAAA (10 caratteri).
    Accetta stringhe o oggetti datetime.date (PostgreSQL).
    """
    from datetime import date, datetime

    if not date_val:
        return ' ' * 10

    # PostgreSQL restituisce datetime.date - converti in stringa DD/MM/YYYY
    if isinstance(date_val, (date, datetime)):
        return date_val.strftime('%d/%m/%Y')

    # Da qui in poi è una stringa
    date_str = str(date_val)

    # Già in formato DD/MM/YYYY
    if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        return date_str

    # YYYY-MM-DD (ISO da PostgreSQL come stringa) -> DD/MM/YYYY
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

    # DD.MM.YYYY -> DD/MM/YYYY
    m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    # YYYYMMDD -> DD/MM/YYYY
    m = re.match(r'^(\d{4})(\d{2})(\d{2})$', date_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

    # DD-MM-YYYY -> DD/MM/YYYY
    m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    return date_str.ljust(10)[:10]


def format_float_edi(value: float, int_digits: int, dec_digits: int) -> str:
    """
    Formatta float per EDI: int_digits.dec_digits con punto decimale.
    Esempio: format_float_edi(8.56, 7, 2) -> "0000008.56"
    """
    if value is None:
        value = 0.0
    try:
        value = float(value)
    except:
        value = 0.0

    total_len = int_digits + dec_digits + 1  # +1 per il punto
    formatted = f"{value:0{total_len}.{dec_digits}f}"
    return formatted[:total_len]


def format_int_edi(value: int, digits: int) -> str:
    """
    Formatta intero per EDI: zero-padded a sinistra.
    """
    if value is None:
        value = 0
    try:
        value = int(value)
    except:
        value = 0
    return str(value).zfill(digits)[:digits]


# =============================================================================
# GENERAZIONE RIGHE - FORMATO EDI
# =============================================================================

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
    vendor_code = DEFAULT_VENDOR_CODE
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
    line += str(data.get('numero_ordine') or '').ljust(30)[:30]
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


def generate_to_d_line(data: Dict[str, Any]) -> str:
    """
    Genera una riga TO_D (dettaglio) secondo formato EDI.

    Schema da Scheme_EDI_TO_D.csv:
    - Pos 1-30:    VendorNumberOrder (30)
    - Pos 31-35:   LineNumber (5) - nota: schema dice 6, produzione usa 5
    - Pos 36:      Filler (1) - spazio separatore
    - Pos 37-56:   ProductCode/AIC (20)
    - Pos 57-62:   SalesQuantity (6) ← q_venduta
    - Pos 63-68:   QuantityDiscountPieces (6) ← q_sconto_merce
    - Pos 69-74:   QuantityFreePieces (6) ← q_omaggio
    - Pos 75-84:   ExtDeliveryDate GG/MM/AAAA (10)
    - Pos 85-90:   Discount1 (6: 3+2 dec)
    - Pos 91-96:   Discount2 (6: 3+2 dec)
    - Pos 97-102:  Discount3 (6: 3+2 dec)
    - Pos 103-108: Discount4 (6: 3+2 dec)
    - Pos 109-118: NetVendorPrice (10: 7+2 dec)
    - Pos 119-128: PriceToDiscount (10: 7+2 dec)
    - Pos 129-133: VAT (5: 2+2 dec)
    - Pos 134:     NetVATPrice S/N (1)
    - Pos 135-144: PriceForFinalSale (10: 7+2 dec)
    - Pos 145-344: NoteAllestimento (200)
    """
    # Codice AIC - padding a 9 cifre
    # NOTA: Il campo ProductCode è 20 chars, ma in produzione sembra
    # che il campo inizi a pos 36 (filler+ProductCode = 21 char totali)
    # Per compatibilità con produzione: padding a 10 cifre
    codice_aic = str(data.get('codice_aic') or '').strip()
    if codice_aic and len(codice_aic) < 9:
        codice_aic = codice_aic.zfill(9)
    # Padding extra per allineamento con produzione (10 cifre)
    codice_aic = codice_aic.zfill(10)

    # Quantità per i campi EDI
    try:
        q_venduta = int(data.get('q_venduta') or data.get('quantita') or 0)
    except:
        q_venduta = 0

    try:
        q_sconto_merce = int(data.get('q_sconto_merce') or 0)
    except:
        q_sconto_merce = 0

    try:
        q_omaggio = int(data.get('q_omaggio') or 0)
    except:
        q_omaggio = 0

    # REGOLA PRODUZIONE: q_sconto_merce va sommato a q_omaggio nel campo QuantityFreePieces
    # QuantityDiscountPieces resta sempre 0
    q_omaggio_totale = q_sconto_merce + q_omaggio

    # Data consegna
    data_consegna = format_date_edi(data.get('data_consegna') or '')

    # Sconti (formato 3+2 decimali = 6 caratteri)
    sconto_1 = float(data.get('sconto_1') or 0)
    sconto_2 = float(data.get('sconto_2') or 0)
    sconto_3 = float(data.get('sconto_3') or 0)
    sconto_4 = float(data.get('sconto_4') or 0)

    # Prezzi (formato 7+2 decimali = 10 caratteri)
    prezzo_netto = float(data.get('prezzo_netto') or 0)
    prezzo_scontare = float(data.get('prezzo_scontare') or data.get('prezzo_listino') or 0)
    prezzo_pubblico = float(data.get('prezzo_pubblico') or 0)

    # IVA (formato 2+2 decimali = 5 caratteri)
    aliquota_iva = float(data.get('aliquota_iva') or 0)

    # Scorporo IVA: S=prezzo netto, N=IVA inclusa
    scorporo_iva = str(data.get('scorporo_iva') or 'S')[:1]

    # Note allestimento
    note_allestimento = str(data.get('note_allestimento') or '')

    line = ""
    # Pos 1-30: VendorNumberOrder (30)
    line += str(data.get('numero_ordine') or '').ljust(30)[:30]
    # Pos 31-35: LineNumber (5)
    line += format_int_edi(data.get('n_riga') or 1, 5)
    # Pos 36-56: ProductCode/AIC (21 chars: 10-digit AIC + 11 spaces)
    # NOTA: Schema originale prevede Filler(1)+ProductCode(20) ma produzione
    # mostra AIC a 10 cifre che inizia direttamente a pos 36
    line += codice_aic.ljust(21)[:21]
    # Pos 57-62: SalesQuantity (6) ← q_venduta
    line += format_int_edi(q_venduta, 6)
    # Pos 63-68: QuantityDiscountPieces (6) ← sempre 0 in produzione
    line += format_int_edi(0, 6)
    # Pos 69-74: QuantityFreePieces (6) ← q_sconto_merce + q_omaggio
    line += format_int_edi(q_omaggio_totale, 6)
    # Pos 75-84: ExtDeliveryDate (10)
    line += data_consegna
    # Pos 85-90: Discount1 (6: 3+2 dec)
    line += format_float_edi(sconto_1, 3, 2)
    # Pos 91-96: Discount2 (6: 3+2 dec)
    line += format_float_edi(sconto_2, 3, 2)
    # Pos 97-102: Discount3 (6: 3+2 dec)
    line += format_float_edi(sconto_3, 3, 2)
    # Pos 103-108: Discount4 (6: 3+2 dec)
    line += format_float_edi(sconto_4, 3, 2)
    # Pos 109-118: NetVendorPrice (10: 7+2 dec)
    line += format_float_edi(prezzo_netto, 7, 2)
    # Pos 119-128: PriceToDiscount (10: 7+2 dec)
    line += format_float_edi(prezzo_scontare, 7, 2)
    # Pos 129-133: VAT (5: 2+2 dec)
    line += format_float_edi(aliquota_iva, 2, 2)
    # Pos 134: NetVATPrice S/N (1)
    line += scorporo_iva
    # Pos 135-144: PriceForFinalSale (10: 7+2 dec)
    line += format_float_edi(prezzo_pubblico, 7, 2)
    # Pos 145-344: NoteAllestimento (200)
    line += note_allestimento.ljust(200)[:200]

    # Verifica e aggiusta lunghezza
    if len(line) < TO_D_LENGTH:
        line = line.ljust(TO_D_LENGTH)
    elif len(line) > TO_D_LENGTH:
        line = line[:TO_D_LENGTH]

    return line


# =============================================================================
# GENERAZIONE FILE
# =============================================================================

def generate_tracciati_per_ordine(
    output_dir: str = None,
    ordini_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Genera file tracciato TO_T e TO_D - UN FILE PER OGNI ORDINE.
    
    Args:
        output_dir: Directory output (default: config.OUTPUT_DIR)
        ordini_ids: Lista ID ordini da esportare (default: tutti pronti)
        
    Returns:
        Lista di dict con info sui file generati
    """
    db = get_db()
    output_dir = output_dir or config.OUTPUT_DIR
    
    # Crea directory se non esiste
    os.makedirs(output_dir, exist_ok=True)
    
    # Query ordini
    if ordini_ids:
        placeholders = ','.join(['?' for _ in ordini_ids])
        query = f"""
            SELECT * FROM V_ORDINI_COMPLETI 
            WHERE id_testata IN ({placeholders})
            AND lookup_method != 'NESSUNO'
            ORDER BY vendor, numero_ordine
        """
        ordini = db.execute(query, ordini_ids).fetchall()
    else:
        ordini = db.execute("""
            SELECT * FROM V_ORDINI_COMPLETI 
            WHERE stato NOT IN ('SCARTATO', 'PENDING_REVIEW') 
            AND lookup_method != 'NESSUNO'
            AND stato != 'ESPORTATO'
            ORDER BY vendor, numero_ordine
        """).fetchall()
    
    if not ordini:
        return []
    
    results = []
    
    for ordine in ordini:
        ordine_dict = dict(ordine)
        id_testata = ordine_dict['id_testata']
        numero_ordine = ordine_dict['numero_ordine']
        vendor = ordine_dict['vendor']
        
        # Verifica se ordine può essere esportato (nessuna supervisione pending)
        if not può_emettere_tracciato(id_testata):
            continue
        
        # Carica dettagli
        dettagli = db.execute("""
            SELECT d.*, v.min_id
            FROM V_DETTAGLI_COMPLETI d
            JOIN V_ORDINI_COMPLETI v ON d.id_testata = v.id_testata
            WHERE d.id_testata = ?
            ORDER BY d.n_riga
        """, (id_testata,)).fetchall()
        
        # Sanitizza numero ordine per nome file
        safe_num = re.sub(r'[^a-zA-Z0-9_-]', '_', str(numero_ordine))
        filename_t = f"TO_T_{vendor}_{safe_num}.TXT"
        filename_d = f"TO_D_{vendor}_{safe_num}.TXT"
        path_t = os.path.join(output_dir, filename_t)
        path_d = os.path.join(output_dir, filename_d)
        
        # Genera TO_T (una sola riga per questo ordine)
        line_t = generate_to_t_line(ordine_dict)
        
        # Genera TO_D
        lines_d = []
        for det in dettagli:
            det_dict = dict(det)
            # Salta solo child (i parent espositore vanno inclusi!)
            # I child sono già aggregati nel parent
            if det_dict.get('is_child'):
                continue
            
            # Aggiungi dati testata al dettaglio
            det_dict['numero_ordine'] = numero_ordine
            det_dict['min_id'] = ordine_dict.get('min_id') or ''
            det_dict['codice_sito'] = ordine_dict.get('anag_codice_sito')
            
            line = generate_to_d_line(det_dict)
            lines_d.append(line)
        
        # Scrivi file
        with open(path_t, 'w', encoding=config.ENCODING) as f:
            f.write(line_t + '\r\n')
        
        with open(path_d, 'w', encoding=config.ENCODING) as f:
            f.write('\r\n'.join(lines_d))
            if lines_d:
                f.write('\r\n')
        
        # Aggiorna stato ordine
        db.execute(
            "UPDATE ORDINI_TESTATA SET stato = 'ESPORTATO' WHERE id_testata = ?", 
            (id_testata,)
        )
        
        results.append({
            'id_testata': id_testata,
            'numero_ordine': numero_ordine,
            'vendor': vendor,
            'file_to_t': filename_t,
            'file_to_d': filename_d,
            'path_to_t': path_t,
            'path_to_d': path_d,
            'num_righe': len(lines_d)
        })
    
    # Registra esportazione complessiva
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cursor = db.execute("""
            INSERT INTO ESPORTAZIONI
            (nome_tracciato_generato, data_tracciato, nome_file_to_t, nome_file_to_d,
             num_testate, num_dettagli, stato)
            VALUES (?, ?, ?, ?, ?, ?, 'GENERATO')
        """, (
            timestamp,
            datetime.now().strftime('%Y-%m-%d'),
            f"{len(results)} file TO_T",
            f"{len(results)} file TO_D",
            len(results),
            sum(r['num_righe'] for r in results)
        ))

        id_esportazione = cursor.lastrowid
        
        # Registra dettaglio esportazione
        for r in results:
            db.execute("""
                INSERT INTO ESPORTAZIONI_DETTAGLIO (id_esportazione, id_testata)
                VALUES (?, ?)
            """, (id_esportazione, r['id_testata']))
        
        log_operation('GENERA_TRACCIATI', 'ESPORTAZIONI', id_esportazione,
                     f"Generati {len(results)} tracciati")
    
    db.commit()
    return results


# =============================================================================
# v6.2.4: VALIDAZIONE CAMPI OBBLIGATORI TRACCIATI
# =============================================================================

def valida_campi_tracciato(ordine: Dict[str, Any], dettagli: List[Dict]) -> Dict[str, Any]:
    """
    Valida i campi obbligatori per la generazione del tracciato.

    CAMPI OBBLIGATORI TO_T (Testata):
    - vendor: Nome vendor
    - numero_ordine: Numero ordine
    - partita_iva: Partita IVA cliente
    - min_id: Codice ministeriale (MIN_ID)
    - gg_dilazione: Giorni di pagamento

    CAMPI OBBLIGATORI TO_D (Dettaglio):
    - numero_ordine: Numero ordine
    - codice_aic: Codice AIC prodotto
    - prezzo_netto: Prezzo > 0 (eccetto omaggio/sconto merce)

    Returns:
        Dict con:
        - valid: True/False
        - errors: Lista errori bloccanti
        - warnings: Lista warning non bloccanti
    """
    errors = []
    warnings = []

    # ==========================================================================
    # VALIDAZIONE TO_T (Testata)
    # ==========================================================================

    # Vendor
    vendor = ordine.get('vendor') or ''
    if not vendor.strip():
        errors.append("TO_T: Campo 'Vendor' obbligatorio mancante")

    # Numero ordine
    numero_ordine = ordine.get('numero_ordine') or ''
    if not numero_ordine.strip():
        errors.append("TO_T: Campo 'Numero Ordine' obbligatorio mancante")

    # Partita IVA
    partita_iva = ordine.get('partita_iva') or ordine.get('partita_iva_estratta') or ''
    if not partita_iva.strip():
        errors.append("TO_T: Campo 'Partita IVA' obbligatorio mancante")
    elif len(partita_iva.strip()) < 11:
        errors.append(f"TO_T: Partita IVA non valida: '{partita_iva}' (deve essere 11 caratteri)")

    # Codice Ministeriale (MIN_ID)
    min_id = (ordine.get('min_id') or ordine.get('anag_min_id') or
              ordine.get('codice_ministeriale') or ordine.get('codice_ministeriale_estratto') or '')
    if not min_id.strip():
        errors.append("TO_T: Campo 'Codice Ministeriale (MIN_ID)' obbligatorio mancante")

    # Giorni di pagamento (dilazione)
    gg_dilazione = ordine.get('gg_dilazione_1') or ordine.get('condizioni_pagamento') or ordine.get('gg_dilazione')
    if not gg_dilazione:
        warnings.append("TO_T: Campo 'Giorni Pagamento' mancante - verrà usato default 90 gg")

    # ==========================================================================
    # VALIDAZIONE TO_D (Dettaglio)
    # ==========================================================================

    righe_senza_aic = []
    righe_senza_prezzo = []

    for idx, det in enumerate(dettagli, 1):
        det_dict = dict(det) if hasattr(det, 'keys') else det
        n_riga = det_dict.get('n_riga') or idx

        # Codice AIC
        codice_aic = det_dict.get('codice_aic') or det_dict.get('codice_prodotto') or ''
        if not codice_aic.strip():
            righe_senza_aic.append(str(n_riga))

        # Prezzo (obbligatorio > 0, eccetto omaggio/sconto merce)
        prezzo_netto = det_dict.get('prezzo_netto') or det_dict.get('prezzo_vendita') or 0
        q_omaggio = det_dict.get('q_omaggio') or 0
        q_sconto_merce = det_dict.get('q_sconto_merce') or 0
        q_venduta = det_dict.get('q_venduta') or 0

        # Se ha quantità venduta (non solo omaggio/sconto), prezzo deve essere > 0
        try:
            prezzo_val = float(prezzo_netto)
        except:
            prezzo_val = 0

        if q_venduta > 0 and prezzo_val <= 0:
            # Non è puro omaggio/sconto → prezzo obbligatorio
            righe_senza_prezzo.append(str(n_riga))

    if righe_senza_aic:
        errors.append(f"TO_D: Codice AIC mancante per righe: {', '.join(righe_senza_aic[:10])}" +
                     (f" (e altre {len(righe_senza_aic)-10})" if len(righe_senza_aic) > 10 else ""))

    if righe_senza_prezzo:
        errors.append(f"TO_D: Prezzo vendita mancante o zero per righe con q_venduta > 0: {', '.join(righe_senza_prezzo[:10])}" +
                     (f" (e altre {len(righe_senza_prezzo)-10})" if len(righe_senza_prezzo) > 10 else ""))

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


# =============================================================================
# v6.2: VALIDAZIONE E GENERAZIONE TRACCIATO (FUNZIONE UNIFICATA)
# =============================================================================

def valida_e_genera_tracciato(
    id_testata: int,
    operatore: str,
    validazione_massiva: bool = False
) -> Dict[str, Any]:
    """
    Valida e genera tracciato TO_T/TO_D per un ordine.

    LOGICA v6.2:
    - Se validazione_massiva=True (Dashboard): conferma TUTTE le righe, copia q_venduta→q_evasa
    - Se validazione_massiva=False (Dettaglio): esporta SOLO righe già CONFERMATE con q_evasa > 0

    Args:
        id_testata: ID ordine
        operatore: Nome operatore
        validazione_massiva: Se True, conferma tutte le righe prima dell'export

    Returns:
        Dict con success, file paths, statistiche
    """
    db = get_db()
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')

    # 1. Carica ordine
    ordine = db.execute("""
        SELECT * FROM V_ORDINI_COMPLETI WHERE id_testata = ?
    """, (id_testata,)).fetchone()

    if not ordine:
        return {'success': False, 'error': 'Ordine non trovato'}

    ordine_dict = dict(ordine)

    # 2. VALIDAZIONE MASSIVA - FIX v6.2.3
    # Logica basata su STATO ORDINE (testata):
    # - Ordine CONFERMATO (pronto export) → NON toccare q_da_evadere, usa valori esistenti
    # - Ordine ESTRATTO/altri → imposta q_da_evadere = q_totale per evasione totale
    if validazione_massiva:
        stato_ordine = ordine_dict.get('stato', 'ESTRATTO')

        # Se ordine NON è già CONFERMATO, imposta q_da_evadere = q_totale per tutte le righe
        if stato_ordine != 'CONFERMATO':
            # Imposta q_da_evadere = q_totale per righe parent
            db.execute("""
                UPDATE ORDINI_DETTAGLIO
                SET q_da_evadere = COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0),
                    stato_riga = 'CONFERMATO'
                WHERE id_testata = ?
                  AND (is_child = FALSE OR is_child IS NULL)
                  AND stato_riga NOT IN ('EVASO', 'PARZIALE')
                  AND (COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0)) > 0
            """, (id_testata,))

            # Imposta q_da_evadere = q_totale per CHILD_ESPOSITORE
            db.execute("""
                UPDATE ORDINI_DETTAGLIO
                SET q_da_evadere = COALESCE(q_venduta, 0) + COALESCE(q_sconto_merce, 0) + COALESCE(q_omaggio, 0),
                    stato_riga = 'CONFERMATO'
                WHERE id_testata = ?
                  AND is_child = TRUE
                  AND stato_riga NOT IN ('EVASO', 'PARZIALE')
            """, (id_testata,))
            db.commit()
        # else: Ordine CONFERMATO → q_da_evadere già impostato, non modificare

        # Carica righe con q_da_evadere > 0 (sia per ordini CONFERMATO che altri)
        dettagli = db.execute("""
            SELECT * FROM ORDINI_DETTAGLIO
            WHERE id_testata = ?
              AND COALESCE(q_da_evadere, 0) > 0
              AND (is_child = FALSE OR is_child IS NULL)
            ORDER BY n_riga
        """, (id_testata,)).fetchall()

        if not dettagli:
            return {
                'success': False,
                'error': 'Nessuna riga con quantità da esportare. Confermare le righe prima.'
            }
    else:
        # Per dettaglio: carica righe con q_da_evadere > 0 (quantità da esportare in questo tracciato)
        dettagli = db.execute("""
            SELECT * FROM ORDINI_DETTAGLIO
            WHERE id_testata = ?
              AND q_da_evadere > 0
              AND (is_child = FALSE OR is_child IS NULL)
            ORDER BY n_riga
        """, (id_testata,)).fetchall()

        if not dettagli:
            return {
                'success': False,
                'error': 'Nessuna riga con quantità da evadere > 0. Inserire prima le quantità nella colonna "Da Evadere".'
            }

    # 3. VALIDAZIONE CAMPI OBBLIGATORI (v6.2.4)
    # Verifica campi TO_T e TO_D prima di generare
    validazione = valida_campi_tracciato(ordine_dict, dettagli)

    if not validazione['valid']:
        # Blocca generazione con errori dettagliati
        error_msg = "BLOCCO GENERAZIONE TRACCIATO\n\n"
        error_msg += "Campi obbligatori mancanti o non validi:\n"
        error_msg += "\n".join(f"• {e}" for e in validazione['errors'])

        if validazione['warnings']:
            error_msg += "\n\nAvvisi:\n"
            error_msg += "\n".join(f"• {w}" for w in validazione['warnings'])

        return {
            'success': False,
            'error': error_msg,
            'validation_errors': validazione['errors'],
            'validation_warnings': validazione['warnings']
        }

    # Se ci sono solo warning, li includeremo nella risposta finale
    validation_warnings = validazione['warnings']

    # 4. Genera tracciati
    numero_ordine = ordine_dict['numero_ordine']
    vendor = ordine_dict['vendor']

    # Nome file con timestamp per evitare sovrascritture
    safe_num = re.sub(r'[^a-zA-Z0-9_-]', '_', str(numero_ordine))
    filename_t = f"TO_T_{vendor}_{safe_num}_{timestamp}.TXT"
    filename_d = f"TO_D_{vendor}_{safe_num}_{timestamp}.TXT"

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    path_t = os.path.join(config.OUTPUT_DIR, filename_t)
    path_d = os.path.join(config.OUTPUT_DIR, filename_d)

    # Genera TO_T (testata)
    line_t = generate_to_t_line(ordine_dict)

    # Genera TO_D (dettagli) - usando q_da_evadere (quantità da esportare in QUESTO tracciato)
    lines_d = []
    righe_esportate = []

    for det in dettagli:
        det_dict = dict(det)

        # Prepara dati per tracciato
        det_dict['numero_ordine'] = numero_ordine
        det_dict['min_id'] = ordine_dict.get('min_id') or ''
        det_dict['codice_sito'] = ordine_dict.get('anag_codice_sito')

        # USA q_da_evadere per la quantità nel tracciato (NON q_evasa che è il cumulativo)
        q_da_evadere = det_dict.get('q_da_evadere', 0) or 0
        det_dict['q_venduta'] = q_da_evadere
        det_dict['_q_da_evadere_originale'] = q_da_evadere  # Salva per post-processing

        line = generate_to_d_line(det_dict)
        lines_d.append(line)
        righe_esportate.append(det_dict)

    # 4. Scrivi file
    with open(path_t, 'w', encoding=config.ENCODING) as f:
        f.write(line_t + '\r\n')

    with open(path_d, 'w', encoding=config.ENCODING) as f:
        f.write('\r\n'.join(lines_d))
        if lines_d:
            f.write('\r\n')

    # 5. Registra esportazione
    cursor = db.execute("""
        INSERT INTO ESPORTAZIONI
        (nome_tracciato_generato, data_tracciato, nome_file_to_t, nome_file_to_d,
         num_testate, num_dettagli, stato)
        VALUES (?, date('now'), ?, ?, 1, ?, 'GENERATO')
    """, (f"{vendor}_{safe_num}_{timestamp}", filename_t, filename_d, len(lines_d)))

    id_esportazione = cursor.lastrowid

    db.execute("""
        INSERT INTO ESPORTAZIONI_DETTAGLIO (id_esportazione, id_testata)
        VALUES (?, ?)
    """, (id_esportazione, id_testata))

    # 6. Aggiorna stato righe esportate
    # LOGICA v6.2.1: q_evasa += q_da_evadere, poi q_da_evadere = 0
    righe_complete = 0
    righe_parziali = 0

    for det_dict in righe_esportate:
        id_dettaglio = det_dict['id_dettaglio']
        q_da_evadere = det_dict.get('_q_da_evadere_originale', 0) or det_dict.get('q_da_evadere', 0) or 0

        # Recupera riga originale per calcolo quantità
        riga_orig = db.execute("""
            SELECT q_venduta, q_sconto_merce, q_omaggio, q_evasa
            FROM ORDINI_DETTAGLIO WHERE id_dettaglio = ?
        """, (id_dettaglio,)).fetchone()

        if riga_orig:
            q_totale = calcola_q_totale(dict(riga_orig))
            q_evasa_precedente = riga_orig['q_evasa'] or 0
        else:
            q_totale = det_dict.get('q_venduta_originale') or det_dict.get('q_originale') or 0
            q_evasa_precedente = 0

        # FIX v6.2.2: Logica unificata per tutti i casi
        # q_evasa = quantità già esportata in tracciati precedenti
        # q_da_evadere = quantità da esportare in QUESTO tracciato
        # nuovo_q_evasa = cumulativo dopo questo tracciato
        nuovo_q_evasa = q_evasa_precedente + q_da_evadere

        # Calcola residuo
        q_residua = q_totale - nuovo_q_evasa

        # v6.2.1: Determina nuovo stato dopo generazione tracciato
        # - EVASO: riga completamente evasa (q_evasa >= q_totale)
        # - PARZIALE: riga parzialmente evasa (0 < q_evasa < q_totale)
        # - ESTRATTO: nessuna evasione
        if q_totale > 0 and nuovo_q_evasa >= q_totale:
            nuovo_stato = 'EVASO'
            righe_complete += 1
        elif nuovo_q_evasa > 0:
            nuovo_stato = 'PARZIALE'
            righe_parziali += 1
        else:
            nuovo_stato = 'ESTRATTO'

        # Aggiorna riga: q_evasa += q_da_evadere, q_da_evadere = 0
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = ?,
                q_evasa = ?,
                q_da_evadere = 0,
                q_residua = ?,
                confermato_da = ?,
                data_conferma = ?,
                num_esportazioni = COALESCE(num_esportazioni, 0) + 1,
                ultima_esportazione = ?,
                id_ultima_esportazione = ?
            WHERE id_dettaglio = ?
        """, (
            nuovo_stato, nuovo_q_evasa, q_residua, operatore, now.isoformat(),
            now.isoformat(), id_esportazione, id_dettaglio
        ))

    # 7. AGGIORNA STATO TUTTE LE RIGHE dell'ordine
    # Corregge lo stato anche per righe non processate in questo tracciato
    # (es. righe già evase in tracciati precedenti)

    # Righe completamente evase → EVASO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'EVASO'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND q_evasa >= (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
          AND (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0)) > 0
    """, (id_testata,))

    # Righe parzialmente evase → PARZIALE
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'PARZIALE'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND q_evasa > 0
          AND q_evasa < (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
    """, (id_testata,))

    # Righe con q_da_evadere > 0 ma non ancora esportate → CONFERMATO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'CONFERMATO'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND (q_evasa IS NULL OR q_evasa = 0)
          AND q_da_evadere > 0
    """, (id_testata,))

    # Righe senza evasione e senza q_da_evadere → ESTRATTO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'ESTRATTO'
        WHERE id_testata = ?
          AND (is_child = FALSE OR is_child IS NULL)
          AND (q_evasa IS NULL OR q_evasa = 0)
          AND (q_da_evadere IS NULL OR q_da_evadere = 0)
    """, (id_testata,))

    # 8. Verifica stato complessivo ordine
    # Conta righe totali e righe completamente evase
    # v6.2: q_totale = q_venduta + q_sconto_merce + q_omaggio
    stats = db.execute("""
        SELECT
            COUNT(*) as totale,
            SUM(CASE
                WHEN q_evasa >= (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
                     AND (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0)) > 0
                THEN 1 ELSE 0 END) as complete,
            SUM(CASE
                WHEN q_evasa > 0
                     AND q_evasa < (COALESCE(q_venduta,0) + COALESCE(q_sconto_merce,0) + COALESCE(q_omaggio,0))
                THEN 1 ELSE 0 END) as parziali,
            SUM(CASE WHEN q_evasa IS NULL OR q_evasa = 0 THEN 1 ELSE 0 END) as non_evase
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
    """, (id_testata,)).fetchone()

    totale_righe = stats['totale'] or 0
    righe_complete_tot = stats['complete'] or 0
    righe_parziali_tot = stats['parziali'] or 0
    righe_non_evase = stats['non_evase'] or 0

    # 8. Aggiorna stato ordine in base all'evasione
    # EVASO = tutte le righe completamente evase (dopo generazione tracciato)
    # PARZ_EVASO = almeno una riga evasa ma non tutte complete
    if totale_righe > 0 and righe_complete_tot == totale_righe:
        # Tutte le righe completamente evase
        db.execute("""
            UPDATE ORDINI_TESTATA
            SET stato = 'EVASO',
                data_validazione = datetime('now'),
                validato_da = ?
            WHERE id_testata = ?
        """, (operatore, id_testata))
        stato_ordine = 'EVASO'
    elif righe_complete_tot > 0 or righe_parziali_tot > 0:
        # Almeno una riga evasa (parzialmente o totalmente)
        db.execute("""
            UPDATE ORDINI_TESTATA
            SET stato = 'PARZ_EVASO',
                data_validazione = COALESCE(data_validazione, datetime('now')),
                validato_da = COALESCE(validato_da, ?)
            WHERE id_testata = ?
        """, (operatore, id_testata))
        stato_ordine = 'PARZ_EVASO'
    else:
        # Nessuna riga evasa - mantieni stato precedente
        stato_ordine = ordine_dict.get('stato', 'ESTRATTO')

    db.commit()

    log_operation('VALIDA_TRACCIATO', 'ORDINI_TESTATA', id_testata,
                 f"Generato tracciato: {len(lines_d)} righe. Stato ordine: {stato_ordine}",
                 operatore=operatore)

    # Costruisci messaggio con eventuali warning
    message = f"Tracciato generato: {len(lines_d)} righe esportate. Stato ordine: {stato_ordine}"
    if validation_warnings:
        message += f"\n\nAvvisi: {len(validation_warnings)}"
        for w in validation_warnings:
            message += f"\n• {w}"

    return {
        'success': True,
        'id_testata': id_testata,
        'stato': stato_ordine,
        'tracciato': {
            'to_t': {
                'filename': filename_t,
                'path': path_t,
                'download_url': f"/api/v1/tracciati/download/{filename_t}"
            },
            'to_d': {
                'filename': filename_d,
                'path': path_d,
                'download_url': f"/api/v1/tracciati/download/{filename_d}",
                'num_righe': len(lines_d)
            }
        },
        'statistiche': {
            'righe_esportate': len(lines_d),
            'righe_complete': righe_complete_tot,
            'righe_parziali': righe_parziali_tot,
            'righe_non_evase': righe_non_evase
        },
        'validation_warnings': validation_warnings,
        'message': message
    }


# =============================================================================
# PREVIEW E UTILITÀ
# =============================================================================

def get_tracciato_preview(id_testata: int) -> Dict[str, Any]:
    """
    Genera preview tracciato senza salvare file.
    
    Returns:
        Dict con preview TO_T e TO_D
    """
    db = get_db()
    
    # Carica testata
    ordine = db.execute(
        "SELECT * FROM V_ORDINI_COMPLETI WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()
    
    if not ordine:
        return {'error': 'Ordine non trovato'}
    
    ordine_dict = dict(ordine)
    
    # Carica dettagli
    dettagli = db.execute("""
        SELECT * FROM V_DETTAGLI_COMPLETI WHERE id_testata = ?
        ORDER BY n_riga
    """, (id_testata,)).fetchall()
    
    # Genera preview
    line_t = generate_to_t_line(ordine_dict)
    
    lines_d = []
    for det in dettagli:
        det_dict = dict(det)
        # Salta solo child (i parent espositore vanno inclusi!)
        if det_dict.get('is_child'):
            continue
        det_dict['numero_ordine'] = ordine_dict['numero_ordine']
        det_dict['min_id'] = ordine_dict.get('min_id') or ''
        lines_d.append(generate_to_d_line(det_dict))
    
    return {
        'to_t': line_t,
        'to_d': lines_d,
        'to_t_length': len(line_t),
        'to_d_count': len(lines_d),
        'ordine': {
            'numero_ordine': ordine_dict['numero_ordine'],
            'vendor': ordine_dict['vendor'],
            'ragione_sociale': ordine_dict['ragione_sociale'],
        }
    }


def get_ordini_pronti_export() -> List[Dict]:
    """
    Ritorna ordini pronti per esportazione.
    
    Logica:
    - Stato ESTRATTO (non ancora esportati)
    - Esclusi SCARTATO, ESPORTATO
    - Con lookup valido
    """
    db = get_db()
    rows = db.execute("""
        SELECT 
            id_testata,
            vendor,
            numero_ordine,
            ragione_sociale,
            citta,
            lookup_method,
            lookup_score,
            num_righe_calc AS num_righe,
            stato,
            data_estrazione,
            data_validazione
        FROM V_ORDINI_COMPLETI
        WHERE stato = 'ESTRATTO'
        AND (lookup_method IS NULL OR lookup_method != 'NESSUNO')
        ORDER BY stato DESC, vendor, numero_ordine
    """).fetchall()
    return [dict(row) for row in rows]


def get_esportazioni_storico(limit: int = 20) -> List[Dict]:
    """
    Ritorna storico esportazioni con flag 'oggi'.
    """
    db = get_db()
    rows = db.execute("""
        SELECT
            e.*,
            CASE
                WHEN date(e.data_esportazione) = date('now') THEN 1
                ELSE 0
            END AS oggi
        FROM ESPORTAZIONI e
        ORDER BY e.data_esportazione DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_file_tracciato(filename: str) -> Optional[str]:
    """
    Ritorna percorso completo file tracciato se esiste.
    """
    path = os.path.join(config.OUTPUT_DIR, filename)
    if os.path.exists(path):
        return path
    return None
