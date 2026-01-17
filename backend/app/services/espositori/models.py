# =============================================================================
# SERV.O v10.1 - ESPOSITORI MODELS
# =============================================================================
# Dataclasses per gestione espositori
# =============================================================================

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


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
    is_espositore_vuoto: bool = False  # Flag per espositore vuoto (non conta nei pezzi)


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
        # Non contare pezzi per espositore vuoto (omaggio contenitore)
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
        """Genera metadata JSON per espositore."""
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
            'child_dettaglio': child_dettaglio,
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
