"""
EXTRACTOR_TO - Estrattore ZENTIVA
==================================
Estrattore per ordini ZENTIVA (Transfer Order)

Struttura documento:
- Logo "ZENTIVA" + Ragione sociale farmacia (titolo)
- "Info Ordine":
  - Partita IVA Cliente: 11 cifre
  - Cliente: <ragione + indirizzo + Codice SAP + CAP>
  - NomeAccount: ragione sociale
  - SAP Nr. Ordine: VUOTO nei PDF visti -> numero ordine estratto da nome file
  - Codice SAP, Tipo Cliente, Tipo Ordine, Data Ordine (DD-MM-YYYY)
  - Contatti, email @zentiva.com, telefono
- "Riepilogo Consegna":
  - Data consegna (DD-MM-YYYY)
  - Indirizzo di spedizione: ragione + indirizzo + CAP citta provincia
  - Distributore (informativo, non usato)
- "Dettagli Ordine" (tabella):
  Categoria/prodotto | Fascia | Codice Prodotto (9 cifre AIC) |
  Prezzo Unitario | Prezzo Netto | Quantita | Omaggio auto | Omaggio agente |
  Valore Lordo | Sconto auto% | Sconto agente% | Valore Netto

Note:
- Numero ordine: dal nome file ("n. O-NNNNNN" -> "O-NNNNNN"). SAP Nr. Ordine
  e' tipicamente vuoto nel PDF (comunicazione vendor).
- Prezzi reali presenti, anche se Tipo Ordine = Transfer.
- Omaggio auto/agente e Sconto agente possono essere vuoti o popolati: il
  parser tollera entrambi i casi.
- Nessuna gestione espositori.

v1.0: Implementazione iniziale
"""

import os
import re
from typing import Dict, List

from ....utils import parse_date, normalize_aic


_INDIRIZZO_PREFIX = (
    'VIA', 'V\\.LE', 'VIALE', 'CORSO', 'C\\.SO', 'PIAZZA', 'P\\.ZZA',
    'PIAZZALE', 'P\\.LE', 'LARGO', 'VICOLO', 'CONTRADA', 'STRADA',
    'LOC\\.?', 'LOCALITA', 'FRAZIONE', 'FRAZ\\.?', 'C/O',
)
_INDIRIZZO_RE = re.compile(
    r'\b(?:' + '|'.join(_INDIRIZZO_PREFIX) + r')\s+[^\n]+',
    re.IGNORECASE,
)


