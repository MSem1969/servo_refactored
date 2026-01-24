# =============================================================================
# SERV.O v8.0 - ESPOSITORE SERVICE
# =============================================================================
# Gestione logica espositori parent-child multi-vendor
# - ANGELINI: codice 6 cifre + XXPZ, chiusura su pezzi
# - MENARINI: codice "--" + keywords + prezzo>0, chiusura su somma netto
# =============================================================================

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


# =============================================================================
# COSTANTI
# =============================================================================

FASCIA_SCOSTAMENTO = {
    'ZERO': (0, 0),
    'BASSO': (-10, 10),
    'MEDIO': (-20, 20),
    'ALTO': (-50, 50),
    'CRITICO': (-100, 100),
}

CODICI_ANOMALIA = {
    # Anomalie Espositore
    'ESP-A01': 'Pezzi child inferiori ad attesi',
    'ESP-A02': 'Pezzi child superiori ad attesi',
    'ESP-A03': 'Espositore senza righe child',
    'ESP-A04': 'Chiusura forzata per nuovo parent',
    'ESP-A05': 'Chiusura forzata a fine documento',
    'ESP-A06': 'Conflitto pattern ML vs estrazione',
    'ESP-A07': 'Chiusura forzata per riga non correlata',  # v9.0
    # Anomalie Lookup Farmacia
    'LKP-A01': 'Lookup score inferiore a 80% - verifica obbligatoria',
    'LKP-A02': 'Farmacia non trovata in anagrafica',
    'LKP-A03': 'Lookup score 80-95% - verifica consigliata',
    'LKP-A04': 'P.IVA mismatch tra PDF e anagrafica - verifica obbligatoria',
    'LKP-A05': 'Cliente non trovato in anagrafica clienti - deposito non determinabile',
    # Anomalie Estrazione
    'EXT-A01': 'Vendor non riconosciuto - estrattore generico',
    # Anomalie Listino (v7.0)
    'LST-A01': 'Codice AIC non trovato nel listino - verifica obbligatoria',
    'LST-A02': 'Prezzo listino mancante - verifica obbligatoria',
    'LST-A03': 'Associazione listino confermata da pattern ML',
    # Anomalie Prezzo (v8.1)
    'PRICE-A01': 'Prodotto in vendita senza prezzo - verifica obbligatoria',
    # Anomalie AIC (v9.0)
    'AIC-A01': 'Codice AIC mancante o non valido - verifica obbligatoria',
}

FASCE_SUPERVISIONE_OBBLIGATORIA = {'ALTO', 'CRITICO'}

# Soglie lookup score
LOOKUP_SCORE_GRAVE = 80      # Sotto: anomalia GRAVE (bloccante)
LOOKUP_SCORE_ORDINARIA = 95  # Sotto: anomalia ORDINARIA (non bloccante)


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class RigaChild:
    """Riga child accumulata in un espositore."""
    codice_aic: str
    codice_originale: str
    codice_materiale: str
    descrizione: str
    quantita: int
    prezzo_netto: float
    valore_netto: float
    aliquota_iva: float = 10.0
    n_riga_originale: int = 0
    is_espositore_vuoto: bool = False  # v8.1: Flag per espositore vuoto (non conta nei pezzi)


