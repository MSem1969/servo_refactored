"""
EXTRACTOR_TO - Estrattore PERRIGO
==================================
Estrattore per ordini PERRIGO (Conferma d'Ordine)

Struttura documento:
- Header: "Numero Doc. / Data" → numero ordine / data (GG.MM.AAAA)
- Sezione "Luogo destinazione": ragione sociale, indirizzo, CAP/città/provincia
- NO P.IVA cliente, NO MIN_ID → lookup su indirizzo destinazione
- Tabella prodotti: Linea (10,20,30...), Codice, Descrizione, Q.tà, Sconto%, Listino, Pr.Netto, Valore, %IVA
- Codice in colonna = materiale SAP Perrigo (10 cifre), NON è AIC
- Sotto la descrizione: "MINSAN : XXXXXXXXX" (9 cifre) = AIC ministeriale reale
- Sotto la descrizione: "EAN : XXXXXXXXXXXXXX" (14 cifre) = GTIN (informativo)
- Componenti espositore: righe child sotto "Componenti" con AIC 9 cifre
- Espositore puro (senza MINSAN, solo EAN alfanumerico): is_no_aic=True + child elaborati
- Prodotto regolare (con MINSAN): l'eventuale sezione "Componenti" è info bundle/LE, non child
- Dilazione: default 60 giorni

v1.1: AIC preso da "MINSAN :" anziché dal codice colonna (materiale SAP)
v1.0: Implementazione iniziale
"""

import re
from typing import Dict, List

from ....utils import parse_date, normalize_aic


