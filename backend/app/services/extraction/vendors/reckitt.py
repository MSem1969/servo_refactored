"""
EXTRACTOR_TO - Estrattore RECKITT v11.2
=======================================
Reckitt Benckiser Healthcare (Italia) S.p.A.

Formato Transfer Order con tabella prodotti strutturata:
- Cod. Art. | Descr. Articolo | Qta | Listino | 1°Col | 2°Col | Cassa | SM | Data Consegna | Netto U | Netto | Cod AIC

Particolarità:
- AIC a 9 cifre in ultima colonna
- Cliente con codice SAP tra parentesi es: (1000053731)
- Indirizzo in formato: VIA, NUM, CITTA, PROV, CAP
- Sconto Merce (SM) nella colonna dedicata
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
    Estrattore RECKITT v1.0.

    Usa pdfplumber per estrarre tabelle strutturate.
    Fallback su parsing testo se pdf_path non disponibile.

    Args:
        text: Testo completo del PDF
        lines: Linee del testo
        pdf_path: Percorso al file PDF (opzionale)

    Returns:
        Lista con un singolo ordine estratto
    """
    data = {'vendor': 'RECKITT', 'righe': []}

    # === HEADER ===
    # Formato RECKITT: etichette e valori su righe separate
    # Riga 1: "Ordine N. DATA TIPO ORDINE SOCIETA'"
    # Riga 2: "SO00001517001235_01 21-11-2025 Transfer Order IT04 - HEALTHCARE"
    # Riga 3: "VENDITORE DATA CONSEGNA Cliente : ..."
    # Riga 4: "GABRIELE PAGANI 27-11-2025 CORSO 22 MARZO, 23 , MILANO, MI, 20129"

    # Numero ordine: formato SO########_## sulla seconda riga
    m = re.search(r'\b(SO\d{10,}_\d{2})\b', text)
    if m:
        data['numero_ordine'] = m.group(1).strip()

    # Data ordine: prima data DD-MM-YYYY dopo il numero ordine
    m = re.search(r'SO\d+_\d+\s+(\d{2}-\d{2}-\d{4})', text)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    # Data consegna: data sulla riga del venditore (dopo VENDITORE ... DATA CONSEGNA)
    # Pattern: nome agente seguito da data
    m = re.search(r'VENDITORE\s+DATA\s+CONSEGNA[^\n]*\n([A-Z][A-Z\s]+?)\s+(\d{2}-\d{2}-\d{4})', text)
    if m:
        data['nome_agente'] = m.group(1).strip()[:50]
        data['data_consegna'] = parse_date(m.group(2))

    # Cliente: "Cliente : FARMACIA 22 MARZO SAS DI BUCCARELLI VINCENZO (1000053731)"
    m = re.search(r'Cliente\s*:\s*([^(]+)\s*\((\d+)\)', text)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:50]
        data['codice_cliente_sap'] = m.group(2)

    # Indirizzo: sulla stessa riga dopo la data consegna
    # Pattern: "27-11-2025 CORSO 22 MARZO, 23 , MILANO, MI, 20129"
    m = re.search(r'\d{2}-\d{2}-\d{4}\s+([A-Z0-9][^,\n]+,\s*\d+\s*,\s*[A-Z]+,\s*[A-Z]{2},\s*\d{5})', text)
    if m:
        addr_line = m.group(1).strip()
        # Parse indirizzo: "CORSO 22 MARZO, 23 , MILANO, MI, 20129"
        addr_parts = [p.strip() for p in addr_line.split(',')]
        if len(addr_parts) >= 4:
            # Via e civico sono le prime parti
            indirizzo_parts = addr_parts[:-3]
            data['indirizzo'] = ', '.join(indirizzo_parts)[:50]
            data['citta'] = addr_parts[-3].strip()[:50]
            data['provincia'] = addr_parts[-2].strip()[:5]
            data['cap'] = addr_parts[-1].strip()[:5]

    # === ESTRAZIONE PRODOTTI ===
    if pdf_path and PDFPLUMBER_AVAILABLE:
        try:
            data['righe'] = _extract_products_from_pdf(pdf_path, data)
        except Exception as e:
            print(f"   ⚠️ Errore estrazione RECKITT con PDF: {e}")
            data['righe'] = _extract_products_from_text(text, lines)
    else:
        data['righe'] = _extract_products_from_text(text, lines)

    return [data]


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