@dataclass
class Espositore:
    """Rappresenta un espositore attivo durante l'elaborazione."""
    codice_aic: str
    codice_originale: str
    codice_materiale: str
    descrizione: str
    pezzi_per_unita: int
    quantita_parent: int
    aliquota_iva: float = 10.0
    n_riga: int = 0
    
    righe_child: List[RigaChild] = field(default_factory=list)
    pezzi_accumulati: int = 0
    valore_netto_accumulato: float = 0.0
    timestamp_apertura: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def pezzi_attesi_totali(self) -> int:
        return self.pezzi_per_unita * self.quantita_parent
    
    def aggiungi_child(self, child: RigaChild) -> None:
        self.righe_child.append(child)
        # v8.1: Non contare pezzi per espositore vuoto (omaggio contenitore)
        if not child.is_espositore_vuoto:
            self.pezzi_accumulati += child.quantita
        self.valore_netto_accumulato += child.valore_netto
    
    def calcola_prezzo_netto_parent(self) -> float:
        if self.quantita_parent <= 0:
            return 0.0
        return round(self.valore_netto_accumulato / self.quantita_parent, 3)
    
    def verifica_scostamento(self) -> Tuple[str, float]:
        if self.pezzi_attesi_totali == 0:
            return 'ZERO', 0.0
        
        scostamento_pct = ((self.pezzi_accumulati - self.pezzi_attesi_totali) 
                          / self.pezzi_attesi_totali) * 100
        
        if scostamento_pct == 0:
            return 'ZERO', 0.0
        elif -10 <= scostamento_pct <= 10:
            return 'BASSO', scostamento_pct
        elif -20 <= scostamento_pct <= 20:
            return 'MEDIO', scostamento_pct
        elif -50 <= scostamento_pct <= 50:
            return 'ALTO', scostamento_pct
        else:
            return 'CRITICO', scostamento_pct
    
    def genera_metadata_json(self, chiusura: str = 'NORMALE', motivo: str = '') -> str:
        """
        Genera metadata JSON per espositore.

        v3.2: Aggiunto child_dettaglio con codice, descrizione, quantità per ogni child.
        """
        # v3.2: Dettaglio completo child per supervisione
        child_dettaglio = [
            {
                'codice': c.codice_originale,
                'aic': c.codice_aic,
                'descrizione': c.descrizione[:30] if c.descrizione else '',
                'quantita': c.quantita,
                'prezzo_netto': c.prezzo_netto,
                'valore_netto': round(c.valore_netto, 2),
            }
            for c in self.righe_child
        ]

        metadata = {
            'pezzi_per_unita': self.pezzi_per_unita,
            'quantita_parent': self.quantita_parent,
            'pezzi_attesi_totali': self.pezzi_attesi_totali,
            'pezzi_trovati': self.pezzi_accumulati,
            'valore_netto_child': round(self.valore_netto_accumulato, 2),
            'prezzo_calcolato': self.calcola_prezzo_netto_parent(),
            'num_child': len(self.righe_child),
            'child_codici': [c.codice_originale for c in self.righe_child],
            'child_dettaglio': child_dettaglio,  # v3.2: Dettaglio completo
            'chiusura': chiusura,
            'motivo_chiusura': motivo,
            'timestamp': self.timestamp_apertura,
        }
        return json.dumps(metadata, ensure_ascii=False)


@dataclass
class ContestoElaborazione:
    """Contesto di elaborazione per un ordine."""
    espositore_attivo: Optional[Espositore] = None
    righe_output: List[Dict] = field(default_factory=list)
    anomalie: List[Dict] = field(default_factory=list)
    contatore_righe: int = 0
    vendor: str = 'ANGELINI'
    
    espositori_elaborati: int = 0
    chiusure_normali: int = 0
    chiusure_forzate: int = 0


# =============================================================================
# ESP01: CLASSIFICAZIONE RIGHE
# =============================================================================

def identifica_tipo_riga(codice: str, descrizione: str, tipo_posizione: str = '', vendor: str = '') -> str:
    """
    ESP01 v3.2: Classifica tipo riga con priorità tipo_posizione.

    v3.2: Aggiunto supporto MENARINI
    - MENARINI: parent ha codice "--" + keywords espositore
    - ANGELINI: parent ha codice 6 cifre + XXPZ o keywords
    """
    codice = str(codice).strip() if codice else ''
    tipo_posizione = str(tipo_posizione).strip().upper() if tipo_posizione else ''
    descrizione = str(descrizione).upper() if descrizione else ''
    vendor = str(vendor).upper() if vendor else ''

    if 'SC.MERCE' in tipo_posizione or 'SCMERCE' in tipo_posizione:
        return 'SCONTO_MERCE'

    if 'P.O.P' in tipo_posizione or 'POP' in tipo_posizione:
        return 'MATERIALE_POP'

    # v3.2: MENARINI - parent ha codice "--" + keywords
    if vendor == 'MENARINI':
        if codice == '--' and re.search(r'BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA', descrizione, re.I):
            return 'PARENT_ESPOSITORE'
        # Qualsiasi altra riga MENARINI è prodotto standard (child gestiti da state machine)
        return 'PRODOTTO_STANDARD'

    # ANGELINI e altri vendor: logica esistente
    codice_num = re.sub(r'[^\d]', '', codice)
    len_codice = len(codice_num)

    if len_codice == 6:
        # Espositori con XXPZ nella descrizione
        if re.search(r'\d+\s*PZ\b', descrizione):
            return 'PARENT_ESPOSITORE'
        # Espositori identificati da parole chiave (anche senza XXPZ)
        elif re.search(r'BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA', descrizione, re.I):
            return 'PARENT_ESPOSITORE'
        else:
            return 'PROMO_AUTONOMA'

    return 'PRODOTTO_STANDARD'


# =============================================================================
# ESP02: ESTRAZIONE PEZZI
# =============================================================================

