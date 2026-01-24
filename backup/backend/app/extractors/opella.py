# =============================================================================
# TO_EXTRACTOR v6.0 - ESTRATTORE OPELLA
# =============================================================================
# Vendor: Opella Healthcare Italy S.r.l.
# Particolarità: AIC 7-9 cifre, colonne GROSSISTA/DESTINATARIO
#               Usa coordinate X per separare colonne
# =============================================================================

import re
from typing import List, Dict, Any

from .base import BaseExtractor

# Import opzionale pdfplumber per coordinate
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class OpellaExtractor(BaseExtractor):
    """
    Estrattore per Transfer Order OPELLA.
    
    Caratteristiche:
    - Codici AIC con 7-9 cifre (normalizzare a 9)
    - Due colonne: GROSSISTA (sinistra) e DESTINATARIO (destra)
    - I dati cliente sono nella colonna DESTINATARIO
    - Usa coordinate X per separare le colonne
    """
    
    vendor = "OPELLA"
    
    # Soglia X per colonna DESTINATARIO (destra)
    X_THRESHOLD = 300
    
    # Pattern header OPELLA
    PATTERNS = {
        'numero_ordine': r'Numero\s+ordine\s+cliente:?\s*(\d+)',
        'data_ordine': r'Data:?\s*(\d{2}\.\d{2}\.\d{4})',
        'dilazione': r'Termini\s+di\s+pagamento:?\s*(\d+)\s*gg',
        'data_consegna': r'Data\s+di\s+consegna\s+richiesta:?\s*(\d{2}\.\d{2}\.\d{4})',
    }
    
    # Pattern riga prodotto
    ROW_PATTERN = re.compile(
        r'^(\d+)\s+(\d{6,9})\s+(.+?)\s+(\d+)\s+UNT\s+([\d,]+)\s+([\d,\.]+)'
    )
    
    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """Estrae ordini da PDF OPELLA."""
        # Se pdf_path disponibile e pdfplumber installato, usa coordinate
        if pdf_path and PDFPLUMBER_AVAILABLE:
            result = self._extract_with_coordinates(pdf_path)
            if result and (result[0].get('righe') or result[0].get('numero_ordine')):
                return result
        
        # Fallback testo
        return self._extract_text_fallback(text, lines)
    
    def _extract_with_coordinates(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Estrazione con pdfplumber per coordinate colonne."""
        data = self.create_empty_order()
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]
                text = page.extract_text() or ""
                words = page.extract_words()
                
                # Estrai header da testo
                self._extract_header_from_text(text, data)
                
                # Raggruppa parole per Y
                rows_by_y = {}
                for w in words:
                    y_key = round(w['top'], 0)
                    if y_key not in rows_by_y:
                        rows_by_y[y_key] = []
                    rows_by_y[y_key].append(w)
                
                # Trova riga DESTINATARIO
                dest_y = None
                for y_key in sorted(rows_by_y.keys()):
                    row_text = ' '.join([w['text'] for w in rows_by_y[y_key]])
                    if 'DESTINATARIO' in row_text:
                        dest_y = y_key
                        break
                
                if dest_y:
                    # Estrai righe successive solo dalla colonna destra (X >= threshold)
                    dest_data = []
                    for y_key in sorted(rows_by_y.keys()):
                        if y_key > dest_y and len(dest_data) < 6:
                            right_words = [w for w in rows_by_y[y_key] if w['x0'] >= self.X_THRESHOLD]
                            if right_words:
                                right_words = sorted(right_words, key=lambda w: w['x0'])
                                line_text = ' '.join([w['text'] for w in right_words])
                                dest_data.append(line_text)
                    
                    # Parse dest_data:
                    # [0] = codice cliente
                    # [1] = ragione sociale
                    # [2] = indirizzo
                    # [3] = regione (ignorare)
                    # [4] = CAP CITTÀ PROV
                    if len(dest_data) >= 2:
                        data['ragione_sociale'] = self.clean_text(dest_data[1], 50)
                    if len(dest_data) >= 3:
                        data['indirizzo'] = self.clean_text(dest_data[2], 50)
                    if len(dest_data) >= 5:
                        # CAP CITTÀ PROV
                        m = re.match(r'(\d{5})\s+(.+?)\s+([A-Z]{2})$', dest_data[4].strip())
                        if m:
                            data['cap'] = m.group(1)
                            data['citta'] = self.clean_text(m.group(2), 50)
                            data['provincia'] = m.group(3)
                
                # Estrai tabella prodotti
                tables = page.extract_tables()
                if tables:
                    data['righe'] = self._extract_table_rows(tables[0])
        
        except Exception as e:
            print(f"⚠️ Errore OPELLA coordinate: {e}")
            return []
        
        return [data]
    
    def _extract_text_fallback(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Fallback: estrazione solo testo."""
        data = self.create_empty_order()
        
        # Header
        self._extract_header_from_text(text, data)
        
        # Cerca destinatario nel testo
        for i, line in enumerate(lines):
            if 'DESTINATARIO DELLA MERCE' in line or 'DESTINATARIO' in line:
                # Cerca ragione sociale nelle righe successive
                for j in range(i+1, min(i+6, len(lines))):
                    if 'FARMACIA' in lines[j] or 'F.CIA' in lines[j]:
                        parts = re.split(r'\s{3,}', lines[j])
                        if len(parts) >= 2:
                            data['ragione_sociale'] = self.clean_text(parts[-1], 50)
                        else:
                            data['ragione_sociale'] = self.clean_text(lines[j], 50)
                        break
                # Cerca CAP/Città/Provincia
                for j in range(i+1, min(i+8, len(lines))):
                    m = re.search(r'(\d{5})\s+([A-Z\']+)\s+([A-Z]{2})\s*$', lines[j])
                    if m:
                        data['cap'] = m.group(1)
                        data['citta'] = m.group(2)
                        data['provincia'] = m.group(3)
                        break
                break
        
        # Righe prodotto
        n = 0
        for line in lines:
            line_stripped = line.strip()
            m = self.ROW_PATTERN.match(line_stripped)
            if m:
                n += 1
                codice_raw = m.group(2)
                desc = self.clean_text(m.group(3), 40)
                qty = int(m.group(4))
                pu = self.parse_float(m.group(5))
                totale = self.parse_float(m.group(6))
                
                aic_info = self.normalize_aic(codice_raw, desc)
                
                row = self.create_empty_row(n)
                row['codice_aic'] = aic_info['aic']
                row['codice_originale'] = aic_info['aic_orig']
                row['descrizione'] = desc
                row['q_venduta'] = qty
                row['prezzo_pubblico'] = pu
                row['prezzo_netto'] = round(totale / qty, 2) if qty > 0 else 0
                row['is_espositore'] = aic_info['is_espositore']
                row['is_no_aic'] = aic_info['is_no_aic']
                data['righe'].append(row)
        
        return [data]
    
    def _extract_header_from_text(self, text: str, data: Dict):
        """Estrae header da testo."""
        # Numero ordine
        m = re.search(self.PATTERNS['numero_ordine'], text, re.IGNORECASE)
        if m:
            data['numero_ordine'] = m.group(1)
        
        # Data ordine
        m = re.search(self.PATTERNS['data_ordine'], text)
        if m:
            data['data_ordine'] = self._parse_date(m.group(1))
        
        # Dilazione
        m = re.search(self.PATTERNS['dilazione'], text, re.IGNORECASE)
        if m:
            data['gg_dilazione'] = int(m.group(1))
        
        # Data consegna
        m = re.search(self.PATTERNS['data_consegna'], text, re.IGNORECASE)
        if m:
            data['data_consegna'] = self._parse_date(m.group(1))
    
    def _extract_table_rows(self, table: List) -> List[Dict[str, Any]]:
        """Estrae righe da tabella."""
        result = []
        n = 0
        
        for row in table:
            if not row or not row[0]:
                continue
            row_text = row[0] if isinstance(row, list) else str(row)
            
            m = self.ROW_PATTERN.match(str(row_text).strip())
            if m:
                n += 1
                codice_raw = m.group(2)
                desc = self.clean_text(m.group(3), 40)
                qty = int(m.group(4))
                pu = self.parse_float(m.group(5))
                totale = self.parse_float(m.group(6))
                
                aic_info = self.normalize_aic(codice_raw, desc)
                
                row_data = self.create_empty_row(n)
                row_data['codice_aic'] = aic_info['aic']
                row_data['codice_originale'] = aic_info['aic_orig']
                row_data['descrizione'] = desc
                row_data['q_venduta'] = qty
                row_data['prezzo_pubblico'] = pu
                row_data['prezzo_netto'] = round(totale / qty, 2) if qty > 0 else 0
                row_data['is_espositore'] = aic_info['is_espositore']
                row_data['is_no_aic'] = aic_info['is_no_aic']
                result.append(row_data)
        
        return result
    
    def _parse_date(self, date_str: str) -> str:
        """Converte data DD.MM.YYYY in DD/MM/YYYY."""
        if not date_str:
            return ''
        return date_str.replace('.', '/')