def extract_zentiva(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF ZENTIVA.

    Returns:
        Lista con dizionario ordine estratto
    """
    data = {'vendor': 'ZENTIVA', 'righe': []}

    # =========================================================================
    # 1. NUMERO ORDINE - dal nome file (SAP Nr. Ordine vuoto nel PDF)
    # Pattern: "Transfer Order Zentiva n. O-798447.pdf"
    # =========================================================================
    if pdf_path:
        basename = os.path.basename(pdf_path)
        m = re.search(r'O-(\d+)', basename)
        if m:
            # Mantiene prefisso "O-" come da comunicazione vendor
            data['numero_ordine'] = f"O-{m.group(1)}"

    # Fallback: prova ad estrarre da SAP Nr. Ordine se mai popolato
    if not data.get('numero_ordine'):
        m = re.search(r'SAP\s+Nr\.?\s*Ordine\s*:?\s*([A-Z0-9\-]+)', text, re.I)
        if m and m.group(1).strip():
            data['numero_ordine'] = m.group(1).strip()

    # =========================================================================
    # 2. PARTITA IVA CLIENTE
    # pdfplumber estrae le colonne mescolate: la P.IVA (11 cifre) appare
    # vicino a "Partita IVA" ma puo' non essere sulla stessa riga.
    # =========================================================================
    # Cerca il primo gruppo di 11 cifre dopo "Partita IVA"
    m = re.search(r'Partita\s+IVA[\s\S]{0,200}?\b(\d{11})\b', text, re.I)
    if m:
        data['partita_iva'] = m.group(1)

    # =========================================================================
    # 3. RAGIONE SOCIALE - da NomeAccount (piu' affidabile del titolo)
    # =========================================================================
    m = re.search(r'Nome\s*Account\s*:?\s*(.+?)(?:\n|SAP\s+Nr)', text, re.I)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:50]
    else:
        # Fallback: titolo prima riga (es. "FARMACIA SANT'ANNA")
        for line in lines[:5]:
            line = line.strip()
            if line and re.match(r"^[A-Z][A-Z\s\.'`,&\-]+$", line) and len(line) > 4:
                data['ragione_sociale'] = line[:50]
                break

    # =========================================================================
    # 4. DATA ORDINE (DD-MM-YYYY)
    # =========================================================================
    m = re.search(r'Data\s+Ordine\s*:?\s*(\d{2}-\d{2}-\d{4})', text, re.I)
    if m:
        data['data_ordine'] = parse_date(m.group(1))
    else:
        # Fallback: in alcuni PDF le label sono scrambled da pdfplumber.
        # Prima data DD-MM-YYYY del documento.
        m = re.search(r'(\d{2}-\d{2}-\d{4})', text)
        if m:
            data['data_ordine'] = parse_date(m.group(1))

    # =========================================================================
    # 5. CONTATTI -> nome agente (es. "GENNARO DI MARZO")
    # =========================================================================
    m = re.search(r'Contatti\s*:?\s*(.+?)(?:\n|Indirizzo\s+email)', text, re.I)
    if m:
        nome = m.group(1).strip()
        if nome and not nome.lower().startswith('indirizzo'):
            data['nome_agente'] = nome[:50]

    # =========================================================================
    # 6. INDIRIZZO DI SPEDIZIONE
    # Regola: si estrae SOLO dalla riga che inizia con la data di consegna
    # in formato GG-MM-AAAA seguito da spazio.
    # Tutto cio' che segue la data sulla stessa riga e' "ragione + indirizzo
    # + CAP + citta + provincia + distributore".
    # =========================================================================
    ship_match = re.search(
        r'^(\d{2}-\d{2}-\d{4})\s+(.+?)$',
        text, re.M
    )
    if ship_match:
        data['data_consegna'] = parse_date(ship_match.group(1))
        ship_line = ship_match.group(2)

        # CAP + Citta + Provincia (in fondo alla riga, prima del distributore)
        # Pattern: "DDDDD CITTA PR"
        cap_match = re.search(
            r'\b(\d{5})\s+([A-Za-z][A-Za-z\.\'\s\-]+?)\s+([A-Z]{2})\b',
            ship_line
        )
        if cap_match:
            data['cap'] = cap_match.group(1)
            data['citta'] = cap_match.group(2).strip().upper()[:50]
            data['provincia'] = cap_match.group(3)

        # Indirizzo: cerca prefisso topografico, tronca al CAP
        addr_match = _INDIRIZZO_RE.search(ship_line)
        if addr_match:
            indirizzo = addr_match.group(0)
            cap_in_addr = re.search(r'\s+\d{5}\b', indirizzo)
            if cap_in_addr:
                indirizzo = indirizzo[:cap_in_addr.start()]
            data['indirizzo'] = indirizzo.strip()[:50]

    # =========================================================================
    # 7. RIGHE PRODOTTO
    # Layout pdfplumber (a colonne mescolate):
    #   IT_10_<descrizione_riga1>
    #   Rx <AIC9><prezzoU> € <prezzoN>€ <q> [<om>] <val_lordo>€ <sc> [<sca>] <val_netto>€
    #   <descrizione_riga2>             <- continuazione
    # NOTA: tra AIC e prezzo NON c'e' spazio (es. "Rx 0417853181.83").
    # =========================================================================
    n_riga = 0
    n = len(lines)
    # Pattern riga dati:
    #   group 1 = eventuale prefisso descrizione presente sulla stessa riga
    #             (es. MONCUCCO: "SIMVASTATINA 10/10MG 30 ")
    #   group 2 = AIC (esattamente 9 cifre, primo gruppo dopo "Rx")
    #   group 3 = resto della riga con prezzi/quantita/sconti
    # Tra AIC e prezzo possono esserci 0 o piu' spazi (pdfplumber a volte
    # li attacca: "Rx 0417853181.83 €"; a volte li separa: "Rx 044103024 4.70 €").
    data_re = re.compile(r'^(.*?)\bRx\s+(\d{9})\s*(.*€)\s*$')

    for i in range(n):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if 'Totale' in stripped and ('Lordo' in stripped or 'Netto' in stripped):
            break

        m = data_re.search(stripped)
        if not m:
            continue

        desc_inline = m.group(1).strip()
        aic_raw = m.group(2)
        nums_part = m.group(3)

        # Descrizione: riga PRECEDENTE (tipicamente "IT_*") + prefisso inline
        # + riga SUCCESSIVA (continuazione)
        desc_parts: List[str] = []
        if i > 0:
            prev = lines[i - 1].strip()
            if prev and not data_re.search(prev) and not re.match(
                r'(Categoria|Fascia|Codice|Prezzo|Quantit|Omaggio|Valore|Sconto|Dettaglio)', prev, re.I
            ):
                desc_parts.append(prev)
        if desc_inline:
            desc_parts.append(desc_inline)
        if i + 1 < n:
            nxt = lines[i + 1].strip()
            if nxt and not data_re.search(nxt) and not nxt.startswith('IT_') and 'Totale' not in nxt:
                desc_parts.append(nxt)
        descrizione = ' '.join(desc_parts).strip()
        # Rimuove prefisso "IT_NN_" (codifica vendor non utile per la descrizione)
        descrizione = re.sub(r'^IT_\d+_\s*', '', descrizione)

        # Parsing numerico:
        # split per "€" -> 4 segmenti monetari + resto
        # parts: [prezzoU, prezzoN, "<q ...> val_lordo", "<sconto_auto ...> val_netto", ...]
        parts = nums_part.split('€')
        # Rimuove eventuale stringa vuota finale
        parts = [p.strip() for p in parts if p.strip()]

        prezzo_unit = 0.0
        prezzo_netto = 0.0
        q_venduta = 0
        q_omaggio = 0
        sconto1 = 0.0
        sconto2 = 0.0
        valore_lordo = 0.0
        valore_netto = 0.0

        if len(parts) >= 1:
            prezzo_unit = _parse_price_eu(parts[0])
        if len(parts) >= 2:
            prezzo_netto = _parse_price_eu(parts[1])

        if len(parts) >= 3:
            # parts[2]: "q [omaggio_auto] [omaggio_agente] val_lordo"
            tokens = re.findall(r'[\d.,]+', parts[2])
            if tokens:
                # Primo = quantita (intero)
                try:
                    q_venduta = int(float(tokens[0].replace(',', '.')))
                except ValueError:
                    q_venduta = 0
                # Ultimo = valore lordo
                if len(tokens) >= 2:
                    valore_lordo = _parse_price_eu(tokens[-1])
                # Token intermedi = omaggi (somma)
                for t in tokens[1:-1] if len(tokens) > 2 else []:
                    try:
                        q_omaggio += int(float(t.replace(',', '.')))
                    except ValueError:
                        pass

        if len(parts) >= 4:
            # parts[3]: "sconto_auto [sconto_agente] val_netto"
            tokens = re.findall(r'[\d.,]+', parts[3])
            if tokens:
                sconto1 = _parse_price_eu(tokens[0])
                if len(tokens) >= 2:
                    valore_netto = _parse_price_eu(tokens[-1])
                if len(tokens) >= 3:
                    sconto2 = _parse_price_eu(tokens[1])

        # Normalizza AIC
        aic_norm, aic_orig, _is_esp_desc, _ = normalize_aic(aic_raw, descrizione)

        n_riga += 1
        data['righe'].append({
            'n_riga': n_riga,
            'codice_aic': aic_norm or aic_raw,
            'codice_originale': aic_orig or aic_raw,
            'descrizione': descrizione[:100],
            'data_consegna': data.get('data_consegna', ''),
            'q_venduta': q_venduta,
            'q_omaggio': q_omaggio,
            'q_sconto_merce': 0,
            'sconto1': sconto1,
            'sconto2': sconto2,
            'prezzo_netto': prezzo_netto,
            'prezzo_pubblico': prezzo_unit,
            'aliquota_iva': 10,  # Rx farmaci = 10%
            'is_espositore': False,
            'is_child': False,
            'is_no_aic': False,
        })

    return [data] if data.get('righe') or data.get('numero_ordine') else []


def _parse_price_eu(price_str: str) -> float:
    """Converte prezzo formato europeo: '1.83' -> 1.83, '1.234,56' -> 1234.56"""
    if not price_str:
        return 0.0
    s = price_str.strip().replace('€', '').strip()
    if not s:
        return 0.0
    # Se contiene sia '.' che ',', il '.' e' separatore migliaia
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        # Solo virgola: separatore decimale europeo
        s = s.replace(',', '.')
    # Se solo '.', e' gia' decimale anglosassone (Zentiva usa cosi')
    try:
        return float(s)
    except ValueError:
        return 0.0
