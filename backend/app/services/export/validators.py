# =============================================================================
# SERV.O v7.0 - EXPORT VALIDATORS
# =============================================================================
# Validazione campi obbligatori per tracciati EDI
# =============================================================================

from typing import Dict, Any, List


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

    # Numero ordine (può essere 'numero_ordine' o 'numero_ordine_vendor')
    numero_ordine = ordine.get('numero_ordine') or ordine.get('numero_ordine_vendor') or ''
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
        warnings.append("TO_T: Campo 'Giorni Pagamento' mancante - verra usato default 90 gg")

    # ==========================================================================
    # VALIDAZIONE TO_D (Dettaglio)
    # ==========================================================================

    righe_senza_aic = []
    righe_aic_invalido = []
    righe_senza_prezzo = []

    for idx, det in enumerate(dettagli, 1):
        det_dict = dict(det) if hasattr(det, 'keys') else det
        n_riga = det_dict.get('n_riga') or idx

        # Codice AIC - deve essere esattamente 9 cifre numeriche
        codice_aic = det_dict.get('codice_aic') or det_dict.get('codice_prodotto') or ''
        codice_aic = codice_aic.strip()
        if not codice_aic:
            righe_senza_aic.append(str(n_riga))
        elif not (len(codice_aic) == 9 and codice_aic.isdigit()):
            # AIC presente ma non valido (non 9 cifre numeriche)
            righe_aic_invalido.append(f"{n_riga}({codice_aic})")

        # Prezzo (obbligatorio > 0, eccetto omaggio/sconto merce)
        prezzo_netto = det_dict.get('prezzo_netto') or det_dict.get('prezzo_vendita') or 0
        q_omaggio = det_dict.get('q_omaggio') or 0
        q_sconto_merce = det_dict.get('q_sconto_merce') or 0
        q_venduta = det_dict.get('q_venduta') or 0

        # Se ha quantita venduta (non solo omaggio/sconto), prezzo deve essere > 0
        try:
            prezzo_val = float(prezzo_netto)
        except:
            prezzo_val = 0

        if q_venduta > 0 and prezzo_val <= 0:
            # Non e puro omaggio/sconto -> prezzo obbligatorio
            righe_senza_prezzo.append(str(n_riga))

    if righe_senza_aic:
        errors.append(f"TO_D: Codice AIC mancante per righe: {', '.join(righe_senza_aic[:10])}" +
                     (f" (e altre {len(righe_senza_aic)-10})" if len(righe_senza_aic) > 10 else ""))

    if righe_aic_invalido:
        errors.append(f"TO_D: Codice AIC non valido (richieste 9 cifre) per righe: {', '.join(righe_aic_invalido[:10])}" +
                     (f" (e altre {len(righe_aic_invalido)-10})" if len(righe_aic_invalido) > 10 else ""))

    if righe_senza_prezzo:
        errors.append(f"TO_D: Prezzo vendita mancante o zero per righe con q_venduta > 0: {', '.join(righe_senza_prezzo[:10])}" +
                     (f" (e altre {len(righe_senza_prezzo)-10})" if len(righe_senza_prezzo) > 10 else ""))

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
