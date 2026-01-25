"""
EXTRACTOR_TO - Estrattore BAYER v11.2
=====================================
Convertito da SERV.O_v6_0_DB_def.ipynb - Cella 7
Regole: REGOLE_BAYER.md

v11.2: Usa estrazione tabellare per mappare correttamente colonne date consegna
       Gestisce prodotti con consegne su date diverse (righe separate)
v11.1: Rimossa logica espositore parent/child (BAYER espositori sono prodotti autonomi)
       Aggiunto supporto date consegna multiple da header colonna
       Anomalia per AIC non conforme (diverso da 9 cifre)
"""

import re
import pdfplumber
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ....utils import parse_date, parse_decimal, parse_int, normalize_aic_simple, format_piva


# Keywords per identificare espositori (flag informativo, NO logica parent/child)
ESPOSITORE_KEYWORDS = ['BANCO', 'DBOX', 'FSTAND', 'EXPO', 'DISPLAY', 'ESPOSITORE', 'CESTA']


def _is_espositore(descrizione: str) -> bool:
    """Verifica se il prodotto è un espositore (solo flag informativo)."""
    desc_upper = descrizione.upper()
    return any(kw in desc_upper for kw in ESPOSITORE_KEYWORDS)


def _parse_date_header(text: str, lines: List[str] = None) -> List[Tuple[str, Optional[datetime]]]:
    """
    Estrae le date consegna dagli header colonna della sezione CONSEGNE.

    BAYER ha due formati possibili per le date:
    1. Date complete su una riga: "5 nov 2025", "26 nov 2025"
    2. Date splittate su più righe (tabella PDF):
       - Riga 1: "Q.tà Merce 20 20 CONDIZIONI"  (giorni)
       - Riga 2: "ARTICOLO Merce Sconto ott dic PAGAMENTO"  (mesi)
       - Riga 3: "Sconto Extra 2025 2026 PARTICOLARI"  (anni)

    Returns:
        Lista di tuple (data_raw, data_parsed) ordinate per posizione nel testo
    """
    dates = []

    # Prima prova: date complete nel testo (formato "giorno mese anno")
    date_pattern = r'(\d{1,2})\s+(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s+(\d{4})'
    for match in re.finditer(date_pattern, text, re.IGNORECASE):
        date_raw = match.group(0)
        date_parsed = parse_date(date_raw)
        if date_parsed and date_parsed not in [d[1] for d in dates]:
            dates.append((date_raw, date_parsed))

    # Se trovate 2+ date, abbiamo finito
    if len(dates) >= 2:
        return dates

    # Seconda prova: date splittate su più righe (formato tabella BAYER)
    # Cerca la sezione CONSEGNE e ricostruisci le date
    if lines:
        lines_text = '\n'.join(lines)

        # Pattern per trovare le righe header con giorni, mesi, anni separati
        # Cerca righe tipo "... 20 20 ..." (giorni), "... ott dic ..." (mesi), "... 2025 2026 ..." (anni)
        days_pattern = r'(?:Merce|CONDIZIONI)[^\d]*(\d{1,2})\s+(\d{1,2})'
        months_pattern = r'(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s+(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)'
        years_pattern = r'(202[4-9]|203\d)\s+(202[4-9]|203\d)'

        days_match = re.search(days_pattern, lines_text, re.IGNORECASE)
        months_match = re.search(months_pattern, lines_text, re.IGNORECASE)
        years_match = re.search(years_pattern, lines_text)

        if days_match and months_match and years_match:
            day1, day2 = days_match.group(1), days_match.group(2)
            month1, month2 = months_match.group(1), months_match.group(2)
            year1, year2 = years_match.group(1), years_match.group(2)

            # Ricostruisci le date
            date1_raw = f"{day1} {month1} {year1}"
            date2_raw = f"{day2} {month2} {year2}"

            date1_parsed = parse_date(date1_raw)
            date2_parsed = parse_date(date2_raw)

            if date1_parsed and date1_parsed not in [d[1] for d in dates]:
                dates.append((date1_raw, date1_parsed))
            if date2_parsed and date2_parsed not in [d[1] for d in dates]:
                dates.append((date2_raw, date2_parsed))

    return dates