def extract_perrigo(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF PERRIGO.

    Returns:
        Lista con dizionario ordine estratto
    """
    data = {'vendor': 'PERRIGO', 'righe': []}

    # =========================================================================
    # 1. NUMERO ORDINE e DATA
    # Formato: "Numero Doc. / Data\n300387373 / 08.03.2026"
    # =========================================================================
    m = re.search(r'Numero\s+Doc\.\s*/\s*Data\s*\n?\s*(\d+)\s*/\s*(\d{2}\.\d{2}\.\d{4})', text)
    if m:
        data['numero_ordine'] = m.group(1)
        data['data_ordine'] = parse_date(m.group(2))

    # =========================================================================
    # 2. LUOGO DESTINAZIONE (unico riferimento cliente)
    # Formato:
    #   Luogo destinazione :
    #   Ditta
    #   FARMACIA SPINETTA
    #   VIA GENOVA 152
    #   15121 ALESSANDRIA AL
    # =========================================================================
    dest_match = re.search(
        r'Luogo\s+destinazione\s*:\s*\n'
        r'\s*Ditta\s*\n'
        r'\s*(.+?)\n'              # Ragione sociale
        r'((?:\s*.+?\n)*?)'        # Righe indirizzo (una o più)
        r'\s*(\d{5})\s+(.+?)\s+([A-Z]{2})\s*\n',
        text
    )
    if dest_match:
        data['ragione_sociale'] = dest_match.group(1).strip()[:50]

        # Indirizzo: le righe tra ragione sociale e CAP
        indirizzo_lines = dest_match.group(2).strip()
        if indirizzo_lines:
            # Può essere multi-riga (es. "c/o CENTRO COMMERCIALE\nVIA SCLAVO 15")
            data['indirizzo'] = ' '.join(indirizzo_lines.split('\n')).strip()[:50]

        data['cap'] = dest_match.group(3)
        data['citta'] = dest_match.group(4).strip()[:50]
        data['provincia'] = dest_match.group(5).strip()

    # =========================================================================
    # 3. AGENTE
    # Formato: "Agente di vendita :    Savino Antonio"
    # =========================================================================
    m = re.search(r'Agente\s+di\s+vendita\s*:\s*(.+?)(?:\n|$)', text)
    if m:
        data['nome_agente'] = m.group(1).strip()[:50]

    # =========================================================================
    # 4. DILAZIONE (default 60 giorni)
    # =========================================================================
    data['gg_dilazione'] = 60

    # =========================================================================
    # 5. RIGHE PRODOTTO
    # Formato layout PDF (pdftotext -layout):
    #   Linea 10: "10  8000006212  PHYSIOMER EXPO BANCO PIENO 8 PZ"
    #   Dati:     "1 ST  75,32 /1 ST  34,60 %  49,26 /1 ST  49,26  22%"
    #   Componenti (opzionali):
    #     "Componenti"
    #     "                  PHYSIOMER COUNTER DISPLAY 8 PZ VUOTO   1 ST"
    #     "951553003  PHYSIOMER GETTO NORMALE 135ML GR/IT           2 ST"
    #   Fine: "Data di consegna : 10.03.2026"
    # =========================================================================

    # Strategia: splittiamo per sezione Linea (10, 20, 30...)
    # Ogni blocco Linea contiene: codice, descrizione, prezzi, componenti, data consegna

    # Troviamo tutte le posizioni di "Linea XX" dove XX è multiplo di 10
    linea_positions = list(re.finditer(r'^\s*(\d{2,3})\s+(\d{7,10})\s+(.+?)$', text, re.M))

    n_riga = 0
    for i, lm in enumerate(linea_positions):
        linea_num = int(lm.group(1))
        codice = lm.group(2)
        descrizione = lm.group(3).strip()[:40]

        # Delimita il blocco di testo per questa linea
        start = lm.end()
        if i + 1 < len(linea_positions):
            end = linea_positions[i + 1].start()
        else:
            # Ultima linea: il blocco arriva fino al riepilogo importi
            # ("Importo totale IVA esclusa"), che segue sempre l'ultima
            # "Data di consegna". Usare i separatori "____" tagliava il blocco
            # PRIMA della data (che vive proprio sulla riga separatore).
            m_end = re.search(r'Importo\s+totale\s+IVA\s+esclusa', text[start:])
            end = start + m_end.start() if m_end else len(text)

        block = text[start:end]

        # La riga "Data di consegna" cade su una riga separatore del PDF:
        # pdfplumber intercala i caratteri del testo con gli underscore del
        # separatore (es. "Da_ta_ d_i c_on_s_eg_n_a :_ 2_2._04_.2_02_6").
        # Rimuovendo gli underscore si recupera "Data di consegna : 22.04.2026".
        block_clean = block.replace('_', '')

        # Data di consegna della SINGOLA referenza (in fondo al blocco linea).
        # PERRIGO prevede una data di consegna per prodotto, diversa dalla data
        # di emissione dell'ordine.
        data_consegna = ''
        dc_match = re.search(r'Data\s+di\s+consegna\s*:\s*(\d{2}\.\d{2}\.\d{4})', block_clean)
        if dc_match:
            data_consegna = parse_date(dc_match.group(1))

        # Quantità principale (prima occorrenza di "N ST")
        qty_match = re.search(r'(\d+)\s+ST\b', block)
        q_venduta = int(qty_match.group(1)) if qty_match else 1

        # Prezzo e sconto dalla prima riga dati
        # Pattern: "N ST  75,32 /1 ST  34,60 %  49,26 /1 ST  49,26  22%"
        prezzo_listino = 0.0
        sconto1 = 0.0
        prezzo_netto = 0.0
        valore = 0.0
        aliquota_iva = 0.0

        # Prezzo listino: "75,32 /1 ST"
        pl_match = re.search(r'([\d.,]+)\s*/1\s*ST', block)
        if pl_match:
            prezzo_listino = _parse_price_eu(pl_match.group(1))

        # Sconto %: "34,60 %"
        sc_match = re.search(r'([\d.,]+)\s*%', block)
        if sc_match:
            sconto1 = _parse_price_eu(sc_match.group(1))

        # Prezzo netto: secondo "XX,XX /1 ST" dopo lo sconto
        pn_matches = list(re.finditer(r'([\d.,]+)\s*/1\s*ST', block))
        if len(pn_matches) >= 2:
            prezzo_netto = _parse_price_eu(pn_matches[1].group(1))
        elif pn_matches:
            prezzo_netto = prezzo_listino

        # IVA %: "22%" alla fine
        iva_match = re.search(r'(\d+)%\s*$', block, re.M)
        if iva_match:
            aliquota_iva = int(iva_match.group(1))

        # AIC = MINSAN sotto la descrizione (9 cifre). Il codice colonna e' materiale SAP.
        # Se manca MINSAN e' espositore puro senza AIC (caso PHYSIOMER EXPO BANCO).
        minsan_match = re.search(r'MINSAN\s*:\s*(\d+)', block)

        if minsan_match:
            minsan = minsan_match.group(1)
            aic_norm, aic_orig, is_esp_desc, _ = normalize_aic(minsan, descrizione)
            codice_aic = aic_norm
            codice_originale = aic_orig
            is_expo = is_esp_desc
            is_no_aic = False
        else:
            codice_aic = ''
            codice_originale = codice
            is_expo = True
            is_no_aic = True

        n_riga += 1
        data['righe'].append({
            'n_riga': n_riga,
            'codice_aic': codice_aic,
            'codice_originale': codice_originale,
            'descrizione': descrizione,
            'data_consegna': data_consegna,
            'q_venduta': q_venduta,
            'q_omaggio': 0,
            'sconto1': sconto1,
            'prezzo_netto': prezzo_netto,
            'prezzo_pubblico': prezzo_listino,
            'aliquota_iva': aliquota_iva,
            'is_espositore': is_expo,
            'is_child': False,
            'is_no_aic': is_no_aic,
        })

        # =====================================================================
        # 6. COMPONENTI (child dell'espositore)
        # Formato: "951553003  PHYSIOMER GETTO NORMALE 135ML GR/IT  2 ST"
        # O senza AIC: "PHYSIOMER COUNTER DISPLAY 8 PZ VUOTO  1 ST"
        # Elaborati per qualsiasi espositore (con o senza MINSAN proprio).
        # Un prodotto LE/bundle che NON e' espositore (descrizione senza
        # ESP/EXP/BANCO/EXPO) vede la sezione "Componenti" ignorata.
        # =====================================================================
        if is_expo and ('Componenti' in block or 'componenti' in block.lower()):
            comp_section = block[block.lower().find('componenti'):]

            # Righe componente con AIC (9 cifre)
            comp_matches = re.finditer(
                r'(\d{9})\s+(.+?)\s+(\d+)\s+ST',
                comp_section
            )
            for cm in comp_matches:
                comp_aic = cm.group(1)
                comp_desc = cm.group(2).strip()[:40]
                comp_qty = int(cm.group(3))

                aic_norm, aic_orig, _, _ = normalize_aic(comp_aic, comp_desc)

                n_riga += 1
                data['righe'].append({
                    'n_riga': n_riga,
                    'codice_aic': aic_norm,
                    'codice_originale': aic_orig,
                    'descrizione': comp_desc,
                    'data_consegna': data_consegna,
                    'q_venduta': comp_qty,
                    'q_omaggio': 0,
                    'sconto1': 0,
                    'prezzo_netto': 0,
                    'prezzo_pubblico': 0,
                    'is_espositore': False,
                    'is_child': True,
                    'id_parent_n_riga': linea_num // 10,  # Riferimento al parent
                })

            # Righe componente SENZA AIC (es. display vuoto)
            # Mixed-case supportato: "BIO OIL Expo Banco Misto Tp Vuoto IT"
            comp_noaic = re.finditer(
                r'^\s{10,}([A-Za-z][A-Za-z0-9\s/+\-\.]+?)\s+(\d+)\s+ST\s*$',
                comp_section, re.M
            )
            for cn in comp_noaic:
                comp_desc = cn.group(1).strip()[:40]
                comp_qty = int(cn.group(2))
                # Evita di ri-matchare righe già catturate con AIC
                if re.search(r'^\d{9}\s', cn.group(0).strip()):
                    continue

                n_riga += 1
                data['righe'].append({
                    'n_riga': n_riga,
                    'codice_aic': '',
                    'codice_originale': '',
                    'descrizione': comp_desc,
                    'data_consegna': data_consegna,
                    'q_venduta': comp_qty,
                    'q_omaggio': 0,
                    'sconto1': 0,
                    'prezzo_netto': 0,
                    'prezzo_pubblico': 0,
                    'is_espositore': False,
                    'is_child': True,
                    'is_no_aic': True,
                })

    # =========================================================================
    # 7. DATA CONSEGNA TESTATA
    # =========================================================================
    if data['righe'] and data['righe'][0].get('data_consegna'):
        data['data_consegna'] = data['righe'][0]['data_consegna']

    return [data] if data.get('righe') or data.get('numero_ordine') else []


def _parse_price_eu(price_str: str) -> float:
    """Converte prezzo formato europeo: '75,32' → 75.32, '1.234,56' → 1234.56"""
    if not price_str:
        return 0.0
    price_str = price_str.strip()
    # Rimuovi punti migliaia, virgola → punto decimale
    price_str = price_str.replace('.', '').replace(',', '.')
    try:
        return float(price_str)
    except ValueError:
        return 0.0
