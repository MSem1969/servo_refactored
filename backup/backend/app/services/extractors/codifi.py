"""
EXTRACTOR_TO - Estrattore CODIFI
=================================
Convertito da TO_EXTRACTOR_v6_0_DB_def.ipynb - Cella 9
Regole: REGOLE_CODIFI.md
"""

import re
from typing import Dict, List

from ...utils import provincia_nome_to_sigla, format_piva


def extract_codifi(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF CODIFI v3.0.
    
    MULTI-CLIENTE: Ogni cliente nel PDF genera un ordine separato!
    
    Parsing indirizzo:
    - Pattern: INDIRIZZO NUMERO_CIVICO CITTA Provincia
    - La parola DOPO il numero civico è sempre la CITTÀ
    """
    orders = []
    current_order = None

    for i, line in enumerate(lines):
        # CODIFI-H01: Nuovo ordine (trigger: N°Ordine + Data Delivery)
        if (('N°Ordine' in line or 'N.Ordine' in line or re.search(r'N.{0,3}Ordine', line)) 
            and 'Data Delivery' in line):
            if current_order and current_order.get('numero_ordine'):
                orders.append(current_order)
            current_order = {
                'vendor': 'CODIFI',
                'numero_ordine': '', 'data_ordine': '', 'data_consegna': '',
                'codice_ministeriale': '', 'partita_iva': '', 'ragione_sociale': '',
                'indirizzo': '', 'cap': '', 'citta': '', 'provincia': '',
                'righe': []
            }
            continue

        # CODIFI-H02/H03: Numero ordine e data consegna
        if current_order and line.strip().startswith('O-'):
            parts = line.split()
            if parts:
                current_order['numero_ordine'] = parts[0]
                for p in parts[1:]:
                    if '/' in p and len(p) == 10:
                        current_order['data_consegna'] = p
                        break
            continue

        # CODIFI-H04/H05: P.IVA e Ragione Sociale
        if ('Cod. Cliente' in line or 'Cod.Cliente' in line) and 'P.IVA' in line and ('Rag. Sociale' in line or 'Rag.Sociale' in line):
            if i+1 < len(lines) and current_order:
                next_line = lines[i+1].strip()
                piva_match = re.search(r'\b(\d{11})\b', next_line)
                if piva_match:
                    current_order['partita_iva'] = format_piva(piva_match.group(1))
                    rs = next_line[piva_match.end():].strip()
                    
                    # Gestione ragione sociale multiriga
                    for j in range(1, 4):
                        if i+1+j < len(lines):
                            continuation = lines[i+1+j].strip()
                            if (continuation and 
                                'Indirizzo' not in continuation and
                                'AIC' not in continuation and
                                len(continuation) < 40 and
                                not re.match(r'^0\d{8}', continuation)):
                                if continuation.startswith('-'):
                                    continuation = continuation[1:].strip()
                                rs = rs + ' ' + continuation
                            else:
                                break
                    
                    current_order['ragione_sociale'] = rs[:100].strip()
            continue

        # CODIFI-H06/H07/H08/H09: Indirizzo, Comune, Provincia, CAP
        # v6.2: Aggiunta estrazione CAP per indirizzo concatenato
        if 'Indirizzo Cliente' in line and 'Comune' in line and 'Provincia' in line:
            if i+1 < len(lines) and current_order:
                addr_line = lines[i+1].strip()

                # Gestione continuazione indirizzo
                if i+2 < len(lines):
                    continuation = lines[i+2].strip()
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
                cap = ''

                if len(words) >= 3:
                    # Provincia = ultima parola formato Xxxxx
                    last = words[-1]
                    if len(last) > 2 and last[0].isupper() and not last.isupper():
                        provincia = last
                        remaining = words[:-1]
                    else:
                        remaining = words

                    # v6.2: Cerca CAP (5 cifre) nella riga
                    for idx, word in enumerate(remaining):
                        if re.match(r'^\d{5}$', word):
                            cap = word
                            # Rimuovi CAP da remaining
                            remaining = remaining[:idx] + remaining[idx+1:]
                            break

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

                current_order['indirizzo'] = indirizzo[:60].strip()
                current_order['citta'] = comune[:30].strip()
                current_order['provincia'] = provincia_nome_to_sigla(provincia) if provincia else ''
                current_order['cap'] = cap  # v6.2
            continue

        # CODIFI-T01/T02/T03/T04/T05: Righe prodotto
        # Formato: AIC (9 cifre) | Cod.Prodotto (6 alfanum, IGNORARE) | Descrizione (inizia con lettera) | Quantità
        if current_order and re.match(r'^0\d{8}', line.strip()):
            parts = line.split()
            if len(parts) >= 3:
                # Colonna 1: Codice AIC (9 cifre)
                aic = parts[0]

                # Colonna 2: Codice prodotto interno - IGNORARE completamente

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
                    if idx < 2:  # Salta AIC e codice prodotto
                        continue
                    if idx == len(parts) - 1 and part.isdigit():
                        continue  # Salta quantità finale
                    if desc_parts or (part and part[0].isalpha()):
                        desc_parts.append(part)
                desc = ' '.join(desc_parts)[:60]

                current_order['righe'].append({
                    'n_riga': len(current_order['righe']) + 1,
                    'codice_aic': aic,
                    'codice_originale': '',  # Non usiamo codice prodotto interno
                    'descrizione': desc,
                    'q_venduta': qty,
                    'is_espositore': False,  # CODIFI non ha espositori
                    'is_child': False,
                })

    # Non dimenticare l'ultimo ordine
    if current_order and current_order.get('numero_ordine'):
        orders.append(current_order)

    return orders