def _extract_product_quantities(line: str, num_date_columns: int) -> Optional[Dict]:
    """
    Estrae i dati di una riga prodotto BAYER.

    Formato linea:
    codice descrizione q_vendita € prezzo [quantities...] dilazione gg

    Le quantities corrispondono alle colonne date (1 o più).

    Returns:
        Dict con codice, descrizione, prezzo, e lista quantities per date
        None se la linea non è una riga prodotto valida
    """
    line_stripped = line.strip()

    # Pattern base: codice (7-10 cifre) + descrizione + q_vendita + prezzo
    # Seguito da numeri (quantities) e "gg" finale
    base_pattern = r'^(\d{7,10})\s+(.+?)\s+(\d+)\s+€\s*([\d,\.]+)\s+'

    match = re.match(base_pattern, line_stripped)
    if not match:
        return None

    codice_raw = match.group(1)
    descrizione = match.group(2).strip()
    q_vendita = parse_int(match.group(3))
    prezzo = float(parse_decimal(match.group(4)))

    # Estrai la parte rimanente dopo il prezzo
    remainder = line_stripped[match.end():].strip()

    # Pattern: [numeri...] dilazione gg
    # I numeri prima di "XX gg" sono le quantities per le date
    numbers_match = re.match(r'^([\d\s]+?)\s*(\d+)\s*gg', remainder)
    if not numbers_match:
        return None

    numbers_str = numbers_match.group(1).strip()
    dilazione = parse_int(numbers_match.group(2))

    # Split dei numeri - sono le quantities per le colonne date
    quantities = [parse_int(n) for n in numbers_str.split() if n.strip()]

    # Se abbiamo più quantities del numero di colonne date,
    # le prime potrebbero essere q_merce_sconto e merce_sconto_extra
    # Prendiamo le ultime N quantities come date columns
    if len(quantities) > num_date_columns:
        date_quantities = quantities[-num_date_columns:]
    else:
        date_quantities = quantities
        # Padding con 0 se mancano colonne
        while len(date_quantities) < num_date_columns:
            date_quantities.append(0)

    return {
        'codice_raw': codice_raw,
        'descrizione': descrizione[:40],
        'q_vendita': q_vendita,
        'prezzo': prezzo,
        'dilazione': dilazione,
        'date_quantities': date_quantities,
    }


def _validate_aic(codice_raw: str) -> Tuple[str, bool, Optional[str]]:
    """
    Valida e normalizza il codice AIC.

    Returns:
        Tuple (aic_normalizzato, is_valid, messaggio_anomalia)
    """
    aic_norm = normalize_aic_simple(codice_raw)

    # AIC standard deve essere 9 cifre
    if len(codice_raw) != 9:
        return (
            aic_norm,
            False,
            f"AIC non conforme: {codice_raw} ({len(codice_raw)} cifre invece di 9)"
        )

    return (aic_norm, True, None)


