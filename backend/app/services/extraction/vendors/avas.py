"""
EXTRACTOR_TO - Estrattore AVAS
==============================
Estrattore per ordini AVAS Pharmaceuticals S.r.l. (Transfer Order).

Struttura documento (1 pagina, layout fisso):
    Avas Pharmaceuticals S.r.l.
    Ripa di Porta Ticinese, 39 | 20143 Milano - MI
    Partita IVA e Codice Fiscale 09190500968        <- P.IVA vendor (NON cliente)
    ...
    Ns Rif. <riferimento>                            <- riferimento/agente
    Cod. Tracciabilità:
    TRANSFER ORDER N. Data <RAGIONE SOCIALE titolo>
    <NUMERO> <DATA GG/MM/AAAA> Sede Legale: <indirizzo sede legale>
    <CAP> <CITTA> (<PR>)
    P.Iva Cliente Codice Fiscale Sede Dest.: <RAGIONE SOCIALE destinazione>
    <indirizzo destinazione>
    <P.IVA CLIENTE 11 cifre>
    <CAP> <CITTA> (<PR>)                             <- destinazione
    Ordine trasferito a
    <DISTRIBUTORE>                                   <- informativo (FARVIMA/SOFAD...)
    <indirizzo distributore>
    Note
    Dilazione pagamento <NN>gg d.f.
    Prezzo al Sconto P. netto Tot.
    AIC / PARAF Descrizione Q.ta Iva
    pubblico netto unitario imponibile
    <AIC9> <DESCRIZIONE> <Q.ta> <PrezzoPub> <Sconto%> <PNettoUnit> <Iva%> <TotImp>
    ...
    Riepilogo IVA ...

Note implementative:
- Numero ordine e data: dalla riga "<num> <data> Sede Legale:".
- Si usano i dati della "Sede Dest." (destinazione merce) per la testata; il
  lookup farmacia avviene comunque sulla P.IVA cliente.
- Il "P. netto unitario" della tabella è GIA' scontato (prezzo pubblico meno lo
  sconto). Come per ZENTIVA, popoliamo prezzo_netto e prezzo_pubblico e NON gli
  sconti, per evitare doppia applicazione lato ERP. La % sconto resta informativa.
- "Ordine trasferito a" (FARVIMA/SOFAD/...) è informativo: il distributore del
  codice EDI deriva dal deposito in anagrafica, non dal PDF.
- Nessuna gestione espositori.

v1.0: Implementazione iniziale
"""

import re
from typing import Dict, List

from ....utils import parse_date, normalize_aic


# Riga prodotto:
#   <AIC 6-10 cifre> <descrizione> <q.ta> <prezzo pub X,XX> <sconto XX,XX%>
#   <p.netto unit X,XXXXX> <iva NN%> <tot imponibile X,XXXXX>
# La descrizione può contenere numeri/virgole/punti (es. "BLOPRESID 16MG 12.5MG
# 28CPR", "LEXOTAN 1,5MG 20CPR"): la coda numerica fissa àncora il parsing.
_ROW_RE = re.compile(
    r'^(\d{6,10})\s+'        # 1: AIC / PARAF
    r'(.+?)\s+'              # 2: descrizione (non greedy)
    r'(\d+)\s+'             # 3: quantità
    r'(\d+,\d{2})\s+'       # 4: prezzo pubblico
    r'(\d+,\d{2})\s*%\s+'   # 5: sconto %
    r'([\d.,]+)\s+'         # 6: prezzo netto unitario
    r'(\d+)\s*%\s+'         # 7: aliquota IVA
    r'([\d.,]+)$'           # 8: totale imponibile (non usato)
)