def estrai_pezzi_espositore(descrizione: str, quantita: int) -> Tuple[Optional[int], Optional[int]]:
    """
    ESP02: Estrae pezzi per unità.

    v8.1: Aggiunto supporto formato "X+Y" per MENARINI (es. "3+3" = 6 pezzi)
    """
    if not descrizione:
        return (None, None)

    descrizione = str(descrizione).upper()

    # v8.1: Pattern "X+Y" per MENARINI (es. "EXPO BANCO 3+3" = 6 pezzi)
    match_sum = re.search(r'(\d+)\s*\+\s*(\d+)(?!\d)', descrizione)
    if match_sum:
        pezzi_per_unita = int(match_sum.group(1)) + int(match_sum.group(2))
        if 1 <= pezzi_per_unita <= 1000:
            return (pezzi_per_unita, pezzi_per_unita * quantita)

    patterns = [
        r'FSTAND\s*(\d+)\s*PZ',
        r'DBOX\s*(\d+)\s*PZ',
        r'EXPO\s*(\d+)\s*PZ',
        r'BANCO\s*(\d+)\s*PZ',
        r'(\d+)\s*PZ\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, descrizione)
        if match:
            pezzi_per_unita = int(match.group(1))
            if 1 <= pezzi_per_unita <= 1000:
                return (pezzi_per_unita, pezzi_per_unita * quantita)

    return (None, None)


# =============================================================================
# ESP06: ELABORAZIONE COMPLETA
# =============================================================================

def elabora_righe_ordine(righe_raw: List[Dict], vendor: str = 'ANGELINI') -> ContestoElaborazione:
    """
    ESP06: Elaborazione completa righe ordine con gestione espositori.

    v3.2: Aggiunto supporto MENARINI
    - Legge tipo_riga oltre a tipo_riga_raw
    - Chiusura MENARINI basata su somma valore netto (non pezzi)
    """
    ctx = ContestoElaborazione(vendor=vendor)

    # v3.2: Per MENARINI, traccia prezzo netto parent per chiusura
    menarini_netto_parent = 0.0

    for riga in righe_raw:
        codice = riga.get('codice_originale', '')
        descrizione = riga.get('descrizione', '')
        tipo_posizione = riga.get('tipo_posizione', '')

        # v3.2: Legge tipo_riga o tipo_riga_raw (per estrattori che pre-marcano)
        tipo = riga.get('tipo_riga_raw') or riga.get('tipo_riga') or identifica_tipo_riga(codice, descrizione, tipo_posizione, vendor)

        # v10.3: CORREZIONE - Se la riga è marcata come child dall'estrattore,
        # NON trattarla come PARENT anche se identifica_tipo_riga la classificherebbe così
        # (es: espositore vuoto MENARINI con cod_min='--' e keywords)
        is_marked_child = riga.get('is_child', False) or riga.get('_belongs_to_parent', False)
        if tipo == 'PARENT_ESPOSITORE' and is_marked_child:
            tipo = 'CHILD_ESPOSITORE'

        # SCONTO_MERCE: sempre autonomo
        if tipo == 'SCONTO_MERCE':
            ctx.contatore_righe += 1
            riga_output = _crea_riga_output(riga, ctx.contatore_righe, 'SCONTO_MERCE')
            riga_output['q_sconto_merce'] = riga.get('quantita', 0)
            riga_output['q_venduta'] = 0
            riga_output['richiede_supervisione'] = False
            ctx.righe_output.append(riga_output)
            continue

        # MATERIALE_POP: sempre autonomo
        if tipo == 'MATERIALE_POP':
            ctx.contatore_righe += 1
            riga_output = _crea_riga_output(riga, ctx.contatore_righe, 'MATERIALE_POP')
            riga_output['q_omaggio'] = riga.get('quantita', 0)
            riga_output['q_venduta'] = 0
            riga_output['richiede_supervisione'] = False
            ctx.righe_output.append(riga_output)
            continue
        
        # PARENT_ESPOSITORE: chiudi precedente, apri nuovo
        if tipo == 'PARENT_ESPOSITORE':
            if ctx.espositore_attivo:
                ctx.contatore_righe += 1
                riga_out, righe_child, anomalia = _chiudi_espositore_forzato(
                    ctx.espositore_attivo, ctx.contatore_righe, 'NUOVO_PARENT', ctx.vendor
                )
                ctx.righe_output.append(riga_out)
                ctx.righe_output.extend(righe_child)  # v10.2: Ripristinato per salvataggio child nel DB
                if anomalia:
                    ctx.anomalie.append(anomalia)
                ctx.chiusure_forzate += 1

            pezzi = riga.get('pezzi_per_unita') or estrai_pezzi_espositore(descrizione, 1)[0] or 0

            # v3.2: Per MENARINI, traccia prezzo netto parent per chiusura
            if vendor.upper() == 'MENARINI':
                menarini_netto_parent = float(riga.get('prezzo_netto', 0) or riga.get('prezzo_netto_parent', 0) or 0)

            ctx.espositore_attivo = Espositore(
                codice_aic=riga.get('codice_aic', ''),
                codice_originale=codice,
                codice_materiale=riga.get('codice_materiale', ''),
                descrizione=descrizione,
                pezzi_per_unita=pezzi,
                quantita_parent=riga.get('quantita', 0) or riga.get('q_venduta', 0) or 1,
                aliquota_iva=riga.get('aliquota_iva', 10),
                n_riga=ctx.contatore_righe + 1,
            )
            ctx.espositori_elaborati += 1
            continue
        
        # PRODOTTO_STANDARD o PROMO_AUTONOMA
        # v3.2: Include anche CHILD_ESPOSITORE per MENARINI (già marcati dall'estrattore)
        if tipo in ['PRODOTTO_STANDARD', 'PROMO_AUTONOMA', 'CHILD_ESPOSITORE']:
            # v9.0: Per MENARINI, verifica che la riga sia effettivamente un child
            # L'estrattore MENARINI marca le righe con is_child o _belongs_to_parent
            should_add_to_parent = False
            if ctx.espositore_attivo:
                if vendor.upper() == 'MENARINI':
                    # Per MENARINI: aggiungi SOLO se l'estrattore ha marcato come child
                    is_marked_child = riga.get('is_child', False) or riga.get('_belongs_to_parent', False)
                    is_child_type = tipo == 'CHILD_ESPOSITORE'
                    should_add_to_parent = is_marked_child or is_child_type
                else:
                    # Per altri vendor (ANGELINI): aggiungi tutte le righe dopo il parent
                    should_add_to_parent = True

            # v9.0: Per MENARINI, se c'è un espositore attivo ma questa riga NON è un child,
            # chiudi l'espositore forzatamente (la riga interrompe la sequenza)
            if ctx.espositore_attivo and not should_add_to_parent and vendor.upper() == 'MENARINI':
                ctx.contatore_righe += 1
                riga_out, righe_child, anomalia = _chiudi_espositore_forzato(
                    ctx.espositore_attivo, ctx.contatore_righe, 'RIGA_NON_CHILD', ctx.vendor
                )
                ctx.righe_output.append(riga_out)
                ctx.righe_output.extend(righe_child)  # v10.2: Ripristinato per salvataggio child nel DB
                if anomalia:
                    ctx.anomalie.append(anomalia)
                ctx.chiusure_forzate += 1
                ctx.espositore_attivo = None
                menarini_netto_parent = 0.0

            if should_add_to_parent:
                # v9.3: Per MENARINI usa valore_netto dal PDF (Totale Netto)
                # Per altri vendor calcola prezzo_netto × quantità
                child_quantita = int(riga.get('quantita', 0) or riga.get('q_venduta', 0) or 0)
                child_prezzo = float(riga.get('prezzo_netto', 0) or 0)
                # v9.3: Usa valore_netto se presente (MENARINI), altrimenti calcola
                child_valore_calcolato = float(riga.get('valore_netto', 0) or 0)
                if child_valore_calcolato == 0:
                    child_valore_calcolato = child_prezzo * child_quantita

                # v8.1: Rileva espositore vuoto (omaggio contenitore MENARINI)
                # Espositore vuoto: nessun AIC valido E prezzo_netto = 0
                is_espositore_vuoto = riga.get('is_espositore_vuoto', False)
                # Backup detection: se non ha AIC e prezzo 0, è probabile espositore vuoto
                if not is_espositore_vuoto and not riga.get('codice_aic') and child_prezzo == 0:
                    is_espositore_vuoto = True

                child = RigaChild(
                    codice_aic=riga.get('codice_aic', ''),
                    codice_originale=codice,
                    codice_materiale=riga.get('codice_materiale', ''),
                    descrizione=descrizione,
                    quantita=child_quantita,
                    prezzo_netto=child_prezzo,
                    valore_netto=child_valore_calcolato,  # Calcolato, non da PDF
                    aliquota_iva=float(riga.get('aliquota_iva', 10) or 10),
                    n_riga_originale=ctx.contatore_righe + 1,
                    is_espositore_vuoto=is_espositore_vuoto,  # v8.1
                )
                ctx.espositore_attivo.aggiungi_child(child)

                # v9.0: Logica chiusura differenziata per vendor
                # IMPORTANTE: Il valore è usato come VERIFICA, non criterio esclusivo
                should_close = False

                # v10.3: Verifica se abbiamo già un espositore vuoto tra i child
                has_espositore_vuoto = any(c.is_espositore_vuoto for c in ctx.espositore_attivo.righe_child)

                if vendor.upper() == 'MENARINI':
                    # v10.3: MENARINI chiude SOLO se:
                    # 1. Valore raggiunto E abbiamo già l'espositore vuoto (con codice materiale)
                    # 2. Oppure se la riga corrente È l'espositore vuoto (chiudi dopo averlo aggiunto)
                    value_reached = False
                    if menarini_netto_parent > 0:
                        diff = ctx.espositore_attivo.valore_netto_accumulato - menarini_netto_parent
                        tolleranza = menarini_netto_parent * 0.05  # 5% di tolleranza
                        if diff >= -tolleranza:
                            value_reached = True

                    # La riga corrente è un espositore vuoto?
                    current_is_espositore_vuoto = child.is_espositore_vuoto

                    # Chiudi se: valore raggiunto E (abbiamo espositore vuoto O la riga corrente lo è)
                    if value_reached and (has_espositore_vuoto or current_is_espositore_vuoto):
                        should_close = True

                    # v9.0: Fallback - se abbiamo pezzi_per_unita e li abbiamo raggiunti
                    if not should_close and ctx.espositore_attivo.pezzi_per_unita:
                        pezzi_attesi = ctx.espositore_attivo.pezzi_per_unita * ctx.espositore_attivo.quantita_parent
                        if ctx.espositore_attivo.pezzi_accumulati >= pezzi_attesi:
                            # Anche qui, aspetta l'espositore vuoto se non l'abbiamo ancora
                            if has_espositore_vuoto or current_is_espositore_vuoto:
                                should_close = True

                    # v9.0: Safety - se abbiamo già molti child (>20) e il valore è vicino (entro 20%)
                    if not should_close and len(ctx.espositore_attivo.righe_child) > 20:
                        if menarini_netto_parent > 0:
                            ratio = ctx.espositore_attivo.valore_netto_accumulato / menarini_netto_parent
                            if ratio >= 0.80:  # Almeno 80% del valore
                                should_close = True
                else:
                    # ANGELINI e altri: chiudi quando pezzi accumulati >= pezzi attesi
                    if ctx.espositore_attivo.pezzi_accumulati >= ctx.espositore_attivo.pezzi_attesi_totali:
                        should_close = True

                if should_close:
                    ctx.contatore_righe += 1
                    riga_out, righe_child, anomalia = _chiudi_espositore_normale(
                        ctx.espositore_attivo, ctx.contatore_righe, ctx.vendor
                    )
                    ctx.righe_output.append(riga_out)
                    ctx.righe_output.extend(righe_child)  # v10.2: Ripristinato per salvataggio child nel DB
                    if anomalia:
                        ctx.anomalie.append(anomalia)
                    ctx.espositore_attivo = None
                    ctx.chiusure_normali += 1
                    menarini_netto_parent = 0.0  # Reset per MENARINI
                continue
            
            ctx.contatore_righe += 1
            riga_output = _crea_riga_output(riga, ctx.contatore_righe, tipo)
            riga_output['richiede_supervisione'] = False
            ctx.righe_output.append(riga_output)
            continue
    
    # Fine documento: chiudi espositore residuo
    if ctx.espositore_attivo:
        ctx.contatore_righe += 1
        motivo = 'SENZA_CHILD' if len(ctx.espositore_attivo.righe_child) == 0 else 'FINE_DOCUMENTO'
        riga_out, righe_child, anomalia = _chiudi_espositore_forzato(
            ctx.espositore_attivo, ctx.contatore_righe, motivo, ctx.vendor
        )
        ctx.righe_output.append(riga_out)
        ctx.righe_output.extend(righe_child)  # v10.2: Ripristinato per salvataggio child nel DB
        if anomalia:
            ctx.anomalie.append(anomalia)
        ctx.chiusure_forzate += 1
        ctx.espositore_attivo = None

    return ctx


# =============================================================================
# v6.2 REFACTORING: UNIFIED CLOSURE FUNCTION
# =============================================================================

def _chiudi_espositore(
    esp: Espositore,
    n_riga: int,
    vendor: str,
    forzato: bool = False,
    motivo: str = ''
) -> Tuple[Dict, List[Dict], Optional[Dict]]:
    """
    Chiude espositore (unificata normale + forzato).

    v6.2 Refactoring: Unifica _chiudi_espositore_normale e _chiudi_espositore_forzato
    eliminando ~80 righe di codice duplicato.

    v10.3: Per MENARINI, recupera codice materiale dalla riga child "espositore vuoto"
    e lo assegna al parent.

    Args:
        esp: Espositore da chiudere
        n_riga: Numero riga corrente
        vendor: Codice vendor
        forzato: True per chiusura forzata
        motivo: Motivo chiusura (solo se forzato)

    Returns:
        Tuple[riga_parent, righe_child, anomalia]
    """
    prezzo_calcolato = esp.calcola_prezzo_netto_parent()
    fascia, scostamento_pct = esp.verifica_scostamento()

    # Richiede supervisione: sempre se forzato, altrimenti solo per fasce critiche
    richiede_supervisione = True if forzato or fascia in FASCE_SUPERVISIONE_OBBLIGATORIA else False

    # v10.3: Per MENARINI, cerca codice materiale nella riga child "espositore vuoto"
    # L'espositore vuoto è la riga con is_espositore_vuoto=True e contiene il codice
    # materiale dell'azienda (es: "87AA25") che deve essere assegnato al parent
    codice_materiale_parent = esp.codice_materiale
    codice_originale_parent = esp.codice_originale

    if vendor.upper() == 'MENARINI':
        for child in esp.righe_child:
            if child.is_espositore_vuoto:
                # Trovato espositore vuoto - usa il suo codice se valido
                codice_child = child.codice_originale
                if codice_child and codice_child != '--' and codice_child.strip():
                    codice_materiale_parent = codice_child
                    # Se il parent ha "--", usa anche come codice_originale
                    if codice_originale_parent == '--' or not codice_originale_parent:
                        codice_originale_parent = codice_child
                    break

    # Riga parent output
    riga_output = {
        'n_riga': n_riga,
        'codice_aic': esp.codice_aic,
        'codice_originale': codice_originale_parent,
        'codice_materiale': codice_materiale_parent,
        'descrizione': esp.descrizione,
        'q_venduta': esp.quantita_parent,
        'q_omaggio': 0,
        'q_sconto_merce': 0,
        'prezzo_netto': prezzo_calcolato,
        'prezzo_pubblico': 0,
        'aliquota_iva': esp.aliquota_iva,
        'valore_netto': esp.valore_netto_accumulato,
        'is_espositore': 1,
        'is_child': 0,
        'tipo_riga': 'PARENT_ESPOSITORE',
        'espositore_metadata': esp.genera_metadata_json('FORZATA' if forzato else 'NORMALE', motivo),
        'richiede_supervisione': richiede_supervisione,
        'stato_riga': 'ESTRATTO',
        '_id_parent_placeholder': True,
    }

    # Genera righe child (logica unificata)
    righe_child = _genera_righe_child(esp, n_riga)

    # Genera anomalia se necessario
    anomalia = _genera_anomalia_espositore(
        esp, fascia, scostamento_pct, vendor,
        forzato, motivo, richiede_supervisione
    )

    return riga_output, righe_child, anomalia


def _genera_righe_child(esp: Espositore, n_riga: int) -> List[Dict]:
    """
    Genera righe child per un espositore.

    v6.2: Funzione estratta per eliminare duplicazione.
    """
    righe_child = []
    for idx, child in enumerate(esp.righe_child):
        # v6.2 FIX: Calcola valore_netto da prezzo × quantità
        child_valore = child.prezzo_netto * child.quantita
        righe_child.append({
            'n_riga': n_riga + 0.001 * (idx + 1),
            'codice_aic': child.codice_aic,
            'codice_originale': child.codice_originale,
            'codice_materiale': child.codice_materiale,
            'descrizione': child.descrizione,
            'q_venduta': child.quantita,
            'q_omaggio': 0,
            'q_sconto_merce': 0,
            'prezzo_netto': child.prezzo_netto,
            'prezzo_pubblico': 0,
            'aliquota_iva': child.aliquota_iva,
            'valore_netto': child_valore,
            'is_espositore': 0,
            'is_child': 1,
            'tipo_riga': 'CHILD_ESPOSITORE',
            'richiede_supervisione': False,
            'stato_riga': 'ESTRATTO',
            '_belongs_to_parent': True,
        })
    return righe_child


def _genera_anomalia_espositore(
    esp: Espositore,
    fascia: str,
    scostamento_pct: float,
    vendor: str,
    forzato: bool,
    motivo: str,
    richiede_supervisione: bool
) -> Optional[Dict]:
    """
    Genera anomalia per espositore se necessario.

    v6.2: Funzione estratta per eliminare duplicazione.
    v6.2.1: Aggiunta verifica pattern ML prima di generare anomalie INFO.
            Se esiste un pattern ordinario con similarity >= 80%, non genera l'anomalia.
    """
    # v6.2.1: Prima di generare anomalia, verifica se esiste pattern ordinario
    # Questo evita di generare anomalie INFO per espositori già convalidati 5+ volte
    if not forzato or fascia not in FASCE_SUPERVISIONE_OBBLIGATORIA:
        # Solo per anomalie non bloccanti (INFO/ATTENZIONE)
        try:
            from .ml_pattern_matching import verifica_pattern_ordinario_per_espositore

            # Prepara lista child per confronto
            child_estratti = [
                {
                    'aic': c.codice_aic,
                    'codice': c.codice_originale,
                    'quantita': c.quantita
                }
                for c in esp.righe_child
            ]

            is_ordinario, similarity = verifica_pattern_ordinario_per_espositore(
                vendor=vendor,
                codice_espositore=esp.codice_originale,
                descrizione_espositore=esp.descrizione,
                child_estratti=child_estratti
            )

            if is_ordinario and similarity and similarity >= 80:
                # Pattern ordinario trovato con alta similarity: non generare anomalia
                return None

        except Exception:
            # Se errore ML, continua normalmente (genera anomalia)
            pass

    # Determina se serve anomalia e quale codice
    if forzato:
        if motivo == 'SENZA_CHILD' or len(esp.righe_child) == 0:
            codice_anom = 'ESP-A03'
        elif motivo == 'NUOVO_PARENT':
            codice_anom = 'ESP-A04'
        elif motivo == 'RIGA_NON_CHILD':
            codice_anom = 'ESP-A07'  # v9.0
        else:
            codice_anom = 'ESP-A05'
        livello = 'ERRORE'
        pattern_suffix = motivo
        desc_extra = ''
    elif esp.pezzi_accumulati != esp.pezzi_attesi_totali:
        codice_anom = 'ESP-A01' if esp.pezzi_accumulati < esp.pezzi_attesi_totali else 'ESP-A02'
        livello = 'ERRORE' if fascia in FASCE_SUPERVISIONE_OBBLIGATORIA else 'ATTENZIONE'
        pattern_suffix = fascia
        desc_extra = f' ({scostamento_pct:+.1f}%)'
    else:
        return None  # Nessuna anomalia - l'INFO con child viene gestita in pdf_processor

    # v3.2: Genera descrizione child per supervisione
    child_desc_parts = []
    for c in esp.righe_child[:5]:  # Max 5 child nella descrizione
        desc_short = c.descrizione[:15] if c.descrizione else c.codice_originale
        child_desc_parts.append(f"{c.codice_originale} {desc_short} x{c.quantita}")
    child_desc = ", ".join(child_desc_parts)
    if len(esp.righe_child) > 5:
        child_desc += f" (+{len(esp.righe_child) - 5} altri)"

    # v3.2: Descrizione arricchita con child
    descrizione_base = f"{CODICI_ANOMALIA[codice_anom]}: attesi {esp.pezzi_attesi_totali}, trovati {esp.pezzi_accumulati}{desc_extra}"
    if child_desc:
        descrizione_completa = f"{descrizione_base}\nChild: {child_desc}"
    else:
        descrizione_completa = descrizione_base

    return {
        'tipo_anomalia': 'ESPOSITORE',
        'livello': livello,
        'codice_anomalia': codice_anom,
        'descrizione': descrizione_completa,
        'valore_anomalo': f"{esp.codice_originale}: {esp.descrizione}",
        'richiede_supervisione': richiede_supervisione,
        'espositore_codice': esp.codice_originale,
        'espositore_descrizione': esp.descrizione,  # v3.2: Descrizione parent
        'pezzi_attesi': esp.pezzi_attesi_totali,
        'pezzi_trovati': esp.pezzi_accumulati,
        'valore_netto_child': round(esp.valore_netto_accumulato, 2),  # v3.2
        'fascia_scostamento': fascia,
        'motivo_chiusura': motivo if forzato else '',
        'pattern_signature': f"{vendor}_{codice_anom}_{esp.codice_originale}_{pattern_suffix}",
        # v3.2: Dettaglio child per pattern description
        'child_dettaglio': [
            {'codice': c.codice_originale, 'descrizione': c.descrizione[:20], 'quantita': c.quantita}
            for c in esp.righe_child
        ],
    }


# Wrapper di compatibilità per le chiamate esistenti
def _chiudi_espositore_normale(esp: Espositore, n_riga: int, vendor: str) -> Tuple[Dict, List[Dict], Optional[Dict]]:
    """Wrapper compatibilità: chiusura normale."""
    return _chiudi_espositore(esp, n_riga, vendor, forzato=False)


def _chiudi_espositore_forzato(esp: Espositore, n_riga: int, motivo: str, vendor: str) -> Tuple[Dict, List[Dict], Dict]:
    """Wrapper compatibilità: chiusura forzata."""
    return _chiudi_espositore(esp, n_riga, vendor, forzato=True, motivo=motivo)


def _crea_riga_output(riga: Dict, n_riga: int, tipo_riga: str) -> Dict:
    """Crea riga output formattata."""
    return {
        'n_riga': n_riga,
        'codice_aic': riga.get('codice_aic', ''),
        'codice_originale': riga.get('codice_originale', ''),
        'codice_materiale': riga.get('codice_materiale', ''),
        'descrizione': riga.get('descrizione', ''),
        'tipo_posizione': riga.get('tipo_posizione', ''),
        'q_venduta': int(riga.get('quantita', 0) or 0),
        'q_omaggio': 0,
        'q_sconto_merce': 0,
        'prezzo_listino': float(riga.get('prezzo_listino', 0) or 0),
        'prezzo_netto': float(riga.get('prezzo_netto', 0) or 0),
        'prezzo_pubblico': float(riga.get('prezzo_pubblico', 0) or 0),
        'sconto_1': float(riga.get('sconto_pct', 0) or 0),
        'aliquota_iva': float(riga.get('aliquota_iva', 10) or 10),
        'valore_netto': float(riga.get('valore_netto', 0) or 0),
        'is_espositore': 0,
        'is_child': 0,
        'tipo_riga': tipo_riga,
        'richiede_supervisione': False,
        'stato_riga': 'ESTRATTO',
    }


# =============================================================================
# v6.2: ML POST-ELABORAZIONE
# =============================================================================

def valuta_espositori_con_ml(
    ctx: ContestoElaborazione,
    id_testata: int,
    vendor: str
) -> ContestoElaborazione:
    """
    v6.2: Valuta espositori elaborati con sistema ML.

    Chiamata dopo elabora_righe_ordine() per confrontare ogni espositore
    con i pattern appresi. Se esiste un pattern ordinario con similarity
    alta, puo' applicare correzioni automatiche o generare ESP-A06.

    IMPORTANTE: Lavora SOLO su anomalie esistenti, non su ordini normali.

    Args:
        ctx: Contesto elaborazione con anomalie
        id_testata: ID ordine per logging
        vendor: Codice vendor

    Returns:
        Contesto aggiornato con eventuali anomalie ESP-A06
    """
    # Import lazy per evitare circular import
    from .ml_pattern_matching import valuta_espositore_con_ml

    # Verifica se ci sono anomalie espositore da valutare
    anomalie_espositore = [
        a for a in ctx.anomalie
        if a.get('tipo_anomalia') == 'ESPOSITORE'
        and a.get('codice_anomalia') in ('ESP-A01', 'ESP-A02', 'ESP-A03', 'ESP-A04', 'ESP-A05')
    ]

    if not anomalie_espositore:
        # Nessuna anomalia espositore, ML non si attiva
        return ctx

    # Per ogni anomalia, cerca pattern ML
    for anomalia in anomalie_espositore:
        codice_esp = anomalia.get('espositore_codice', '')
        if not codice_esp:
            continue

        # Trova la riga parent corrispondente
        parent_row = next(
            (r for r in ctx.righe_output
             if r.get('codice_originale') == codice_esp
             and r.get('is_espositore') == 1),
            None
        )

        if not parent_row:
            continue

        # Trova i child di questo parent
        child_rows = [
            r for r in ctx.righe_output
            if r.get('_belongs_to_parent')
            and r.get('is_child') == 1
        ]

        # Prepara lista child per confronto ML
        child_estratti = [
            {
                'aic': r.get('codice_aic', ''),
                'codice': r.get('codice_originale', ''),
                'descrizione': r.get('descrizione', ''),
                'quantita': r.get('q_venduta', 0)
            }
            for r in child_rows
        ]

        # Valuta con ML
        decision, anomalia_ml = valuta_espositore_con_ml(
            id_testata=id_testata,
            id_dettaglio=0,  # Non abbiamo ancora id_dettaglio
            vendor=vendor,
            codice_espositore=codice_esp,
            descrizione_espositore=parent_row.get('descrizione', ''),
            child_estratti=child_estratti
        )

        # Gestisci decisione ML
        if decision == 'APPLY_ML':
            # Pattern applicato automaticamente: rimuovi anomalia originale
            anomalia['ml_decision'] = 'APPLY_ML'
            anomalia['richiede_supervisione'] = False
            anomalia['livello'] = 'INFO'
            anomalia['descrizione'] += ' [ML: pattern applicato automaticamente]'

        elif decision == 'APPLY_WARNING':
            # Applicato con warning: mantieni anomalia ma non bloccante
            anomalia['ml_decision'] = 'APPLY_WARNING'
            anomalia['richiede_supervisione'] = False
            anomalia['livello'] = 'ATTENZIONE'
            anomalia['descrizione'] += ' [ML: pattern applicato con warning]'

        elif decision == 'SEND_SUPERVISION' and anomalia_ml:
            # Conflitto grave: aggiungi ESP-A06
            ctx.anomalie.append(anomalia_ml)
            anomalia['ml_decision'] = 'SEND_SUPERVISION'
            anomalia['descrizione'] += ' [ML: conflitto rilevato]'

    return ctx
