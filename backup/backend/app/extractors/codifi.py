# =============================================================================
# TO_EXTRACTOR v6.0 - ESTRATTORE CODIFI
# =============================================================================
# Vendor: CODIFI S.R.L.
# Riferimento: REGOLE_CODIFI.md
# Particolarità: MULTI-CLIENTE - ogni cliente = ordine separato
#               Parsing indirizzo avanzato (numero civico → città)
#               No ID MIN diretto
# =============================================================================

import re
from typing import List, Dict, Any

from .base import BaseExtractor
from ..utils import provincia_nome_to_sigla


class CodifiExtractor(BaseExtractor):
    """
    Estrattore per Transfer Order CODIFI.
    
    MULTI-CLIENTE:
    - Un PDF può contenere N ordini (uno per cliente)
    - Trigger nuovo ordine: riga con "N°Ordine" + "Data Delivery"
    - Ogni ordine genera coppia TO_T/TO_D separata
    
    Parsing indirizzo:
    - Pattern: INDIRIZZO NUMERO_CIVICO CITTÀ Provincia
    - La parola DOPO il numero civico è la CITTÀ
    """
    
    vendor = "CODIFI"
    
    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """
        Estrae ordini da PDF CODIFI.
        
        Returns:
            Lista di ordini (uno per ogni cliente nel PDF)
        """
        orders = []
        current_order = None
        
        for i, line in enumerate(lines):
            # CODIFI-H01: Identificazione nuovo ordine
            if self._is_new_order_trigger(line):
                # Salva ordine precedente se esiste
                if current_order and current_order.get('numero_ordine'):
                    orders.append(current_order)
                # Inizializza nuovo ordine
                current_order = self.create_empty_order()
                continue
            
            if current_order is None:
                continue
            
            # CODIFI-H02/H03: Numero ordine e data consegna
            if line.strip().startswith('O-'):
                self._parse_order_line(line, current_order)
                continue
            
            # CODIFI-H04/H05: P.IVA e Ragione Sociale
            if self._is_cliente_line(line):
                self._parse_cliente_block(lines, i, current_order)
                continue
            
            # CODIFI-H06-H09: Indirizzo, Comune, Provincia
            if self._is_indirizzo_line(line):
                self._parse_indirizzo_block(lines, i, current_order)
                continue
            
            # CODIFI-T01-T05: Righe prodotto (AIC 9 cifre)
            if self._is_product_line(line):
                row = self._parse_product_line(line, len(current_order.get('righe', [])) + 1)
                if row:
                    current_order.setdefault('righe', []).append(row)
        
        # Non dimenticare l'ultimo ordine
        if current_order and current_order.get('numero_ordine'):
            orders.append(current_order)
        
        return orders
    
    def _is_new_order_trigger(self, line: str) -> bool:
        """Verifica se la riga è trigger per nuovo ordine."""
        return (('N°Ordine' in line or 'N.Ordine' in line or 
                 re.search(r'N.{0,3}Ordine', line)) and 
                'Data Delivery' in line)
    
    def _is_cliente_line(self, line: str) -> bool:
        """Verifica se la riga contiene header cliente."""
        return (('Cod. Cliente' in line or 'Cod.Cliente' in line) and 
                'P.IVA' in line and 
                ('Rag. Sociale' in line or 'Rag.Sociale' in line))
    
    def _is_indirizzo_line(self, line: str) -> bool:
        """Verifica se la riga contiene header indirizzo."""
        return ('Indirizzo Cliente' in line and 
                'Comune' in line and 
                'Provincia' in line)
    
    def _is_product_line(self, line: str) -> bool:
        """Verifica se la riga è un prodotto (AIC 9 cifre)."""
        return bool(re.match(r'^0\d{8}', line.strip()))
    
    def _parse_order_line(self, line: str, order: Dict):
        """Estrae numero ordine e data consegna."""
        parts = line.split()
        if parts:
            order['numero_ordine'] = parts[0]  # O-XXXXXXXXX
            # Cerca data nella riga
            for p in parts[1:]:
                if '/' in p and len(p) == 10:
                    order['data_consegna'] = p
                    break
    
    def _parse_cliente_block(self, lines: List[str], i: int, order: Dict):
        """
        Estrae P.IVA e Ragione Sociale dal blocco cliente.
        
        Gestisce ragione sociale multiriga.
        """
        if i + 1 >= len(lines):
            return
        
        next_line = lines[i + 1].strip()
        
        # Cerca P.IVA (11 cifre consecutive)
        piva_match = re.search(r'\b(\d{11})\b', next_line)
        if piva_match:
            order['partita_iva'] = piva_match.group(1).zfill(11)  # Mantiene 11 cifre
            # Ragione sociale = tutto dopo P.IVA
            rs = next_line[piva_match.end():].strip()
            
            # Gestione multiriga ragione sociale
            for j in range(1, 4):
                if i + 1 + j < len(lines):
                    continuation = lines[i + 1 + j].strip()
                    if (continuation and
                        'Indirizzo' not in continuation and
                        'AIC' not in continuation and
                        len(continuation) < 40 and
                        not re.match(r'^0\d{8}', continuation)):
                        # Rimuovi trattino iniziale
                        if continuation.startswith('-'):
                            continuation = continuation[1:].strip()
                        rs = rs + ' ' + continuation
                    else:
                        break
            
            order['ragione_sociale'] = self.clean_text(rs, 100)
    
    def _parse_indirizzo_block(self, lines: List[str], i: int, order: Dict):
        """
        Estrae Indirizzo, Comune, Provincia.
        
        Parsing avanzato:
        - Pattern: INDIRIZZO NUMERO_CIVICO CITTÀ Provincia
        - Parola DOPO numero civico = CITTÀ
        - Ultima parola con formato Xxxxx = Provincia (nome)
        """
        if i + 1 >= len(lines):
            return
        
        addr_line = lines[i + 1].strip()
        
        # Gestione continuazione indirizzo
        if i + 2 < len(lines):
            continuation = lines[i + 2].strip()
            if (continuation and
                not re.match(r'^0\d{8}', continuation) and
                len(continuation) < 25 and
                'AIC' not in continuation and
                'Cod.' not in continuation):
                addr_line = addr_line + ' ' + continuation
        
        words = addr_line.split()
        indirizzo = addr_line
        comune = ''
        provincia = ''
        
        if len(words) >= 3:
            # Provincia = ultima parola formato Xxxxx (CamelCase)
            last = words[-1]
            if len(last) > 2 and last[0].isupper() and not last.isupper():
                provincia = last
                remaining = words[:-1]
            else:
                remaining = words
            
            if remaining:
                # Cerca NUMERO CIVICO da destra (ultimo numero)
                numero_civico_idx = -1
                for idx in range(len(remaining) - 1, -1, -1):
                    word = remaining[idx]
                    # Numero civico: cifre o cifre+lettera (es: 10, 10A, 123B)
                    if re.match(r'^\d+[A-Za-z]?$', word):
                        numero_civico_idx = idx
                        break
                
                if numero_civico_idx >= 0 and numero_civico_idx < len(remaining) - 1:
                    # Parola DOPO numero civico = CITTÀ
                    comune = remaining[numero_civico_idx + 1].upper()
                    indirizzo = ' '.join(remaining[:numero_civico_idx + 1])
                elif numero_civico_idx == len(remaining) - 1:
                    # Numero civico è l'ultima parola → nessuna città
                    indirizzo = ' '.join(remaining)
                else:
                    # Nessun numero civico → tutto è indirizzo
                    indirizzo = ' '.join(remaining)
        
        order['indirizzo'] = self.clean_text(indirizzo, 60)
        order['citta'] = self.clean_text(comune, 30)
        order['provincia'] = provincia_nome_to_sigla(provincia) if provincia else ''
    
    def _parse_product_line(self, line: str, n_riga: int) -> Dict[str, Any]:
        """
        Estrae dati riga prodotto CODIFI.

        Formato fisso:
        - Colonna 1: Codice AIC (9 cifre 0-9)
        - Colonna 2: Codice prodotto interno (6 alfanumerici) - IGNORARE
        - Colonne successive: Descrizione (inizia sempre con lettera)
        - Ultima colonna: Quantità

        CODIFI non ha espositori.
        """
        parts = line.split()
        if len(parts) < 3:
            return None

        # Colonna 1: Codice AIC (9 cifre)
        aic = parts[0]

        # Colonna 2: Codice prodotto interno - IGNORARE completamente
        # (non salvare, non usare per descrizione)

        # Quantità = ultimo numero della riga
        qty = 1
        for p in reversed(parts):
            if p.isdigit():
                qty = int(p)
                break

        # Descrizione = dalla prima parte che inizia con lettera
        # (salta AIC e codice prodotto, esclude quantità finale)
        desc_parts = []
        for idx, part in enumerate(parts):
            # Salta le prime 2 colonne (AIC e codice prodotto)
            if idx < 2:
                continue
            # Salta quantità finale (ultimo elemento se numerico)
            if idx == len(parts) - 1 and part.isdigit():
                continue
            # La descrizione inizia con lettera
            if desc_parts or (part and part[0].isalpha()):
                desc_parts.append(part)
        desc = ' '.join(desc_parts)

        row = self.create_empty_row(n_riga)
        row['codice_aic'] = aic
        row['codice_originale'] = ''  # Non usiamo il codice prodotto interno
        row['descrizione'] = self.clean_text(desc, 60)
        row['q_venduta'] = qty
        row['is_espositore'] = False  # CODIFI non ha espositori
        row['is_no_aic'] = False

        return row
