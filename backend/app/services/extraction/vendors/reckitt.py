"""
EXTRACTOR_TO - Estrattore RECKITT v11.4
=======================================
Reckitt Benckiser Healthcare (Italia) S.p.A.

Formato Transfer Order con tabella prodotti strutturata:
- Cod. Art. | Descr. Articolo | Qta | Listino | 1°Col | 2°Col | Cassa | SM | Data Consegna | Netto U | Netto | Cod AIC

Particolarità:
- AIC a 9 cifre in ultima colonna
- Cliente con codice SAP tra parentesi es: (1000053731)
- Indirizzo in formato: VIA, NUM, CITTA, PROV, CAP
- Sconto Merce (SM) nella colonna dedicata
- Supporto multipagina con delimitatore "Pagina n di y"
- Supporto multi-ordine nello stesso PDF

v11.4 (2026-02-05):
- Aggiunta gestione multi-ordine come DOC_GENERICI
- Fine ordine = quando Pagina n = y (ultima pagina)
- Fix estrazione header con approccio semantico/sequenziale
"""

import re
from typing import Dict, List, Tuple

from ....utils import parse_date

# Import pdfplumber opzionale
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


def _normalize_aic_reckitt(codice: str, descrizione: str = '') -> Tuple[str, str, bool, bool]:
    """
    Normalizza AIC specifico per RECKITT.

    RECKITT usa AIC a 9 cifre standard.
    Rileva espositori da descrizione (EXPO, ESPOSITORE, etc.)

    Args:
        codice: Codice AIC originale
        descrizione: Descrizione prodotto (per rilevare espositore)

    Returns:
        Tuple (aic_normalized, aic_originale, is_espositore, is_child)
    """
    codice = str(codice).strip() if codice else ''
    aic_orig = codice
    is_espositore = False
    is_child = False

    # Rileva espositore da descrizione
    esp_keywords = ['EXPO', 'ESPOSITORE', 'DISPLAY', 'BANCO', 'TERRA']
    desc_upper = descrizione.upper() if descrizione else ''
    for kw in esp_keywords:
        if kw in desc_upper:
            is_espositore = True
            break

    # Estrae solo cifre
    aic_digits = re.sub(r'[^\d]', '', codice)

    # Padding a 9 cifre se necessario
    if aic_digits and len(aic_digits) < 9:
        aic_padded = aic_digits.zfill(9)
    else:
        aic_padded = aic_digits

    return aic_padded, aic_orig, is_espositore, is_child


