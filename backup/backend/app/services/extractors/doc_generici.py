"""
EXTRACTOR_TO - Estrattore DOC_GENERICI v1.0
============================================
Transfer Order DOC Generici (ordini via grossisti)

Particolarità:
- Doppio indirizzo (fiscale + consegna)
- NO prezzi/sconti nel documento
- Classe farmaco (A-A, C-C, I-I)
- Supporto multipagina
- Codici AIC anche non standard (integratori 9xx)
- Lookup su indirizzo CONSEGNA (non fiscale)

Regole: REGOLE_DOC_GENERICI.md
"""

import re
from typing import Dict, List, Optional

from ...utils import parse_date, parse_int


# =============================================================================
# FUNZIONE PRINCIPALE
# =============================================================================

def extract_doc_generici(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore per Transfer Order DOC GENERICI.

    Applica regole:
    - DOCGEN-H01..H11 (header)
    - DOCGEN-T01..T07 (tabella prodotti)
    - DOCGEN-A01..A10 (anomalie)

    Args:
        text: Testo completo PDF
        lines: Righe separate del PDF
        pdf_path: Percorso file (non usato per questo vendor)

    Returns:
        Lista con un dict contenente dati ordine
    """
    data = {
        'vendor': 'DOC_GENERICI',
        'righe': [],
        'anomalie_estrazione': [],
    }

    # =========================================================================
    # ESTRAZIONE HEADER (DOCGEN-H01..H11)
    # =========================================================================

    # DOCGEN-H01: Numero Ordine (10 cifre)
    m = re.search(r'Num\.\s*(\d{10})\s+DEL', text, re.I)
    if m:
        data['numero_ordine'] = m.group(1)

    # DOCGEN-H02: Data Ordine (DD/MM/YYYY)
    m = re.search(r'DEL\s+(\d{2}/\d{2}/\d{4})', text, re.I)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    # DOCGEN-H03: Grossista/Distributore
    m = re.search(r'Grossista\s+([^\n]+)', text, re.I)
    if m:
        data['grossista'] = m.group(1).strip()[:80]

    # DOCGEN-H04: Codice + Nome Agente
    m = re.search(r'Agente\s+(\d{5})\s+([^\n]+)', text, re.I)
    if m:
        data['codice_agente'] = m.group(1)
        data['nome_agente'] = m.group(2).strip()[:50]

    # DOCGEN-H05: Ragione Sociale Farmacia
    m = re.search(r'Farmacia\s+(.+?)\s+P\.?IVA', text, re.I)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:80]

    # DOCGEN-H06: P.IVA (11 cifre)
    m = re.search(r'P\.?IVA\s+(\d{11})', text, re.I)
    if m:
        data['partita_iva'] = m.group(1)

    # DOCGEN-H07: Indirizzo Fiscale
    m = re.search(r'Ind\.?\s*Fiscale\s+Via\s+([^\n]+)', text, re.I)
    if m:
        data['indirizzo_fiscale'] = m.group(1).strip()[:60]

    # DOCGEN-H08: CAP, Città, Provincia (Fiscale) - PRIMA occorrenza
    cap_matches = list(re.finditer(
        r'CAP\s+(\d{5})\s+Citt[àa]\s+([A-Z][A-Z\s\']+?)\s+Prov\.\s*([A-Z]{2})',
        text, re.I
    ))
    if len(cap_matches) >= 1:
        m = cap_matches[0]
        data['cap_fiscale'] = m.group(1)
        data['citta_fiscale'] = m.group(2).strip()
        data['provincia_fiscale'] = m.group(3).upper()

    # DOCGEN-H09: Indirizzo Consegna Merce (CRITICO per lookup)
    m = re.search(r'Ind\.?\s*Consegna\s+Merce\s+Via\s+([^\n]+)', text, re.I)
    if m:
        data['indirizzo'] = m.group(1).strip()[:60]  # Mappato come indirizzo principale

    # DOCGEN-H10: CAP, Città, Provincia (Consegna) - SECONDA occorrenza
    # Questi sono i campi che vanno nel tracciato TO_T
    if len(cap_matches) >= 2:
        m = cap_matches[1]
        data['cap'] = m.group(1)
        data['citta'] = m.group(2).strip()
        data['provincia'] = m.group(3).upper()
    elif len(cap_matches) == 1:
        # Se solo una occorrenza, usa quella per entrambi
        m = cap_matches[0]
        data['cap'] = m.group(1)
        data['citta'] = m.group(2).strip()
        data['provincia'] = m.group(3).upper()

    # DOCGEN-H11: Telefono e Fax
    m = re.search(r'Telefono\s+([\d/]+)', text, re.I)
    if m:
        data['telefono'] = m.group(1).strip()

    m = re.search(r'Fax\s+([\d/]+)', text, re.I)
    if m:
        data['fax'] = m.group(1).strip()

    # =========================================================================
    # ESTRAZIONE RIGHE PRODOTTO (DOCGEN-T01..T07)
    # =========================================================================

    righe = _extract_product_lines(text, lines)
    data['righe'] = righe

    # =========================================================================
    # ESTRAZIONE TOTALE FOOTER (per validazione)
    # =========================================================================

    m = re.search(r'Totale:\s*(\d+)', text, re.I)
    if m:
        data['totale_pezzi_footer'] = parse_int(m.group(1))

    # =========================================================================
    # VALIDAZIONE E ANOMALIE
    # =========================================================================

    anomalie = _validate_and_detect_anomalies(data)
    data['anomalie_estrazione'] = anomalie

    return [data]


# =============================================================================
# ESTRAZIONE RIGHE PRODOTTO
# =============================================================================

def _extract_product_lines(text: str, lines: List[str]) -> List[Dict]:
    """
    Estrae righe prodotto dalla tabella (DOCGEN-T01..T07).

    Pattern riga:
    [9 cifre AIC] [descrizione] [qty] [X-X classe] [ACCORDO TO]

    Args:
        text: Testo completo
        lines: Righe separate

    Returns:
        Lista di dict con dati riga
    """
    righe = []
    n_riga = 0
    in_tabella = False

    # Pattern per identificare inizio tabella
    pattern_header = re.compile(r'COD\.\s*A\.I\.C\.\s+Prodotto', re.I)

    # Pattern per riga prodotto completa
    # AIC (9 cifre) + descrizione + qty + classe (X-X) + ACCORDO TO
    pattern_riga = re.compile(
        r'^(\d{9})\s+'           # Codice AIC (9 cifre)
        r'(.+?)\s+'              # Descrizione (greedy ma non troppo)
        r'(\d{1,4})\s+'          # Quantità (1-4 cifre)
        r'([A-Z]-[A-Z])\s+'      # Classe farmaco (A-A, C-C, I-I)
        r'ACCORDO\s+TO\s*$',     # Condizione (costante)
        re.I
    )

    # Pattern alternativo più permissivo
    pattern_riga_alt = re.compile(
        r'^(\d{9})\s+'           # Codice AIC
        r'(.+?)\s+'              # Descrizione
        r'(\d{1,4})\s+'          # Quantità
        r'([A-Z]-[A-Z])',        # Classe (senza ACCORDO TO obbligatorio)
        re.I
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Rileva inizio tabella
        if pattern_header.search(line):
            in_tabella = True
            continue

        # Stop se footer
        if 'Totale:' in line or re.match(r'^Pagina\s+\d+\s+di\s+\d+', line, re.I):
            continue

        # Se in tabella, prova a parsare riga prodotto
        if in_tabella:
            # Prova pattern completo
            m = pattern_riga.match(line)
            if not m:
                # Prova pattern alternativo
                m = pattern_riga_alt.match(line)

            if m:
                n_riga += 1
                codice_aic = m.group(1)
                descrizione = m.group(2).strip()
                quantita = parse_int(m.group(3))
                classe_farmaco = m.group(4).upper()

                # Validazione codice AIC (DOCGEN-A01: accetta anche 9xx)
                if len(codice_aic) == 9 and codice_aic.isdigit():
                    righe.append({
                        'n_riga': n_riga,
                        'codice_aic': codice_aic,
                        'codice_originale': codice_aic,
                        'descrizione': descrizione[:60],
                        'q_venduta': quantita,
                        'q_sconto_merce': 0,  # DOC_GENERICI non ha sconto merce
                        'q_omaggio': 0,       # DOC_GENERICI non ha omaggio
                        'classe_farmaco': classe_farmaco,
                        'condizione': 'ACCORDO TO',
                        # DOC_GENERICI NON ha prezzi (DOCGEN-A03)
                        'prezzo_netto': None,
                        'prezzo_pubblico': None,
                        'sconto1': None,
                        'sconto2': None,
                        'sconto3': None,
                        'sconto4': None,
                        'valore_netto': None,
                        'aliquota_iva': 10,  # Default IVA
                    })

    return righe


# =============================================================================
# VALIDAZIONE E ANOMALIE
# =============================================================================

def _validate_and_detect_anomalies(data: Dict) -> List[Dict]:
    """
    Valida dati estratti e rileva anomalie (DOCGEN-A01..A10).

    Args:
        data: Dict con dati estratti

    Returns:
        Lista di anomalie rilevate
    """
    anomalie = []
    righe = data.get('righe', [])

    # DOCGEN-A04: Totale Pezzi Non Coerente
    totale_footer = data.get('totale_pezzi_footer')
    if totale_footer is not None and righe:
        totale_calcolato = sum(r.get('q_venduta', 0) for r in righe)
        if totale_calcolato != totale_footer:
            differenza = abs(totale_calcolato - totale_footer)
            differenza_pct = (differenza / totale_footer * 100) if totale_footer > 0 else 0

            # Determina livello
            if differenza_pct > 5:
                livello = 'ERRORE'
                richiede_sup = True
            else:
                livello = 'ATTENZIONE'
                richiede_sup = False

            anomalie.append({
                'tipo_anomalia': 'TOTALE_NON_COERENTE',
                'codice_anomalia': 'DOCGEN-A04',
                'livello': livello,
                'descrizione': f'Totale pezzi non coerente: footer={totale_footer}, calcolato={totale_calcolato}',
                'valore_anomalo': f'Differenza: {differenza} pezzi ({differenza_pct:.1f}%)',
                'richiede_supervisione': richiede_sup,
            })

    # DOCGEN-A08: Quantità Anomala (qty=0 o qty>200)
    for riga in righe:
        qty = riga.get('q_venduta', 0)
        if qty == 0:
            anomalie.append({
                'tipo_anomalia': 'QUANTITA_ANOMALA',
                'codice_anomalia': 'DOCGEN-A08',
                'livello': 'ERRORE',
                'descrizione': f'Quantità zero per AIC {riga.get("codice_aic")}',
                'valore_anomalo': f'qty=0',
                'richiede_supervisione': True,
            })
        elif qty > 200:
            anomalie.append({
                'tipo_anomalia': 'QUANTITA_ANOMALA',
                'codice_anomalia': 'DOCGEN-A08',
                'livello': 'ATTENZIONE',
                'descrizione': f'Quantità elevata per AIC {riga.get("codice_aic")}',
                'valore_anomalo': f'qty={qty}',
                'richiede_supervisione': False,
            })

    # DOCGEN-A10: Footer Mancante (se ordine multipagina)
    # Nota: verificato a livello di processo, non qui

    return anomalie


# =============================================================================
# WRAPPER
# =============================================================================

def extract(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """Wrapper per compatibilità."""
    return extract_doc_generici(text, lines, pdf_path)