def _extract_products_from_table(pdf_path: str, date_columns: List[Tuple[str, Optional[datetime]]]) -> List[Dict]:
    """
    Estrae i prodotti dalla tabella PDF usando pdfplumber table extraction.

    Struttura colonne BAYER:
    [0] Articolo (codice + descrizione)
    [1] Q.tà Vendita
    [2] Prezzo Cessione
    [3] Q.tà Merce Sconto
    [4] Merce Sconto Extra
    [5] Data colonna 1 (es: 5 nov 2025)
    [6] Data colonna 2 (es: 26 nov 2025)  - se presente
    [...] Altri campi vuoti
    [-1] Condizioni Pagamento (es: "60 gg")

    Returns:
        Lista di dict con dati prodotto e quantità per data
    """
    products = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            tables = pdf.pages[0].extract_tables()
            if not tables:
                return []

            table = tables[0]

            for row in table:
                if not row or not row[0]:
                    continue

                cell0 = row[0]
                if not cell0:
                    continue

                # Cerca righe prodotto: iniziano con codice numerico 7-10 cifre
                # Il codice può essere seguito da descrizione con newline
                cell0_clean = cell0.replace('\n', ' ').strip()
                match = re.match(r'^(\d{7,10})\s+(.+)', cell0_clean)
                if not match:
                    continue

                codice_raw = match.group(1)
                descrizione = match.group(2).strip()[:40]

                # Estrai quantità vendita e prezzo
                q_vendita = 0
                prezzo = 0.0

                if len(row) > 1 and row[1]:
                    q_vendita = parse_int(row[1])
                if len(row) > 2 and row[2]:
                    prezzo_str = row[2].replace('€', '').strip()
                    prezzo = float(parse_decimal(prezzo_str))

                # Estrai dilazione dal ultimo elemento
                dilazione = 60  # default
                if row[-1] and 'gg' in str(row[-1]):
                    dil_match = re.search(r'(\d+)\s*gg', str(row[-1]))
                    if dil_match:
                        dilazione = parse_int(dil_match.group(1))

                # Colonne date: tipicamente indici 5 e 6 (o solo 5 se una sola data)
                # Indice 3 = Q.tà Merce Sconto, Indice 4 = Merce Sconto Extra
                date_col_indices = [5, 6] if len(date_columns) >= 2 else [5]

                date_quantities = []
                for col_idx in date_col_indices:
                    if col_idx < len(row) and row[col_idx]:
                        qty = parse_int(row[col_idx])
                    else:
                        qty = 0
                    date_quantities.append(qty)

                # Padding se necessario
                while len(date_quantities) < len(date_columns):
                    date_quantities.append(0)

                products.append({
                    'codice_raw': codice_raw,
                    'descrizione': descrizione,
                    'q_vendita': q_vendita,
                    'prezzo': prezzo,
                    'dilazione': dilazione,
                    'date_quantities': date_quantities,
                })

    except Exception as e:
        # Fallback: ritorna lista vuota, userà estrazione testo
        print(f"[BAYER] Table extraction failed: {e}")
        return []

    return products


