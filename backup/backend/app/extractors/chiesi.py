# =============================================================================
# TO_EXTRACTOR v6.0 - ESTRATTORE CHIESI
# =============================================================================
# Vendor: Chiesi Italia S.p.A.
# Riferimento: REGOLE_CHIESI.md
# Particolarità: ESCLUDERE P.IVA 02944970348 (è del vendor!)
#               Q.TA' S.M. → QOmaggio (NON correlato a Q.TA')
#               Data consegna specifica per riga
# =============================================================================

import re
from typing import List, Dict, Any

from .base import BaseExtractor


class ChiesiExtractor(BaseExtractor):
    """
    Estrattore per Transfer Order CHIESI.
    
    ATTENZIONE:
    - P.IVA 02944970348 è del vendor CHIESI, NON del cliente!
    - La colonna CODICE (interno Chiesi) va IGNORATA
    - Q.TA' S.M. (Sconto Merce) → mappa a QOmaggio
    """
    
    vendor = "CHIESI"
    
    # P.IVA CHIESI (da escludere!)
    CHIESI_PIVA = "02944970348"
    
    # Pattern specifici CHIESI
    PATTERNS = {
        'numero_ordine': r'Numero\s+Ordine:?\s*(O-\d+)\s+del\s+(\d{2}/\d{2}/\d{4})',
        'piva': r'P\.?IVA\s+(\d{11})',
        'cliente_consegna': r'Cliente\s+consegna\s+([A-Z][^\n]+)',
        'cliente_fatturazione': r'Cliente\s+Fatturazione\s+([A-Z][^\n]+)',
        'indirizzo_consegna': r'Indirizzo\s+consegna\s+([^\n]+)',
        'cap_localita': r'Cap\s+e\s+Localit[àa]\s+(?:IT-)?(\d{5})\s+([A-Z][A-Z\s\']+?)\s+([A-Z]{2})',
        'agente': r'Agente\s+([A-Z][A-Z\s]+?)(?:\s+Codice|\s*$)',
        'dilazione': r'Dilazione\s+(\d{2,3})R?',
    }
    
    # Pattern riga prodotto CHIESI
    # AIC | CODICE | PRODOTTO | DATA CONSEGNA | Q.TA' | Q.TA' S.M. | SCONTO | PREZZO | TOTALE
    ROW_PATTERN = re.compile(
        r'^(\d{9})\s+(\S+)\s+(.+?)\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+([\d,]+)%?\s+([\d,]+)\s+([\d,]+)\s*$'
    )
    
    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """Estrae ordini da PDF CHIESI."""
        data = self.create_empty_order()
        
        # === HEADER ===
        
        # CHIESI-H01: Numero ordine e data
        m = re.search(self.PATTERNS['numero_ordine'], text, re.IGNORECASE)
        if m:
            data['numero_ordine'] = m.group(1)
            data['data_ordine'] = m.group(2)
        
        # CHIESI-H02: P.IVA Cliente (ESCLUDERE P.IVA Chiesi!)
        for piva_match in re.finditer(self.PATTERNS['piva'], text):
            piva = piva_match.group(1)
            if piva != self.CHIESI_PIVA:  # Escludi P.IVA vendor
                data['partita_iva'] = piva.zfill(11)  # Mantiene 11 cifre
                break
        
        # CHIESI-H03: Ragione sociale (preferisci "Cliente consegna")
        m = re.search(self.PATTERNS['cliente_consegna'], text)
        if m:
            data['ragione_sociale'] = self.clean_text(m.group(1), 50)
        else:
            m = re.search(self.PATTERNS['cliente_fatturazione'], text)
            if m:
                data['ragione_sociale'] = self.clean_text(m.group(1), 50)
        
        # CHIESI-H04: Indirizzo
        m = re.search(self.PATTERNS['indirizzo_consegna'], text)
        if m:
            data['indirizzo'] = self.clean_text(m.group(1), 50)
        
        # CHIESI-H05: CAP, Città, Provincia
        m = re.search(self.PATTERNS['cap_localita'], text)
        if m:
            data['cap'] = m.group(1)
            data['citta'] = self.clean_text(m.group(2), 50)
            data['provincia'] = m.group(3)
        
        # CHIESI-H06: Agente
        m = re.search(self.PATTERNS['agente'], text, re.MULTILINE)
        if m:
            data['nome_agente'] = self.clean_text(m.group(1), 50)
        
        # CHIESI-H07: Dilazione
        m = re.search(self.PATTERNS['dilazione'], text)
        if m:
            data['gg_dilazione'] = int(m.group(1))
        
        # === RIGHE PRODOTTO ===
        data['righe'] = self._extract_rows(lines, data.get('data_ordine', ''))
        
        # Usa data prima riga come data consegna header
        if data['righe'] and data['righe'][0].get('data_consegna'):
            data['data_consegna'] = data['righe'][0]['data_consegna']
        
        return [data]
    
    def _extract_rows(self, lines: List[str], fallback_date: str = '') -> List[Dict[str, Any]]:
        """
        Estrae righe prodotto CHIESI.
        
        Formato riga:
        AIC | CODICE | PRODOTTO | DATA CONSEGNA | Q.TA' | Q.TA' S.M. | SCONTO | PREZZO | TOTALE
        
        Note:
        - CODICE (colonna 2) va IGNORATO
        - Q.TA' S.M. → q_omaggio (NON correlato a Q.TA')
        - Ogni riga ha la propria data consegna
        """
        result = []
        n = 0
        
        for line in lines:
            line_stripped = line.strip()
            m = self.ROW_PATTERN.match(line_stripped)
            if m:
                n += 1
                aic = m.group(1)
                # m.group(2) = CODICE interno Chiesi → IGNORA
                descrizione = self.clean_text(m.group(3), 40)
                data_consegna = m.group(4)
                q_venduta = self.parse_int(m.group(5))
                q_omaggio = self.parse_int(m.group(6))  # Q.TA' S.M. → QOmaggio
                sconto = self.parse_float(m.group(7))
                prezzo_netto = self.parse_float(m.group(8))
                # m.group(9) = TOTALE → IGNORA (calcolato)
                
                aic_info = self.normalize_aic(aic, descrizione)
                
                row = self.create_empty_row(n)
                row['codice_aic'] = aic_info['aic']
                row['codice_originale'] = aic_info['aic_orig']
                row['descrizione'] = descrizione
                row['data_consegna'] = data_consegna
                row['q_venduta'] = q_venduta
                row['q_omaggio'] = q_omaggio
                row['sconto1'] = sconto
                row['prezzo_netto'] = prezzo_netto
                row['is_espositore'] = aic_info['is_espositore']
                row['is_no_aic'] = aic_info['is_no_aic']
                result.append(row)
        
        return result
