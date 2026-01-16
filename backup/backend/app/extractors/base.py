# =============================================================================
# TO_EXTRACTOR v6.0 - BASE EXTRACTOR
# =============================================================================
# Classe base per tutti gli estrattori vendor-specifici
# =============================================================================

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from collections import defaultdict


class BaseExtractor(ABC):
    """
    Classe base astratta per estrattori vendor.
    
    Ogni vendor deve implementare:
    - extract() -> lista di ordini estratti
    """
    
    # Identificativo vendor
    vendor: str = "UNKNOWN"
    
    # Pattern comuni
    DATE_PATTERN = r'(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})'
    PIVA_PATTERN = r'P\.?\s*IVA[:\s]*(\d{11})'
    CAP_PATTERN = r'\b(\d{5})\b'
    PROVINCIA_PATTERN = r'\(([A-Z]{2})\)|(?:^|\s)([A-Z]{2})(?:\s|$)'
    
    def __init__(self):
        """Inizializza estrattore."""
        pass
    
    @abstractmethod
    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """
        Estrae ordini dal PDF.
        
        Args:
            text: Testo completo estratto dal PDF
            lines: Lista di righe del testo
            pdf_path: Percorso al file PDF (per estrazioni con coordinate)
            
        Returns:
            Lista di dizionari ordine, ciascuno con:
            - numero_ordine: str
            - data_ordine: str
            - data_consegna: str
            - partita_iva: str
            - ragione_sociale: str
            - indirizzo: str
            - cap: str
            - citta: str
            - provincia: str
            - nome_agente: str
            - gg_dilazione: int
            - codice_ministeriale: str (opzionale)
            - righe: List[Dict] con dettagli prodotti
        """
        pass
    
    def extract_header(self, text: str) -> Dict[str, Any]:
        """
        Estrae dati header comuni.
        Può essere sovrascritta per logica vendor-specifica.
        """
        return {}
    
    def extract_rows(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        Estrae righe prodotto.
        Può essere sovrascritta per logica vendor-specifica.
        """
        return []
    
    # =========================================================================
    # METODI HELPER COMUNI
    # =========================================================================
    
    def find_pattern(self, text: str, pattern: str, group: int = 1) -> Optional[str]:
        """Cerca pattern e ritorna gruppo specificato."""
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(group).strip() if m else None
    
    def find_all_patterns(self, text: str, pattern: str) -> List[str]:
        """Trova tutte le occorrenze di un pattern."""
        return re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
    
    def clean_text(self, text: str, max_len: int = None) -> str:
        """Pulisce testo rimuovendo spazi multipli."""
        if not text:
            return ''
        text = re.sub(r'\s+', ' ', str(text)).strip()
        if max_len and len(text) > max_len:
            text = text[:max_len]
        return text
    
    def extract_date(self, text: str) -> Optional[str]:
        """Estrae prima data trovata nel testo."""
        m = re.search(self.DATE_PATTERN, text)
        return m.group(1) if m else None
    
    def extract_piva(self, text: str, exclude_piva: str = None) -> Optional[str]:
        """Estrae P.IVA, escludendo quella del vendor se specificata."""
        for m in re.finditer(self.PIVA_PATTERN, text, re.IGNORECASE):
            piva = m.group(1)
            if exclude_piva and piva == exclude_piva:
                continue
            return piva
        return None
    
    def extract_cap(self, text: str) -> Optional[str]:
        """Estrae CAP (5 cifre)."""
        m = re.search(self.CAP_PATTERN, text)
        return m.group(1) if m else None
    
    def extract_provincia(self, text: str) -> Optional[str]:
        """Estrae sigla provincia (2 lettere)."""
        # Prima cerca (XX)
        m = re.search(r'\(([A-Z]{2})\)', text)
        if m:
            return m.group(1)
        # Poi cerca sigla a fine riga
        m = re.search(r'\s([A-Z]{2})\s*$', text)
        if m:
            return m.group(1)
        return None
    
    def parse_int(self, value: str) -> int:
        """Converte stringa in intero."""
        if not value:
            return 0
        value = re.sub(r'[^\d]', '', str(value))
        return int(value) if value else 0
    
    def parse_float(self, value: str) -> float:
        """Converte stringa in float (formato italiano)."""
        if not value:
            return 0.0
        value = str(value).strip().replace(' ', '')
        value = value.replace('€', '').replace('EUR', '')
        # Formato italiano: virgola decimale
        if ',' in value and '.' in value:
            if value.rfind(',') > value.rfind('.'):
                value = value.replace('.', '').replace(',', '.')
            else:
                value = value.replace(',', '')
        elif ',' in value:
            value = value.replace(',', '.')
        try:
            return float(value)
        except:
            return 0.0
    
    def normalize_aic(self, codice: str, descrizione: str = '') -> Dict[str, Any]:
        """
        Normalizza codice AIC a 9 cifre.
        
        Returns:
            Dict con: aic, aic_orig, is_espositore, is_no_aic
        """
        codice = str(codice).strip() if codice else ''
        aic_orig = codice
        is_espositore = False
        is_no_aic = False
        
        # Rileva espositore
        esp_pattern = r'(ESP|EXP|BANCO|EXPO)'
        if re.search(esp_pattern, codice.upper()) or \
           re.search(esp_pattern, descrizione.upper()):
            is_espositore = True
        
        # Rileva codice non valido
        if codice in ('--', '-', '', 'N/A', 'NA'):
            is_no_aic = True
            return {
                'aic': '',
                'aic_orig': aic_orig,
                'is_espositore': is_espositore,
                'is_no_aic': True
            }
        
        # Estrai solo cifre
        codice_num = re.sub(r'[^\d]', '', codice)
        
        if codice_num:
            # Normalizza a 9 cifre
            if len(codice_num) == 7:
                codice_num = '00' + codice_num
            elif len(codice_num) == 8:
                codice_num = '0' + codice_num
            elif len(codice_num) > 9:
                codice_num = codice_num[:9]
            codice_num = codice_num.zfill(9)
        else:
            is_no_aic = True
        
        return {
            'aic': codice_num,
            'aic_orig': aic_orig,
            'is_espositore': is_espositore,
            'is_no_aic': is_no_aic
        }
    
    def create_empty_order(self) -> Dict[str, Any]:
        """Crea struttura ordine vuota."""
        return {
            'numero_ordine': '',
            'data_ordine': '',
            'data_consegna': '',
            'partita_iva': '',
            'codice_ministeriale': '',
            'ragione_sociale': '',
            'indirizzo': '',
            'cap': '',
            'citta': '',
            'provincia': '',
            'nome_agente': '',
            'gg_dilazione': 90,
            'righe': []
        }
    
    def create_empty_row(self, n_riga: int = 1) -> Dict[str, Any]:
        """Crea struttura riga prodotto vuota."""
        return {
            'n_riga': n_riga,
            'codice_aic': '',
            'codice_originale': '',
            'descrizione': '',
            'q_venduta': 0,
            'q_omaggio': 0,
            'q_sconto_merce': 0,
            'data_consegna': '',
            'sconto1': 0.0,
            'sconto2': 0.0,
            'sconto3': 0.0,
            'sconto4': 0.0,
            'prezzo_netto': 0.0,
            'prezzo_pubblico': 0.0,
            'aliquota_iva': 10.0,
            'is_espositore': False,
            'is_child': False,
            'is_no_aic': False,
        }


class GenericExtractor(BaseExtractor):
    """Estrattore generico per vendor non riconosciuti."""
    
    vendor = "GENERIC"
    
    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """Estrazione generica: cerca numeri ordine e codici AIC."""
        data = self.create_empty_order()
        
        # Cerca numero ordine
        m = re.search(r'(?:N[°.r]?|Numero)\s*(?:Ordine|Order)[:\s]*(\S+)', text, re.I)
        if m:
            data['numero_ordine'] = m.group(1)
        
        # Cerca P.IVA
        piva = self.extract_piva(text)
        if piva:
            data['partita_iva'] = piva.zfill(11)  # Mantiene/aggiunge zeri iniziali
        
        # Cerca codici AIC (9 cifre che iniziano con 0)
        n = 0
        for aic in re.findall(r'\b(0\d{8})\b', text):
            n += 1
            aic_info = self.normalize_aic(aic, '')
            row = self.create_empty_row(n)
            row['codice_aic'] = aic_info['aic']
            row['codice_originale'] = aic_info['aic_orig']
            row['q_venduta'] = 1
            data['righe'].append(row)
        
        return [data] if data['righe'] or data['numero_ordine'] else []
