"""
EXTRACTOR_TO - Estrattore ANGELINI v3.2
========================================
Refactored per usare utilities condivise
"""

import re
from typing import Dict, List, Optional

from ...utils import parse_date, parse_decimal, parse_int, normalize_aic_simple
from ..espositore import elabora_righe_ordine


# =============================================================================
# FUNZIONE PRINCIPALE (copiata esatta dal notebook)
# =============================================================================

def extract_angelini(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore completo per PDF ANGELINI/ACRAF.
    COPIATO ESATTO dal notebook TO_EXTRACTOR_ANGELINI_v3_REAL.ipynb
    """
    data = {
        'vendor': 'ANGELINI',
        'righe_raw': [],
        'righe': [],
        'anomalie_espositore': [],
    }
    
    # =========================================
    # HEADER
    # =========================================
    
    # Numero ordine e data: Num.2008372053 del 31.10.2025
    m = re.search(r'Num[.:]?\s*(\d{10})\s+del\s+(\d{2}[./]\d{2}[./]\d{4})', text)
    if m:
        data['numero_ordine'] = m.group(1)
        data['data_ordine'] = parse_date(m.group(2))
    
    # Data consegna
    m = re.search(r'Data\s+consegna\s+(\d{2}[./]\d{2}[./]\d{4})', text)
    if m:
        data['data_consegna'] = parse_date(m.group(1))
    
    # Agente
    m = re.search(r'Agente\s+([A-Z][A-Za-z\s]+?)\s+Tipo', text)
    if m:
        data['nome_agente'] = m.group(1).strip()
    
    # Cooperativa
    m = re.search(r'Cooperativa:\s*(\d+)\s+([^\n]+)', text)
    if m:
        data['cooperativa'] = f"{m.group(1)} {m.group(2).strip()}"
    
    # P.IVA
    m = re.search(r'P\.?I\.?:?\s*(\d{11})', text)
    if m:
        data['partita_iva'] = m.group(1)
    
    # ID MIN / Codice Ministeriale
    m = re.search(r'ID\s*MIN:?\s*(\d+)', text)
    if m:
        data['codice_ministeriale'] = m.group(1).zfill(9)
    
    # CLDM (codice alternativo)
    m = re.search(r'CLDM:?\s*(\d+)', text)
    if m:
        data['cldm'] = m.group(1)
    
    # Ragione sociale (dopo "Indirizzo spedizione")
    m = re.search(r'Indirizzo\s+spedizione\s*\n?([^\n]+)', text, re.I)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:80]
    
    # Indirizzo
    m = re.search(r'((?:VIA|CORSO|PIAZZA|VIALE|V\.LE|P\.ZZA)[^\n]+)', text, re.I)
    if m:
        data['indirizzo'] = m.group(1).strip()[:60]
    
    # CAP, Città, Provincia: I-95026 ACITREZZA CT
    m = re.search(r'I-?(\d{5})\s+([A-Z][A-Za-z\s\']+?)\s+([A-Z]{2})(?:\s|$)', text)
    if m:
        data['cap'] = m.group(1)
        data['citta'] = m.group(2).strip()
        data['provincia'] = m.group(3)
    
    # =========================================
    # RIGHE PRODOTTO - Pattern dal notebook
    # =========================================
    
    righe_raw = []
    
    # Pattern per riga con valori completi (vendita normale)
    pattern_vendita = re.compile(
        r'^(\d{6,9})\s+'                    # Codice AIC (6-9 cifre)
        r'(.+?)\s+'                          # Descrizione
        r'(\d{6}|[A-Z0-9]{10,})\s+'          # Codice Materiale
        r'(\d+)\s+'                          # Quantità
        r'PZ\s+'                             # UM
        r'([\d,]+)\s+'                       # Prezzo listino
        r'([\d,]+)\s+'                       # % Sconto
        r'([\d,]+)\s+'                       # Prezzo netto
        r'(\d+)\s+'                          # % IVA
        r'([\d.,]+)'                         # Valore netto
    )
    
    # Pattern per SC.MERCE
    pattern_scmerce = re.compile(
        r'^(\d{6,9})\s+'                    # Codice AIC
        r'(.+?)\s+'                          # Descrizione
        r'(\d{6}|[A-Z0-9]{10,})\s+'          # Codice Materiale
        r'SC\.?MERCE\s+'                     # Tipo posizione
        r'(\d+)\s+'                          # Quantità
        r'PZ',                               # UM
        re.I
    )
    
    # Pattern per P.O.P.
    pattern_pop = re.compile(
        r'^(\d{6,9})\s+'                    # Codice AIC
        r'(.+?)\s+'                          # Descrizione
        r'(\d{6}|[A-Z0-9]{10,})\s+'          # Codice Materiale
        r'P\.?O\.?P\.?\s+'                   # Tipo posizione
        r'(\d+)\s+'                          # Quantità
        r'PZ',                               # UM
        re.I
    )
    
    # Pattern per espositore parent (6 cifre, senza prezzo)
    pattern_parent = re.compile(
        r'^(\d{6})\s+'                       # Codice 6 cifre
        r'(.+?\d+\s*PZ)\s+'                  # Descrizione con XXPZ
        r'(\d{6})\s+'                        # Codice Materiale
        r'(\d+)\s+'                          # Quantità
        r'PZ',                               # UM
        re.I
    )

    # Pattern per espositore parent con BANCO (senza XXPZ nella descrizione)
    # Il numero pezzi può essere in una riga orfana successiva concatenata
    pattern_parent_banco = re.compile(
        r'^(\d{6})\s+'                       # Codice 6 cifre
        r'(.+?BANCO.*?)\s+'                  # Descrizione con BANCO
        r'(\d{6})\s+'                        # Codice Materiale
        r'(\d+)\s+'                          # Quantità
        r'PZ'                                # UM
        r'(?:\s+(\d+)\s*PZ)?',               # Opzionale: XXPZ (pezzi contenuti)
        re.I
    )

    # =========================================
    # PRE-PROCESSING: Gestione righe orfane (migliorato)
    # =========================================
    # Regole:
    # 1. Ignorare righe "spazzatura" (header, footer, pagine)
    # 2. Concatenare solo righe brevi e significative
    # 3. Gestione speciale per XXPZ (pezzi espositore)

    processed_lines = []
    pattern_codice = re.compile(r'^\d{6,9}\s+')

    # Pattern per righe da IGNORARE completamente
    pattern_ignora = re.compile(
        r'^(Pagina|Indirizzo\s+spedizione|N\.documento|AIC/MINSAN|'
        r'Descrizione|Materiale|Tipo\s+posizione|Quantit|UM|Prezzo|'
        r'%\s*Sconto|%\s*IVA|Valore\s+netto|listino|netto|'
        r'Imponibile|IVA\s+vendite|Importo\s+finale|Note\s+attuali|'
        r'Totale\s+quantit|Cooperativa|N\./data\s+riferimento|'
        r'I-\d{5}|FARMACIA|VIA\s+|CORSO\s+|PIAZZA\s+|VIALE\s+|'
        r'CLDM|P\.I\.|ID\s+MIN|Num\.\d|Agente\s+|Tipo\s+ZTO|'
        r'Area\s+vendite|Italia$|Conferma\s+ordine|\d{10}\s*/\s*\d)',
        re.I
    )

    # Pattern per righe che sono SOLO numero di pagina
    pattern_solo_numero = re.compile(r'^\d{1,3}$')

    # Pattern per XXPZ (pezzi espositore) - riga orfana significativa
    pattern_pezzi = re.compile(r'^(\d+)\s*PZ\s*$', re.I)

    # Pattern per continuazione descrizione (breve, no numeri iniziali)
    pattern_continuazione = re.compile(r'^[A-Z]{2,}.*$', re.I)

    ultimo_parent_idx = None  # Indice dell'ultimo parent espositore trovato

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 1. Se inizia con codice prodotto -> nuova riga
        if pattern_codice.match(line):
            processed_lines.append(line)
            # Controlla se è un parent espositore (6 cifre, no prezzo alla fine)
            if re.match(r'^\d{6}\s+', line) and not re.match(r'^\d{7,9}\s+', line):
                # Verifica che non abbia prezzo (ultima colonna numerica con decimali)
                if not re.search(r'\d+[,\.]\d{2}\s*$', line):
                    ultimo_parent_idx = len(processed_lines) - 1
            continue

        # 2. Ignora righe spazzatura
        if pattern_ignora.match(line):
            continue

        # 3. Ignora numeri di pagina isolati
        if pattern_solo_numero.match(line):
            continue

        # 4. Gestione speciale XXPZ -> associa al parent espositore
        m_pezzi = pattern_pezzi.match(line)
        if m_pezzi and ultimo_parent_idx is not None:
            pezzi = m_pezzi.group(1)
            processed_lines[ultimo_parent_idx] += f' {pezzi}PZ'
            continue

        # 5. Concatena righe brevi significative alla riga precedente
        if processed_lines and len(line) < 30:
            if pattern_continuazione.match(line) or re.match(r'^\d+\s*(PZ|ML|MG|CPR|BS|FL)', line, re.I):
                processed_lines[-1] += ' ' + line
                continue

    # Usa le righe processate invece delle originali
    lines = processed_lines

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Prova SC.MERCE
        m = pattern_scmerce.match(line)
        if m:
            aic_norm = normalize_aic_simple(m.group(1))
            righe_raw.append({
                'codice_aic': aic_norm,
                'codice_originale': m.group(1),
                'descrizione': m.group(2).strip(),
                'codice_materiale': m.group(3),
                'tipo_posizione': 'SC.MERCE',
                'quantita': parse_int(m.group(4)),
                'prezzo_listino': 0,
                'sconto_pct': 0,
                'prezzo_netto': 0,
                'aliquota_iva': 0,
                'valore_netto': 0,
            })
            continue
        
        # Prova P.O.P.
        m = pattern_pop.match(line)
        if m:
            aic_norm = normalize_aic_simple(m.group(1))
            righe_raw.append({
                'codice_aic': aic_norm,
                'codice_originale': m.group(1),
                'descrizione': m.group(2).strip(),
                'codice_materiale': m.group(3),
                'tipo_posizione': 'P.O.P.',
                'quantita': parse_int(m.group(4)),
                'prezzo_listino': 0,
                'sconto_pct': 0,
                'prezzo_netto': 0,
                'aliquota_iva': 0,
                'valore_netto': 0,
            })
            continue
        
        # Prova parent espositore (6 cifre con XXPZ)
        m = pattern_parent.match(line)
        if m:
            aic_norm = normalize_aic_simple(m.group(1))
            righe_raw.append({
                'codice_aic': aic_norm,
                'codice_originale': m.group(1),
                'descrizione': m.group(2).strip(),
                'codice_materiale': m.group(3),
                'tipo_posizione': '',
                'quantita': parse_int(m.group(4)),
                'prezzo_listino': 0,
                'sconto_pct': 0,
                'prezzo_netto': 0,
                'aliquota_iva': 10,
                'valore_netto': 0,
            })
            continue

        # Prova parent espositore con BANCO
        m = pattern_parent_banco.match(line)
        if m:
            aic_norm = normalize_aic_simple(m.group(1))
            descrizione = m.group(2).strip()

            # Cerca XXPZ nella descrizione concatenata (può venire da riga orfana)
            pezzi_match = re.search(r'(\d+)\s*PZ', descrizione)
            if pezzi_match:
                descrizione_con_pz = descrizione
            else:
                # Cerca se c'è XXPZ alla fine della riga (da riga orfana)
                pezzi_fine = m.group(5) if m.lastindex >= 5 and m.group(5) else None
                if pezzi_fine:
                    descrizione_con_pz = f"{descrizione} {pezzi_fine}PZ"
                else:
                    descrizione_con_pz = descrizione

            righe_raw.append({
                'codice_aic': aic_norm,
                'codice_originale': m.group(1),
                'descrizione': descrizione_con_pz,
                'codice_materiale': m.group(3),
                'tipo_posizione': '',
                'quantita': parse_int(m.group(4)),
                'prezzo_listino': 0,
                'sconto_pct': 0,
                'prezzo_netto': 0,
                'aliquota_iva': 10,
                'valore_netto': 0,
            })
            continue

        # Prova vendita normale
        m = pattern_vendita.match(line)
        if m:
            aic_norm = normalize_aic_simple(m.group(1))
            righe_raw.append({
                'codice_aic': aic_norm,
                'codice_originale': m.group(1),
                'descrizione': m.group(2).strip(),
                'codice_materiale': m.group(3),
                'tipo_posizione': '',
                'quantita': parse_int(m.group(4)),
                'prezzo_listino': parse_decimal(m.group(5)),
                'sconto_pct': parse_decimal(m.group(6)),
                'prezzo_netto': parse_decimal(m.group(7)),
                'aliquota_iva': parse_decimal(m.group(8)),
                'valore_netto': parse_decimal(m.group(9)),
            })
            continue
    
    data['righe_raw'] = righe_raw

    # Elabora con logica espositori
    if righe_raw:
        ctx = elabora_righe_ordine(righe_raw, vendor='ANGELINI')
        data['righe'] = ctx.righe_output
        data['anomalie_espositore'] = ctx.anomalie
        data['_stats'] = {
            'righe_raw': len(righe_raw),
            'righe_output': len(ctx.righe_output),
            'espositori': ctx.espositori_elaborati,
            'chiusure_normali': ctx.chiusure_normali,
            'chiusure_forzate': ctx.chiusure_forzate,
            'anomalie': len(ctx.anomalie),
        }
    
    return [data]


# =============================================================================
# WRAPPER
# =============================================================================

def extract(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """Wrapper per compatibilità."""
    return extract_angelini(text, lines, pdf_path)
