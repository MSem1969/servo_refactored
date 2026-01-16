# =============================================================================
# TO_EXTRACTOR v6.0 - ESTRATTORE MENARINI
# =============================================================================
# Vendor: A. MENARINI / CODIFI S.R.L.
# Riferimento: REGOLE_MENARINI.md
# Particolarità: Parent/Child con coordinate X
#               X0 < 28 → PARENT (includere)
#               X0 >= 28 → CHILD (ignorare)
# =============================================================================

import re
from typing import List, Dict, Any, Optional

from .base import BaseExtractor

# Import opzionale pdfplumber per coordinate
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class MenariniExtractor(BaseExtractor):
    """
    Estrattore per Transfer Order MENARINI.
    
    Gestione Parent/Child:
    - Le righe PARENT (non indentate, X0 < 28) vanno incluse
    - Le righe CHILD (indentate, X0 >= 28) vanno IGNORATE
    - Gli espositori PARENT vanno inclusi con anomalia NO_AIC
    
    Se pdfplumber disponibile: usa coordinate X per rilevare child
    Altrimenti: fallback su indentazione testo
    """
    
    vendor = "MENARINI"
    
    # Soglia coordinata X per parent/child
    X_THRESHOLD = 28
    
    # Pattern header MENARINI
    PATTERNS = {
        'numero_ordine': r'Ordine\s+N\.?:?\s*(\d+)(?:_\d{8})?',
        'cliente': r'Cliente\s+(.+?)\s+Cod\.?\s*Cliente',
        'piva': r'Partita\s+IVA\s+(\d{11})',
        'indirizzo_cap': r'Indirizzo\s+(.+?)\s+CAP\s+(\d{5})',
        'citta_prov': r"Città\s+([A-Z][A-Z\s/'-]+?)\s+Provincia\s+([A-Z]{2})",
        'agente': r'Rep\s+([A-Z][A-Z\s]+?)\s+Tipo\s+Ordine',
        'data_ordine': r'Data\s+Ordine\s+(\d{2}/\d{2}/\d{4})',
        'data_consegna': r'Data\s+Consegna\s+(\d{2}/\d{2}/\d{4})',
        'dilazione': r'(\d+)\s*GG',
    }
    
    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """Estrae ordini da PDF MENARINI."""
        # Se pdf_path disponibile e pdfplumber installato, usa coordinate
        if pdf_path and PDFPLUMBER_AVAILABLE:
            return self._extract_with_coordinates(text, pdf_path)
        else:
            return self._extract_text_fallback(text, lines)
    
    def _extract_with_coordinates(self, text: str, pdf_path: str) -> List[Dict[str, Any]]:
        """Estrazione con pdfplumber per rilevare parent/child."""
        all_orders = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    words = page.extract_words()
                    tables = page.extract_tables()
                    
                    # Raggruppa parole per Y (riga)
                    rows_by_y = {}
                    for w in words:
                        y_key = round(w['top'], 0)
                        if y_key not in rows_by_y:
                            rows_by_y[y_key] = []
                        rows_by_y[y_key].append(w)
                    
                    # Identifica coordinate X dei prodotti
                    product_coords = []
                    for y_key in sorted(rows_by_y.keys()):
                        row_words = sorted(rows_by_y[y_key], key=lambda w: w['x0'])
                        if row_words:
                            first_text = row_words[0]['text'].upper()
                            x0 = row_words[0]['x0']
                            # Keyword prodotti MENARINI
                            keywords = ['AFTAMED', 'FASTUM', 'SUSTENIUM', 'NEBUL', 
                                       'MOMENT', 'VIVIN', 'GLORIA', 'COLLIRIO']
                            if any(kw in first_text for kw in keywords):
                                is_child = (x0 >= self.X_THRESHOLD)
                                product_coords.append({
                                    'y': y_key, 
                                    'is_child': is_child, 
                                    'x0': x0
                                })
                    
                    # Estrai da tabelle
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        header = table[0]
                        if not header or 'Prodotto' not in str(header):
                            continue
                        
                        data = self._extract_header(page_text)
                        data['righe'] = self._extract_table_rows(
                            table, product_coords
                        )
                        
                        if data.get('righe') or data.get('numero_ordine'):
                            all_orders.append(data)
        
        except Exception as e:
            print(f"⚠️ Errore MENARINI coordinate: {e}")
            return self._extract_text_fallback(text, text.split('\n'))
        
        return all_orders if all_orders else self._extract_text_fallback(text, text.split('\n'))
    
    def _extract_text_fallback(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Fallback: estrazione solo testo (senza coordinate)."""
        data = self._extract_header(text)
        
        n_riga = 0
        for line in lines:
            line_stripped = line.strip()
            
            # Cerca pattern codice ministeriale + quantità
            m = re.search(r'(\d{9})\s+(\d+)\s+', line_stripped)
            if m:
                cod_min = m.group(1)
                qty = int(m.group(2))
                
                # Rileva child tramite indentazione (spazi/tab iniziali)
                if line.startswith('  ') or line.startswith('\t'):
                    continue  # Ignora child
                
                # Estrai descrizione
                desc_match = re.match(r'^(.+?)\s+\d{9}', line_stripped)
                descrizione = desc_match.group(1).strip()[:40] if desc_match else ''
                
                n_riga += 1
                is_espositore = (cod_min == '--' or not re.match(r'^\d{9}$', cod_min))
                
                row = self.create_empty_row(n_riga)
                row['codice_aic'] = '' if is_espositore else cod_min
                row['codice_originale'] = cod_min
                row['descrizione'] = descrizione
                row['q_venduta'] = qty
                row['is_espositore'] = is_espositore
                row['is_no_aic'] = is_espositore
                data['righe'].append(row)
        
        return [data] if data.get('righe') or data.get('numero_ordine') else []
    
    def _extract_header(self, text: str) -> Dict[str, Any]:
        """Estrae dati header MENARINI."""
        data = self.create_empty_order()
        
        # Numero ordine
        m = re.search(self.PATTERNS['numero_ordine'], text)
        if m:
            data['numero_ordine'] = m.group(1).strip()
        
        # Cliente/Ragione sociale
        m = re.search(self.PATTERNS['cliente'], text)
        if m:
            data['ragione_sociale'] = self.clean_text(m.group(1), 50)
        
        # P.IVA
        m = re.search(self.PATTERNS['piva'], text)
        if m:
            data['partita_iva'] = m.group(1).zfill(11)  # Mantiene 11 cifre
        
        # Indirizzo e CAP
        m = re.search(self.PATTERNS['indirizzo_cap'], text)
        if m:
            data['indirizzo'] = self.clean_text(m.group(1), 50)
            data['cap'] = m.group(2)
        
        # Città e Provincia
        m = re.search(self.PATTERNS['citta_prov'], text)
        if m:
            data['citta'] = self.clean_text(m.group(1), 50)
            data['provincia'] = m.group(2)
        
        # Agente
        m = re.search(self.PATTERNS['agente'], text)
        if m:
            data['nome_agente'] = self.clean_text(m.group(1), 50)
        
        # Data ordine
        m = re.search(self.PATTERNS['data_ordine'], text)
        if m:
            data['data_ordine'] = m.group(1)
        
        # Data consegna
        m = re.search(self.PATTERNS['data_consegna'], text)
        if m:
            data['data_consegna'] = m.group(1)
        
        # Dilazione
        m = re.search(self.PATTERNS['dilazione'], text, re.IGNORECASE)
        if m:
            data['gg_dilazione'] = int(m.group(1))
        
        return data
    
    def _extract_table_rows(self, table: List, product_coords: List[Dict]) -> List[Dict[str, Any]]:
        """Estrae righe da tabella pdfplumber."""
        result = []
        
        # Salta header
        data_rows = [r for r in table[1:] 
                     if r and r[0] and not str(r[0]).strip().startswith('Totale')]
        
        n_riga = 0
        for idx, row in enumerate(data_rows):
            desc_raw = str(row[0] or '').strip()
            if not desc_raw:
                continue
            
            # Verifica se è child usando coordinate X
            is_child = False
            if idx < len(product_coords):
                is_child = product_coords[idx].get('is_child', False)
            
            if is_child:
                continue  # Ignora righe child
            
            cod_min = str(row[1] or '').strip() if len(row) > 1 else ''
            
            try:
                qty = int(str(row[2] or '0').strip()) if len(row) > 2 else 0
            except:
                qty = 0
            
            try:
                prezzo = float(str(row[3] or '0').replace('€', '').replace(',', '.').strip()) if len(row) > 3 else 0.0
            except:
                prezzo = 0.0
            
            sconto_str = str(row[4] or '--').strip() if len(row) > 4 else '--'
            sconto1 = 0.0
            if sconto_str != '--':
                try:
                    sconto1 = float(sconto_str.replace('%', '').replace(',', '.'))
                except:
                    pass
            
            # Sconto merce + Omaggi
            sm = str(row[5] or '--').strip() if len(row) > 5 else '--'
            om = str(row[6] or '--').strip() if len(row) > 6 else '--'
            q_sm = int(sm) if sm.isdigit() else 0
            q_om = int(om) if om.isdigit() else 0
            q_omaggio = q_sm + q_om
            
            pn = str(row[7] or '--').replace('€', '').replace(',', '.').strip() if len(row) > 7 else '--'
            prezzo_netto = float(pn) if pn and pn != '--' else 0.0
            
            # Pulisci descrizione (rimuovi codice tra parentesi)
            descrizione = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', desc_raw).strip()[:40]
            is_espositore = (cod_min == '--' or not re.match(r'^\d{9}$', cod_min))
            
            n_riga += 1
            row_data = self.create_empty_row(n_riga)
            row_data['codice_aic'] = '' if is_espositore else cod_min
            row_data['codice_originale'] = cod_min if cod_min != '--' else ''
            row_data['descrizione'] = descrizione
            row_data['q_venduta'] = qty
            row_data['q_omaggio'] = q_omaggio
            row_data['sconto1'] = sconto1
            row_data['prezzo_pubblico'] = prezzo
            row_data['prezzo_netto'] = prezzo_netto
            row_data['is_espositore'] = is_espositore
            row_data['is_no_aic'] = is_espositore
            result.append(row_data)
        
        return result
