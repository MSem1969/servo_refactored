# =============================================================================
# TO_EXTRACTOR v6.1 - ESPOSITORE SERVICE
# =============================================================================
# Gestione logica espositori parent-child secondo REGOLE_ANGELINI v3.1
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
    # Anomalie Lookup
    'LKP-A01': 'Lookup score inferiore a 80% - verifica obbligatoria',
    'LKP-A02': 'Farmacia non trovata in anagrafica',
    'LKP-A03': 'Lookup score 80-95% - verifica consigliata',
    # Anomalie Estrazione
    'EXT-A01': 'Vendor non riconosciuto - estrattore generico',
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
        metadata = {
            'pezzi_per_unita': self.pezzi_per_unita,
            'quantita_parent': self.quantita_parent,
            'pezzi_attesi_totali': self.pezzi_attesi_totali,
            'pezzi_trovati': self.pezzi_accumulati,
            'valore_netto_child': round(self.valore_netto_accumulato, 2),
            'prezzo_calcolato': self.calcola_prezzo_netto_parent(),
            'num_child': len(self.righe_child),
            'child_codici': [c.codice_originale for c in self.righe_child],
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

def identifica_tipo_riga(codice: str, descrizione: str, tipo_posizione: str = '') -> str:
    """ESP01 v3.1: Classifica tipo riga con priorità tipo_posizione."""
    codice = str(codice).strip() if codice else ''
    tipo_posizione = str(tipo_posizione).strip().upper() if tipo_posizione else ''
    descrizione = str(descrizione).upper() if descrizione else ''
    
    if 'SC.MERCE' in tipo_posizione or 'SCMERCE' in tipo_posizione:
        return 'SCONTO_MERCE'
    
    if 'P.O.P' in tipo_posizione or 'POP' in tipo_posizione:
        return 'MATERIALE_POP'
    
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
    """ESP02: Estrae pezzi per unità."""
    if not descrizione:
        return (None, None)
    
    descrizione = str(descrizione).upper()
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
    """ESP06: Elaborazione completa righe ordine con gestione espositori."""
    ctx = ContestoElaborazione(vendor=vendor)
    
    for riga in righe_raw:
        codice = riga.get('codice_originale', '')
        descrizione = riga.get('descrizione', '')
        tipo_posizione = riga.get('tipo_posizione', '')
        
        tipo = riga.get('tipo_riga_raw') or identifica_tipo_riga(codice, descrizione, tipo_posizione)
        
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
                # Aggiungi righe child all'output
                ctx.righe_output.extend(righe_child)
                if anomalia:
                    ctx.anomalie.append(anomalia)
                ctx.chiusure_forzate += 1
            
            pezzi = riga.get('pezzi_per_unita') or estrai_pezzi_espositore(descrizione, 1)[0] or 0
            
            ctx.espositore_attivo = Espositore(
                codice_aic=riga.get('codice_aic', ''),
                codice_originale=codice,
                codice_materiale=riga.get('codice_materiale', ''),
                descrizione=descrizione,
                pezzi_per_unita=pezzi,
                quantita_parent=riga.get('quantita', 0),
                aliquota_iva=riga.get('aliquota_iva', 10),
                n_riga=ctx.contatore_righe + 1,
            )
            ctx.espositori_elaborati += 1
            continue
        
        # PRODOTTO_STANDARD o PROMO_AUTONOMA
        if tipo in ['PRODOTTO_STANDARD', 'PROMO_AUTONOMA']:
            if ctx.espositore_attivo:
                # v6.2 FIX: Calcola valore_netto da prezzo_netto × quantità
                # invece di usare il valore dal PDF che può essere arrotondato
                child_quantita = int(riga.get('quantita', 0) or 0)
                child_prezzo = float(riga.get('prezzo_netto', 0) or 0)
                child_valore_calcolato = child_prezzo * child_quantita

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
                )
                ctx.espositore_attivo.aggiungi_child(child)
                
                if ctx.espositore_attivo.pezzi_accumulati >= ctx.espositore_attivo.pezzi_attesi_totali:
                    ctx.contatore_righe += 1
                    riga_out, righe_child, anomalia = _chiudi_espositore_normale(
                        ctx.espositore_attivo, ctx.contatore_righe, ctx.vendor
                    )
                    ctx.righe_output.append(riga_out)
                    # Aggiungi righe child all'output
                    ctx.righe_output.extend(righe_child)
                    if anomalia:
                        ctx.anomalie.append(anomalia)
                    ctx.espositore_attivo = None
                    ctx.chiusure_normali += 1
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
        # Aggiungi righe child all'output
        ctx.righe_output.extend(righe_child)
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

    # Riga parent output
    riga_output = {
        'n_riga': n_riga,
        'codice_aic': esp.codice_aic,
        'codice_originale': esp.codice_originale,
        'codice_materiale': esp.codice_materiale,
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
        return None  # Nessuna anomalia

    return {
        'tipo_anomalia': 'ESPOSITORE',
        'livello': livello,
        'codice_anomalia': codice_anom,
        'descrizione': f"{CODICI_ANOMALIA[codice_anom]}: attesi {esp.pezzi_attesi_totali}, trovati {esp.pezzi_accumulati}{desc_extra}",
        'valore_anomalo': f"{esp.codice_originale}: {esp.descrizione}",
        'richiede_supervisione': richiede_supervisione,
        'espositore_codice': esp.codice_originale,
        'pezzi_attesi': esp.pezzi_attesi_totali,
        'pezzi_trovati': esp.pezzi_accumulati,
        'fascia_scostamento': fascia,
        'motivo_chiusura': motivo if forzato else '',
        'pattern_signature': f"{vendor}_{codice_anom}_{esp.codice_originale}_{pattern_suffix}",
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
