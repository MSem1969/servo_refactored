# =============================================================================
# TO_EXTRACTOR v6.2 - ESTRATTORE BAYER
# =============================================================================
# Vendor: Bayer S.p.A.
# Riferimento: REGOLE_BAYER.md v2.0
# Particolarità:
#   - Doppio blocco (GROSSISTA + CLIENTE)
#   - Date consegna multiple per documento
#   - Sconto merce extra
#   - Espositori 6 cifre con padding "5"
# =============================================================================

import re
from typing import List, Dict, Any
from collections import defaultdict

from .base import BaseExtractor


class BayerExtractor(BaseExtractor):
    """
    Estrattore per Transfer Order BAYER v2.0.

    Caratteristiche:
    - Formato Transfer Order Bayer
    - Numero ordine in formato IT25O-XXXXX
    - Dati cliente in blocco CLIENTE (dopo COOPERATIVA/GROSSISTA)
    - Supporto date consegna multiple con split ordini
    - Gestione sconto merce + sconto extra
    - Espositori con codici 6 cifre (padding 5XXXXXX)
    """

    vendor = "BAYER"

    # Pattern specifici BAYER
    PATTERNS = {
        'numero_ordine': r'NUM\.\s*PROP\.\s*D\'ORDINE\s+(IT\d{2}O-\d+)',
        'data_ordine': r'DATA\s+ACQUISIZIONE\s+(\d{1,2})\s+(\w{3,9})\s+(\d{4})',
        'data_consegna': r'DATA\s+(?:DI\s+)?CONSEGNA.*?(\d{1,2})\s+(\w{3,9})\s+(\d{4})',
        'piva': r'P\.IVA:\s*(\d{11})',
        'provincia': r'\(([A-Z]{2})\)',
        'gg_dilazione': r'(\d+)\s*gg',
    }

    # Mesi italiani per conversione date
    MESI_IT = {
        'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
        'set': '09', 'ott': '10', 'nov': '11', 'dic': '12',
        'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
        'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
        'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12',
    }

    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """
        Estrae ordini da PDF BAYER.

        Se ci sono date consegna multiple, crea ordini separati:
        - Singola data: numero_ordine originale
        - Multiple date: numero_ordine_a, numero_ordine_b, etc.
        """
        # === ESTRAZIONE HEADER COMUNE ===
        header = self._extract_header(text, lines)

        # === ESTRAZIONE RIGHE CON DATE CONSEGNA ===
        righe_con_date = self._extract_rows_with_dates(text, lines)

        # === RAGGRUPPA PER DATA CONSEGNA ===
        righe_per_data = defaultdict(list)
        for riga in righe_con_date:
            data_consegna = riga.get('data_consegna_riga') or header.get('data_consegna') or ''
            righe_per_data[data_consegna].append(riga)

        # === GENERA ORDINI ===
        ordini = []
        date_ordinate = sorted(righe_per_data.keys())

        if len(date_ordinate) <= 1:
            # Singola data o nessuna data: ordine unico
            data = header.copy()
            data['righe'] = righe_con_date
            if date_ordinate:
                data['data_consegna'] = date_ordinate[0]
            ordini.append(data)
        else:
            # Multiple date: split ordini con suffisso
            suffissi = 'abcdefghijklmnopqrstuvwxyz'
            for idx, data_consegna in enumerate(date_ordinate):
                data = header.copy()
                suffisso = suffissi[idx] if idx < len(suffissi) else str(idx + 1)
                data['numero_ordine'] = f"{header.get('numero_ordine', '')}_{suffisso}"
                data['data_consegna'] = data_consegna

                # Rinumera righe per questo ordine
                righe_ordine = []
                for n, riga in enumerate(righe_per_data[data_consegna], 1):
                    riga_copy = riga.copy()
                    riga_copy['n_riga'] = n
                    righe_ordine.append(riga_copy)

                data['righe'] = righe_ordine
                ordini.append(data)

        return ordini

    def _extract_header(self, text: str, lines: List[str]) -> Dict[str, Any]:
        """Estrae dati header comuni."""
        data = self.create_empty_order()
        data['vendor'] = self.vendor

        # BAYER-H01: Grossista (primo blocco con SAP)
        data['grossista'] = self._extract_grossista(lines)

        # BAYER-H02: Ragione Sociale Cliente (secondo blocco con SAP)
        cliente = self._extract_cliente(lines)
        data.update(cliente)

        # BAYER-H06: Numero Ordine
        m = re.search(self.PATTERNS['numero_ordine'], text)
        if m:
            data['numero_ordine'] = m.group(1)

        # BAYER-H07: Data Ordine
        m = re.search(self.PATTERNS['data_ordine'], text, re.IGNORECASE)
        if m:
            data['data_ordine'] = self._parse_date_italian(m.group(1), m.group(2), m.group(3))

        # Data Consegna (default dal header se presente)
        m = re.search(self.PATTERNS['data_consegna'], text, re.IGNORECASE)
        if m:
            data['data_consegna'] = self._parse_date_italian(m.group(1), m.group(2), m.group(3))

        # BAYER-T08: Condizioni Pagamento
        m = re.search(self.PATTERNS['gg_dilazione'], text)
        if m:
            data['gg_dilazione'] = int(m.group(1))
        else:
            data['gg_dilazione'] = 60  # Default BAYER

        return data

    def _extract_grossista(self, lines: List[str]) -> str:
        """
        Estrae ragione sociale del grossista (COOPERATIVA/GROSSISTA).

        Struttura:
        ```
        COOPERATIVA/ GROSSISTA
        1002338729 (SAP: 0005308522)
        FARVIMA MEDICINALI S.P.A.
        ```
        """
        # Trova intestazione COOPERATIVA/GROSSISTA
        for i, line in enumerate(lines):
            line_upper = line.upper()
            if 'COOPERATIVA' in line_upper and 'GROSSISTA' in line_upper:
                # Cerca SAP nelle righe successive (max 5)
                for j in range(i + 1, min(i + 6, len(lines))):
                    if '(SAP:' in lines[j]:
                        # Ragione sociale è la riga successiva al SAP
                        if j + 1 < len(lines):
                            next_line = lines[j + 1].strip()
                            # Verifica che non sia P.IVA
                            if next_line and not next_line.startswith('P.IVA'):
                                return self.clean_text(next_line, 100)
                        break
                break

        # Fallback: primo blocco SAP (se non trovato intestazione)
        for i, line in enumerate(lines):
            if '(SAP:' in line and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('P.IVA'):
                    return self.clean_text(next_line, 100)

        return ''

    def _extract_cliente(self, lines: List[str]) -> Dict[str, Any]:
        """
        Estrae dati completi del cliente (farmacia destinataria).

        Struttura BAYER (secondo blocco dopo COOPERATIVA/GROSSISTA):
        ```
        1002345057 (SAP: 0003346340)
        FARMACIA PICAZIO DR.NICOLETTA
        P.IVA: 03011890617 - C.F.:PCZNLT61H68A243I
        VIA NAPOLI 240
        ARZANO
        (NA)
        ```
        """
        result = {
            'ragione_sociale': '',
            'partita_iva': '',
            'indirizzo': '',
            'citta': '',
            'provincia': '',
            'cap': '',
        }

        # Trova il SECONDO blocco con pattern SAP (il primo è GROSSISTA)
        sap_indices = []
        for i, line in enumerate(lines):
            if '(SAP:' in line or re.search(r'\d{10}\s*\(SAP:', line):
                sap_indices.append(i)

        if len(sap_indices) < 2:
            # Fallback: cerca etichetta "CLIENTE"
            for i, line in enumerate(lines):
                if line.strip().upper() == 'CLIENTE':
                    # Cerca SAP dopo CLIENTE
                    for j in range(i, min(i + 5, len(lines))):
                        if '(SAP:' in lines[j]:
                            sap_indices = [0, j]  # Fake primo, reale secondo
                            break
                    break

        if len(sap_indices) < 2:
            return result

        cliente_sap_idx = sap_indices[1]

        # BAYER-H02: Ragione Sociale - riga DOPO il codice SAP
        if cliente_sap_idx + 1 < len(lines):
            next_line = lines[cliente_sap_idx + 1].strip()
            # Verifica che non sia P.IVA (in quel caso ragione sociale è sulla stessa riga)
            if not next_line.startswith('P.IVA'):
                result['ragione_sociale'] = self.clean_text(next_line, 80)

        # Cerca P.IVA, indirizzo, città, provincia nelle righe successive
        for i in range(cliente_sap_idx, min(cliente_sap_idx + 12, len(lines))):
            line = lines[i].strip()

            # BAYER-H03: P.IVA
            m = re.search(r'P\.?IVA:?\s*(\d{11})', line)
            if m and not result['partita_iva']:
                result['partita_iva'] = m.group(1)
                piva_line_idx = i

                # BAYER-H04: Indirizzo - riga DOPO P.IVA
                if i + 1 < len(lines):
                    ind_line = lines[i + 1].strip()
                    # L'indirizzo non deve essere città o provincia
                    if ind_line and not re.match(r'^\([A-Z]{2}\)$', ind_line) and len(ind_line) > 3:
                        result['indirizzo'] = self.clean_text(ind_line, 60)

            # BAYER-H05: Provincia - pattern "(XX)" da solo o attaccato alla città
            m = re.search(r'\(([A-Z]{2})\)', line)
            if m and not result['provincia']:
                result['provincia'] = m.group(1)

                # Città: può essere sulla stessa riga prima di (XX) o riga precedente
                citta_match = re.match(r'^([A-Z][A-Za-z\s\'\.]+?)\s*\([A-Z]{2}\)', line)
                if citta_match:
                    # Città sulla stessa riga: "ARZANO(NA)" o "ARZANO (NA)"
                    result['citta'] = self.clean_text(citta_match.group(1), 50)
                elif line == f"({m.group(1)})":
                    # Provincia da sola su riga: città è riga precedente
                    if i > 0:
                        prev_line = lines[i - 1].strip()
                        # Verifica che non sia indirizzo (contiene VIA, CORSO, etc.)
                        if prev_line and not any(kw in prev_line.upper() for kw in ['VIA ', 'CORSO ', 'PIAZZA ', 'VIALE ']):
                            result['citta'] = self.clean_text(prev_line, 50)

        return result

    def _extract_rows_with_dates(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        """
        Estrae righe prodotto con date consegna individuali.

        Cerca pattern per identificare blocchi con date consegna diverse.
        """
        result = []
        n = 0
        current_data_consegna = ''

        # Pattern per identificare header di sezione con data consegna
        data_section_pattern = re.compile(
            r'(?:DATA\s+(?:DI\s+)?CONSEGNA|CONSEGNA\s+(?:PREVISTA|DEL)?)\s*[:\s]*(\d{1,2})\s+(\w{3,9})\s+(\d{4})',
            re.IGNORECASE
        )

        # Pattern per riga prodotto BAYER
        # Formato: CODICE | DESCRIZIONE | QTY VENDITA | PREZZO | QTY SCONTO | SCONTO EXTRA | GG
        row_pattern = re.compile(
            r'^(\d{6,10})\s+'           # Codice (6-10 cifre)
            r'(.+?)\s+'                  # Descrizione
            r'(\d+)\s+'                  # Quantità vendita
            r'€?\s*([\d,.]+)\s*'         # Prezzo
            r'(?:(\d+)\s+)?'             # Quantità sconto merce (opzionale)
            r'(?:(\d+)\s+)?'             # Merce sconto extra (opzionale)
            r'(?:(\d+)\s*gg)?'           # Giorni dilazione (opzionale)
        )

        # Pattern alternativo più semplice
        simple_row_pattern = re.compile(
            r'^(\d{6,10})\s+'            # Codice
            r'([A-Za-z][\w\s\.\-\%\/]+?)\s+'  # Descrizione (inizia con lettera)
            r'(\d+)\s+'                  # Quantità
            r'€?\s*([\d,.]+)'            # Prezzo
        )

        for line in lines:
            line_stripped = line.strip()

            # Cerca nuova sezione con data consegna
            m = data_section_pattern.search(line)
            if m:
                current_data_consegna = self._parse_date_italian(m.group(1), m.group(2), m.group(3))
                continue

            # Cerca riga prodotto
            m = row_pattern.match(line_stripped)
            if not m:
                m = simple_row_pattern.match(line_stripped)

            if m:
                n += 1
                codice_raw = m.group(1)
                desc = self.clean_text(m.group(2), 60)

                # Gestione codice AIC ed espositori
                aic_info = self._normalize_bayer_code(codice_raw, desc)

                row = self.create_empty_row(n)
                row['codice_aic'] = aic_info['aic']
                row['codice_originale'] = aic_info['aic_orig']
                row['descrizione'] = desc
                row['q_venduta'] = self.parse_int(m.group(3))
                row['prezzo_netto'] = self.parse_float(m.group(4))
                row['is_espositore'] = aic_info['is_espositore']
                row['is_no_aic'] = aic_info['is_no_aic']
                row['data_consegna_riga'] = current_data_consegna

                # Campi opzionali (se pattern completo)
                if len(m.groups()) >= 5 and m.group(5):
                    row['q_sconto_merce'] = self.parse_int(m.group(5))
                if len(m.groups()) >= 6 and m.group(6):
                    row['merce_sconto_extra'] = self.parse_int(m.group(6))

                result.append(row)

        return result

    def _normalize_bayer_code(self, codice: str, descrizione: str = '') -> Dict[str, Any]:
        """
        Normalizza codice prodotto BAYER.

        - 6 cifre: espositore, padding con "5" (es: 091639 → 500091639)
        - 7-8 cifre: padding a 9 cifre con 0
        - 9 cifre: AIC standard
        - 10+ cifre: troncamento a 9
        """
        codice = codice.strip().lstrip('0') or '0'
        is_espositore = False
        is_no_aic = False

        # Identificazione espositori da descrizione
        desc_upper = descrizione.upper()
        if any(kw in desc_upper for kw in ['EXPO', 'ESPOSITORE', 'DISPLAY', 'BANCO']):
            is_espositore = True

        # Normalizzazione codice
        codice_orig = codice
        codice_len = len(codice)

        if codice_len == 6:
            # Espositore con padding "5"
            aic = f"500{codice.zfill(6)}"
            is_espositore = True
        elif codice_len <= 9:
            # Padding a 9 cifre
            aic = codice.zfill(9)
        else:
            # Troncamento (>9 cifre)
            aic = codice[:9]

        return {
            'aic': aic,
            'aic_orig': codice_orig,
            'is_espositore': 1 if is_espositore else 0,
            'is_no_aic': 1 if is_no_aic else 0,
        }

    def _parse_date_italian(self, day: str, month: str, year: str) -> str:
        """
        Converte data con mese italiano in DD/MM/YYYY.

        Es: "20", "ott", "2025" → "20/10/2025"
        """
        day_int = int(day)
        month_lower = month.lower()[:3]
        month_num = self.MESI_IT.get(month_lower, '01')
        return f"{day_int:02d}/{month_num}/{year}"