def extract_bayer(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF BAYER (formato SAP).

    Particolarità BAYER:
    - Formato SAP standard
    - Espositori sono prodotti AUTONOMI (no logica parent/child)
    - Date consegna negli header colonna (possono essere multiple)
    - Stesso prodotto può avere consegne su date diverse → righe separate
    - AIC a 10 cifre genera anomalia per revisione
    """
    data = {
        'vendor': 'BAYER',
        'righe': [],
        'anomalie': [],
    }

    # Numero ordine
    for i, line in enumerate(lines):
        if "NUM. PROP" in line and i > 0:
            data['numero_ordine'] = lines[i-1].strip()
            break

    # Data ordine
    for i, line in enumerate(lines):
        if "DATA ACQUISIZIONE" in line and i > 0:
            data['data_ordine'] = parse_date(lines[i-1].strip())
            break

    # Ragione sociale e P.IVA (secondo blocco SAP)
    sap_count = 0
    for i, line in enumerate(lines):
        if '(SAP:' in line:
            sap_count += 1
            if sap_count == 2 and i+1 < len(lines):
                data['ragione_sociale'] = lines[i+1].strip()[:50]
                if i+2 < len(lines) and 'P.IVA:' in lines[i+2]:
                    m = re.search(r'P\.IVA:\s*(\d{11})', lines[i+2])
                    if m:
                        data['partita_iva'] = format_piva(m.group(1))
                break

    # Indirizzo, CAP, Città, Provincia
    for i, line in enumerate(lines):
        if line.strip() == 'CLIENTE' and i+3 < len(lines):
            data['indirizzo'] = lines[i+1].strip()[:50]
            citta_line = lines[i+2].strip()
            cap_citta = re.match(r'^(\d{5})\s+(.+)$', citta_line)
            if cap_citta:
                data['cap'] = cap_citta.group(1)
                data['citta'] = cap_citta.group(2).strip()
            else:
                data['citta'] = citta_line
            prov = lines[i+3].strip()
            if re.match(r'^\([A-Z]{2}\)$', prov):
                data['provincia'] = prov[1:3]
            break

    # Agente
    m = re.search(r'COLLABORATORE\s+([A-Z][A-Z\s]+)', text)
    if m:
        data['nome_agente'] = m.group(1).strip()

    # Dilazione default (verrà sovrascritta per riga se presente)
    m = re.search(r'(\d+)\s*gg', text)
    if m:
        data['gg_dilazione'] = int(m.group(1))

    # ========================================
    # ESTRAZIONE DATE CONSEGNA DA HEADER
    # ========================================
    date_columns = _parse_date_header(text, lines)
    num_date_columns = max(1, len(date_columns))

    # Data consegna default (prima data trovata)
    if date_columns:
        data['data_consegna'] = date_columns[0][1]

    # ========================================
    # ESTRAZIONE RIGHE PRODOTTO
    # ========================================
    righe = []
    anomalie = []
    n_riga = 0

    # Prova prima estrazione tabellare (più accurata per colonne date)
    products = []
    if pdf_path:
        products = _extract_products_from_table(pdf_path, date_columns)

    # Fallback: estrazione da testo se tabella fallisce
    if not products:
        for line in lines:
            product = _extract_product_quantities(line, num_date_columns)
            if product:
                products.append(product)

    # Processa i prodotti estratti
    for product in products:
        # Valida AIC
        aic_norm, aic_valid, aic_anomalia = _validate_aic(product['codice_raw'])

        # Flag espositore (informativo)
        is_espositore = _is_espositore(product['descrizione'])

        # Crea righe separate per ogni data consegna con quantità > 0
        for date_idx, qty in enumerate(product['date_quantities']):
            if qty <= 0:
                continue

            n_riga += 1

            # Determina data consegna per questa riga
            if date_idx < len(date_columns):
                data_consegna = date_columns[date_idx][1]
            else:
                data_consegna = data.get('data_consegna')

            riga = {
                'n_riga': n_riga,
                'codice_aic': aic_norm,
                'codice_originale': product['codice_raw'],
                'descrizione': product['descrizione'],
                'quantita': qty,
                'prezzo_netto': product['prezzo'],
                'aliquota_iva': 10,  # Default IVA
                'valore_netto': product['prezzo'] * qty,
                'data_consegna': data_consegna,
                'is_espositore': is_espositore,
                'tipo_riga': 'PRODOTTO_STANDARD',
            }

            righe.append(riga)

            # Anomalia AIC non conforme
            if not aic_valid and aic_anomalia:
                anomalie.append({
                    'tipo': 'AIC',
                    'codice': 'AIC-A01',
                    'livello': 'ERRORE',
                    'messaggio': aic_anomalia,
                    'n_riga': n_riga,
                    'codice_aic': product['codice_raw'],
                    'descrizione': product['descrizione'],
                })

    data['righe'] = righe
    data['anomalie'] = anomalie

    # Stats per debug
    extraction_method = 'table' if pdf_path and products else 'text'
    data['_stats'] = {
        'extraction_method': extraction_method,
        'date_columns': len(date_columns),
        'date_values': [d[0] for d in date_columns],
        'righe_totali': len(righe),
        'prodotti_estratti': len(products),
        'anomalie_aic': len([a for a in anomalie if a['codice'] == 'AIC-A01']),
        'espositori': len([r for r in righe if r.get('is_espositore')]),
    }

    return [data]