def extract_reckitt(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore RECKITT v11.4.

    MULTI-ORDINE: Ogni PDF può contenere più ordini!

    Delimitazione ordini:
    - Ogni ordine inizia con numero "SO########_##"
    - Ogni ordine termina con "Pagina n di y" dove n = y (ultima pagina)
    - Se n < y, l'ordine continua nella pagina successiva
    - Header ripetuto su pagine successive viene ignorato (stesso numero ordine)

    Usa pdfplumber per estrarre tabelle strutturate.
    Fallback su parsing testo se pdf_path non disponibile.

    Args:
        text: Testo completo del PDF
        lines: Linee del testo
        pdf_path: Percorso al file PDF (opzionale)

    Returns:
        Lista di dict, uno per ogni ordine nel PDF
    """
    orders = []
    current_order = None
    current_lines = []

    # Pattern per identificare inizio nuovo ordine: SO0000151700XXXX_01
    pattern_nuovo_ordine = re.compile(r'\b(SO\d{10,}_\d{2})\b')

    # Pattern per identificare fine pagina/ordine: "Pagina n di y"
    pattern_pagina = re.compile(r'Pagina\s+(\d+)\s+di\s+(\d+)', re.I)

    for i, line in enumerate(lines):
        # Rileva inizio nuovo ordine
        m = pattern_nuovo_ordine.search(line)
        if m:
            nuovo_numero = m.group(1)

            # Verifica se è lo stesso ordine (pagina successiva) o un ordine diverso
            if current_order and current_order.get('numero_ordine') == nuovo_numero:
                # Stesso numero ordine = continuazione su pagina successiva
                # Non creare nuovo ordine, continua ad accumulare righe
                continue

            # Numero ordine diverso: finalizza ordine precedente e inizia nuovo
            if current_order and current_order.get('numero_ordine'):
                _finalize_order(current_order, current_lines, pdf_path)
                orders.append(current_order)

            # Inizia nuovo ordine
            current_order = _create_new_order()
            current_order['numero_ordine'] = nuovo_numero

            # Estrai data ordine dalla stessa riga
            m_data = re.search(r'SO\d+_\d+\s+(\d{2}-\d{2}-\d{4})', line)
            if m_data:
                current_order['data_ordine'] = parse_date(m_data.group(1))

            current_lines = [line]
            continue

        # Controlla se siamo a fine pagina (Pagina n di y)
        m_pag = pattern_pagina.search(line)
        if m_pag and current_order:
            pagina_corrente = int(m_pag.group(1))
            pagina_totale = int(m_pag.group(2))

            # Aggiungi la riga
            current_lines.append(line)

            # Se è l'ultima pagina dell'ordine (n = y), finalizza
            if pagina_corrente == pagina_totale:
                _finalize_order(current_order, current_lines, pdf_path)
                orders.append(current_order)
                current_order = None
                current_lines = []
            # Altrimenti (n < y) l'ordine continua, non finalizzare
            continue

        # Accumula righe per l'ordine corrente
        if current_order:
            current_lines.append(line)

    # Finalizza l'ultimo ordine se non è già stato finalizzato
    # (caso di PDF senza footer "Pagina n di y")
    if current_order and current_order.get('numero_ordine'):
        _finalize_order(current_order, current_lines, pdf_path)
        orders.append(current_order)

    return orders


def _create_new_order() -> Dict:
    """Crea struttura dati per nuovo ordine RECKITT."""
    return {
        'vendor': 'RECKITT',
        'numero_ordine': '',
        'data_ordine': '',
        'data_consegna': '',
        'nome_agente': '',
        'ragione_sociale': '',
        'indirizzo': '',
        'cap': '',
        'citta': '',
        'provincia': '',
        'righe': [],
    }


def _finalize_order(order: Dict, lines: List[str], pdf_path: str = None):
    """
    Finalizza un ordine estraendo header e prodotti dalle righe accumulate.

    NOTA: Per supportare multi-ordine, l'estrazione prodotti usa SEMPRE
    il text parsing sulle righe accumulate (non pdfplumber che legge tutto il PDF).

    Args:
        order: Dizionario ordine da completare
        lines: Righe di testo accumulate per questo ordine
        pdf_path: Percorso PDF (non usato per prodotti in multi-ordine)
    """
    # Ricostruisci il testo dalle righe
    text = '\n'.join(lines)

    # === ESTRAI HEADER ===
    _extract_header(order, text)

    # === ESTRAI PRODOTTI ===
    # Usa sempre text parsing per garantire estrazione solo delle righe
    # di questo ordine (pdfplumber leggerebbe tutto il PDF)
    order['righe'] = _extract_products_from_text(text, lines)


def _extract_header(order: Dict, text: str):
    """
    Estrae campi header dal testo dell'ordine.

    Approccio semantico/sequenziale per gestire testo spezzato su più righe.
    """
    # Data consegna e nome agente
    m = re.search(r'VENDITORE\s+DATA\s+CONSEGNA[^\n]*\n([A-Z][A-Z\s]+?)\s+(\d{2}-\d{2}-\d{4})', text)
    if m:
        order['nome_agente'] = m.group(1).strip()[:50]
        order['data_consegna'] = parse_date(m.group(2))

    # === CLIENTE E INDIRIZZO (Approccio semantico/sequenziale) ===
    # Formato RECKITT con testo spezzato su più righe e nome agente in mezzo:
    # "Cliente : FARMACIA MAGLIULO DR.SSA ANTONELLA MAGLIULO & c. (1000091"
    # "MICHELE VAIANO 28-11-2025 760) VIA MICHELE CARAVELLI 27/29, TORRE ANNUNZIATA, NA, 80058"

    # Normalizza il testo: rimuovi newline per gestire testo spezzato
    text_normalized = re.sub(r'\s+', ' ', text)

    # Keywords che identificano l'inizio dell'indirizzo
    addr_keywords = r'(?:VIA|VIALE|CORSO|PIAZZA|PIAZZALE|LARGO|VICOLO|STRADA|CONTRADA|LOC\.|LOCALITA)'

    # Pattern unico che cattura tutta la sequenza
    cliente_pattern = re.search(
        r'Cliente\s*:\s*'                          # Marker "Cliente :"
        r'([A-Z][A-Z0-9\s\.\'\&\-]+?)'             # Ragione sociale (gruppo 1)
        r'\s*\([^)]+\)\s*'                         # (codice SAP) - ignorato
        r'.*?'                                     # Qualsiasi cosa (agente, data) - ignorato
        r'(' + addr_keywords + r'[A-Z0-9\s\.\,\/\-]+?)'  # Indirizzo da keyword (gruppo 2)
        r',\s*([A-Z][A-Z\s\']+?)'                  # Città (gruppo 3)
        r',\s*([A-Z]{2})'                          # Provincia (gruppo 4)
        r',\s*(\d{5})',                            # CAP (gruppo 5)
        text_normalized, re.I
    )

    if cliente_pattern:
        order['ragione_sociale'] = cliente_pattern.group(1).strip()[:80]
        order['indirizzo'] = cliente_pattern.group(2).strip()[:50]
        order['citta'] = cliente_pattern.group(3).strip()[:50]
        order['provincia'] = cliente_pattern.group(4).upper()[:5]
        order['cap'] = cliente_pattern.group(5).strip()[:5]


def _extract_products_from_pdf(pdf_path: str, data: Dict) -> List[Dict]:
    """
    Estrae prodotti dalla tabella PDF usando pdfplumber.

    Colonne tabella RECKITT:
    | Cod. Art. | Descr. Articolo | Qta | Listino | 1°Col | 2°Col | Cassa | SM | Data Consegna | Netto U | Netto | Cod AIC |
    """
    righe = []
    n = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                if not table:
                    continue

                for row in table:
                    if not row or len(row) < 10:
                        continue

                    # Skip header row
                    if row[0] and 'Cod' in str(row[0]) and 'Art' in str(row[0]):
                        continue

                    # Verifica che la prima colonna sia un codice articolo (numerico)
                    cod_art = str(row[0]).strip() if row[0] else ''
                    if not cod_art or not re.match(r'^\d+$', cod_art):
                        continue

                    try:
                        # Estrai campi dalla riga
                        # row[0] = Cod. Art.
                        # row[1] = Descr. Articolo
                        # row[2] = Qta
                        # row[3] = Listino
                        # row[4] = 1°Col (sconto %)
                        # row[5] = 2°Col (sconto %)
                        # row[6] = Cassa
                        # row[7] = SM (Sconto Merce)
                        # row[8] = Data Consegna
                        # row[9] = Netto U
                        # row[10] = Netto
                        # row[11] = Cod AIC

                        descrizione = str(row[1]).strip() if row[1] else ''

                        # Quantità
                        qta_str = str(row[2]).strip() if row[2] else '0'
                        qta = int(re.sub(r'[^\d]', '', qta_str) or '0')

                        # Prezzo listino (pubblico)
                        listino_str = str(row[3]).strip() if row[3] else '0'
                        listino = _parse_price(listino_str)

                        # Sconto Merce (SM)
                        sm_str = str(row[7]).strip() if len(row) > 7 and row[7] else '0'
                        sconto_merce = int(re.sub(r'[^\d]', '', sm_str) or '0')

                        # Prezzo netto unitario
                        netto_u_str = str(row[9]).strip() if len(row) > 9 and row[9] else '0'
                        netto_u = _parse_price(netto_u_str)

                        # Prezzo netto totale
                        netto_str = str(row[10]).strip() if len(row) > 10 and row[10] else '0'
                        netto_tot = _parse_price(netto_str)

                        # Codice AIC (ultima colonna)
                        aic_raw = str(row[11]).strip() if len(row) > 11 and row[11] else ''

                        # Data consegna riga
                        data_consegna_riga = ''
                        if len(row) > 8 and row[8]:
                            dc_str = str(row[8]).strip()
                            if re.match(r'\d{2}[-/]\d{2}[-/]\d{4}', dc_str):
                                data_consegna_riga = parse_date(dc_str)

                        # Normalizza AIC
                        aic_norm, aic_orig, is_esp, is_child = _normalize_aic_reckitt(aic_raw, descrizione)

                        if qta > 0 or aic_norm:
                            n += 1
                            righe.append({
                                'n_riga': n,
                                'codice_articolo': cod_art,
                                'codice_aic': aic_norm,
                                'codice_originale': aic_orig,
                                'descrizione': descrizione[:40],
                                'q_venduta': qta,
                                'q_sconto_merce': sconto_merce,
                                'prezzo_pubblico': listino,
                                'prezzo_netto': netto_u,
                                'prezzo_netto_totale': netto_tot,
                                'data_consegna_riga': data_consegna_riga,
                                'is_espositore': is_esp,
                                'is_child': is_child,
                            })

                    except Exception as e:
                        print(f"   ⚠️ Errore parsing riga RECKITT: {e} - row: {row}")
                        continue

    return righe


def _extract_products_from_text(text: str, lines: List[str]) -> List[Dict]:
    """
    Fallback: estrae prodotti dal testo quando PDF non disponibile.

    Pattern riga:
    COD_ART DESCRIZIONE QTA LISTINO SCONTO1 SCONTO2 CASSA SM DATA NETTO_U NETTO AIC
    """
    righe = []
    n = 0

    # Pattern per riga prodotto con AIC a 9 cifre alla fine
    # Es: 3259113 DUREX GEL MASSAGE 2IN1 ALOE VERA 200ML 24 7.74 32.00 0.00 0.00 0 27-11-2025 5.26 126.32 986705933
    product_pattern = re.compile(
        r'^(\d{6,7})\s+'           # Cod. Art. (6-7 cifre)
        r'(.+?)\s+'                # Descrizione
        r'(\d+)\s+'                # Qta
        r'([\d,.]+)\s+'            # Listino
        r'([\d,.]+)\s+'            # 1°Col
        r'([\d,.]+)\s+'            # 2°Col
        r'([\d,.]+)\s+'            # Cassa
        r'(\d+)\s+'                # SM
        r'(\d{2}-\d{2}-\d{4})\s+'  # Data Consegna
        r'([\d,.]+)\s+'            # Netto U
        r'([\d,.]+)\s+'            # Netto
        r'(\d{9})$'                # Cod AIC (9 cifre)
    )

    for line in lines:
        line = line.strip()
        m = product_pattern.match(line)
        if m:
            n += 1
            cod_art = m.group(1)
            descrizione = m.group(2).strip()
            qta = int(m.group(3))
            listino = _parse_price(m.group(4))
            sconto_merce = int(m.group(8))
            data_consegna = parse_date(m.group(9))
            netto_u = _parse_price(m.group(10))
            netto_tot = _parse_price(m.group(11))
            aic_raw = m.group(12)

            aic_norm, aic_orig, is_esp, is_child = _normalize_aic_reckitt(aic_raw, descrizione)

            righe.append({
                'n_riga': n,
                'codice_articolo': cod_art,
                'codice_aic': aic_norm,
                'codice_originale': aic_orig,
                'descrizione': descrizione[:40],
                'q_venduta': qta,
                'q_sconto_merce': sconto_merce,
                'prezzo_pubblico': listino,
                'prezzo_netto': netto_u,
                'prezzo_netto_totale': netto_tot,
                'data_consegna_riga': data_consegna,
                'is_espositore': is_esp,
                'is_child': is_child,
            })

    return righe


def _parse_price(price_str: str) -> float:
    """Parse prezzo da stringa con formati vari (1.234,56 o 1234.56)."""
    if not price_str:
        return 0.0

    price_str = str(price_str).strip()

    # Rimuovi spazi
    price_str = price_str.replace(' ', '')

    # Formato italiano: 1.234,56 -> 1234.56
    if ',' in price_str and '.' in price_str:
        price_str = price_str.replace('.', '').replace(',', '.')
    # Formato italiano senza migliaia: 123,45 -> 123.45
    elif ',' in price_str:
        price_str = price_str.replace(',', '.')

    try:
        return float(price_str)
    except ValueError:
        return 0.0