def extract_avas(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF AVAS.

    Returns:
        Lista con un dizionario ordine estratto (un ordine per PDF).
    """
    data: Dict = {'vendor': 'AVAS', 'righe': []}

    # =========================================================================
    # 1. NUMERO ORDINE + DATA ORDINE
    #    Riga: "246 16/06/2026 Sede Legale: CORSO ..."
    # =========================================================================
    m = re.search(
        r'^(\d{1,8})\s+(\d{2}/\d{2}/\d{4})\s+Sede\s+Legale',
        text, re.M | re.I
    )
    if m:
        data['numero_ordine'] = m.group(1).strip()
        data['data_ordine'] = parse_date(m.group(2))
    else:
        # Fallback numero: footer "TRANSFER ORDER N. 246 - Pagina 1"
        mn = re.search(r'TRANSFER\s+ORDER\s+N\.?\s*(\d+)', text, re.I)
        if mn:
            data['numero_ordine'] = mn.group(1)
        # Fallback data: prima GG/MM/AAAA del documento
        md = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if md:
            data['data_ordine'] = parse_date(md.group(1))

    # =========================================================================
    # 2. PARTITA IVA CLIENTE (11 cifre, DOPO l'etichetta "P.Iva Cliente")
    #    NB: la P.IVA del vendor (09190500968) compare PRIMA, quindi si àncora
    #    dopo "P.Iva Cliente" per non pescarla.
    # =========================================================================
    m = re.search(r'P\.?\s*Iva\s+Cliente[\s\S]{0,200}?\b(\d{11})\b', text, re.I)
    if m:
        data['partita_iva'] = m.group(1)

    # =========================================================================
    # 3-6. BLOCCO DESTINAZIONE (Sede Dest.)
    #    riga i  : "...Sede Dest.: <RAGIONE SOCIALE>"
    #    riga i+1: "<indirizzo>"
    #    riga i+2: "<P.IVA 11 cifre>"
    #    riga i+3: "<CAP> <CITTA> (<PR>)"
    # =========================================================================
    dest_idx = None
    for i, line in enumerate(lines):
        md = re.search(r'Sede\s+Dest\.?\s*:?\s*(.+)$', line, re.I)
        if md:
            dest_idx = i
            ragione = md.group(1).strip()
            if ragione:
                data['ragione_sociale'] = ragione[:50]
            break

    if dest_idx is not None:
        # Indirizzo: prima riga successiva con prefisso topografico
        # (CORSO/VIA/PIAZZA...), prima del CAP cliente.
        for j in range(dest_idx + 1, min(dest_idx + 5, len(lines))):
            cand = lines[j].strip()
            if re.match(
                r'^(VIA|V\.LE|VIALE|CORSO|C\.SO|PIAZZA|P\.ZZA|PIAZZALE|P\.LE|'
                r'LARGO|VICOLO|CONTRADA|STRADA|LOC\.?|LOCALITA|FRAZ\.?|BORGO)\b',
                cand, re.I
            ):
                data['indirizzo'] = cand[:50]
                break

        # CAP / Città / Provincia: prima riga "<CAP> <citta> (<PR>)" dopo la
        # destinazione. (La prima occorrenza prima di questo blocco è la Sede
        # Legale, che scartiamo partendo da dest_idx.)
        for j in range(dest_idx + 1, min(dest_idx + 6, len(lines))):
            mc = re.match(r'^(\d{5})\s+(.+?)\s*\(([A-Za-z]{2})\)\s*$', lines[j].strip())
            if mc:
                data['cap'] = mc.group(1)
                citta = mc.group(2).strip()
                # Scarta città degenere (es. "92029" ripetuto al posto del nome)
                if citta and not citta.isdigit():
                    data['citta'] = citta.upper()[:50]
                data['provincia'] = mc.group(3).upper()
                break

    # Fallback ragione sociale: titolo "TRANSFER ORDER N. Data <RAGIONE>"
    if not data.get('ragione_sociale'):
        mt = re.search(r'TRANSFER\s+ORDER\s+N\.?\s+Data\s+(.+)$', text, re.M | re.I)
        if mt:
            data['ragione_sociale'] = mt.group(1).strip()[:50]

    # =========================================================================
    # 7. RIFERIMENTO / AGENTE - "Ns Rif. <valore>"
    # =========================================================================
    m = re.search(r'Ns\s+Rif\.?\s*(.+)$', text, re.M | re.I)
    if m:
        rif = m.group(1).strip()
        if rif:
            data['nome_agente'] = rif[:50]

    # =========================================================================
    # 8. DILAZIONE PAGAMENTO - "Dilazione pagamento 60gg d.f."
    # =========================================================================
    m = re.search(r'Dilazione\s+pagamento\s+(\d+)\s*gg', text, re.I)
    if m:
        data['gg_dilazione'] = int(m.group(1))

    # =========================================================================
    # 9. RIGHE PRODOTTO
    # =========================================================================
    n_riga = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Stop alla sezione riepilogo IVA / totali
        if stripped.startswith('Riepilogo IVA') or stripped.startswith('Totale IVA'):
            break

        m = _ROW_RE.match(stripped)
        if not m:
            continue

        aic_raw = m.group(1)
        descrizione = m.group(2).strip()
        q_venduta = int(m.group(3))
        prezzo_pubblico = _parse_eu(m.group(4))
        prezzo_netto = _parse_eu(m.group(6))
        try:
            aliquota_iva = int(m.group(7))
        except ValueError:
            aliquota_iva = 10

        aic_norm, aic_orig, is_esp, is_child = normalize_aic(aic_raw, descrizione)

        n_riga += 1
        data['righe'].append({
            'n_riga': n_riga,
            'codice_aic': aic_norm or aic_raw,
            'codice_originale': aic_orig or aic_raw,
            'descrizione': descrizione[:100],
            'data_consegna': data.get('data_consegna', ''),
            'q_venduta': q_venduta,
            'q_omaggio': 0,
            'q_sconto_merce': 0,
            # Prezzo netto unitario AVAS = già scontato -> sconti a 0 per evitare
            # doppia applicazione lato ERP (stesso approccio di ZENTIVA).
            'sconto1': 0.0,
            'sconto2': 0.0,
            'prezzo_netto': prezzo_netto,
            'prezzo_pubblico': prezzo_pubblico,
            'aliquota_iva': aliquota_iva,
            'is_espositore': is_esp,
            'is_child': is_child,
            'is_no_aic': False,
        })

    return [data] if data.get('righe') or data.get('numero_ordine') else []


def _parse_eu(price_str: str) -> float:
    """Converte prezzo formato europeo: '6,89' -> 6.89, '1.234,56' -> 1234.56."""
    if not price_str:
        return 0.0
    s = str(price_str).strip().replace('€', '').strip()
    if not s:
        return 0.0
    if '.' in s and ',' in s:
        # Punto = separatore migliaia, virgola = decimale
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0
