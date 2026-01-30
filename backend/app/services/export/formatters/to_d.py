# =============================================================================
# SERV.O v7.0 - TO_D LINE FORMATTER
# =============================================================================
# Generazione riga TO_D (dettaglio) secondo formato EDI
# =============================================================================

from typing import Dict, Any

from .common import (
    TO_D_LENGTH,
    format_date_edi,
    format_float_edi,
    format_int_edi,
)


def generate_to_d_line(data: Dict[str, Any]) -> str:
    """
    Genera una riga TO_D (dettaglio) secondo formato EDI.

    Schema da Scheme_EDI_TO_D.csv:
    - Pos 1-30:    VendorNumberOrder (30)
    - Pos 31-35:   LineNumber (5) - nota: schema dice 6, produzione usa 5
    - Pos 36:      Filler (1) - spazio separatore
    - Pos 37-56:   ProductCode/AIC (20)
    - Pos 57-62:   SalesQuantity (6) <- q_venduta
    - Pos 63-68:   QuantityDiscountPieces (6) <- q_sconto_merce
    - Pos 69-74:   QuantityFreePieces (6) <- q_omaggio
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
    # NOTA: Il campo ProductCode e 20 chars, ma in produzione sembra
    # che il campo inizi a pos 36 (filler+ProductCode = 21 char totali)
    # Per compatibilita con produzione: padding a 10 cifre
    codice_aic = str(data.get('codice_aic') or '').strip()
    if codice_aic and len(codice_aic) < 9:
        codice_aic = codice_aic.zfill(9)
    # Padding extra per allineamento con produzione (10 cifre)
    codice_aic = codice_aic.zfill(10)

    # Quantita per i campi EDI
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

    # v11.5: VALIDAZIONE RIGIDA - totale tracciato <= q_da_evadere
    # Se q_da_evadere è specificato, verifica che non ci sia duplicazione quantità
    q_da_evadere = data.get('_q_da_evadere_originale') or data.get('q_da_evadere')
    if q_da_evadere is not None:
        q_da_evadere = int(q_da_evadere) if q_da_evadere else 0
        totale_tracciato = q_venduta + q_omaggio_totale  # SalesQuantity + QuantityFreePieces
        if totale_tracciato > q_da_evadere:
            n_riga = data.get('n_riga', '?')
            raise ValueError(
                f"Formatter TO_D - Riga {n_riga}: totale tracciato ({totale_tracciato}) > "
                f"q_da_evadere ({q_da_evadere}). "
                f"SalesQuantity={q_venduta}, QuantityFreePieces={q_omaggio_totale}. "
                f"Possibile duplicazione quantità."
            )

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
    line += str(data.get('numero_ordine') or data.get('numero_ordine_vendor') or '').ljust(30)[:30]
    # Pos 31-35: LineNumber (5)
    line += format_int_edi(data.get('n_riga') or 1, 5)
    # Pos 36-56: ProductCode/AIC (21 chars: 10-digit AIC + 11 spaces)
    # NOTA: Schema originale prevede Filler(1)+ProductCode(20) ma produzione
    # mostra AIC a 10 cifre che inizia direttamente a pos 36
    line += codice_aic.ljust(21)[:21]
    # Pos 57-62: SalesQuantity (6) <- q_venduta
    line += format_int_edi(q_venduta, 6)
    # Pos 63-68: QuantityDiscountPieces (6) <- sempre 0 in produzione
    line += format_int_edi(0, 6)
    # Pos 69-74: QuantityFreePieces (6) <- q_sconto_merce + q_omaggio
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
