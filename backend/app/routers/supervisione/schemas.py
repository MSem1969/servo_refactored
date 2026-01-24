# =============================================================================
# SERV.O v8.1 - SUPERVISIONE SCHEMAS
# =============================================================================
# Modelli Pydantic condivisi per tutti i moduli supervisione
# =============================================================================

from typing import List, Optional
from pydantic import BaseModel


# =============================================================================
# MODELLI BASE
# =============================================================================

class DecisioneBase(BaseModel):
    """Base per decisioni supervisione."""
    operatore: str
    note: Optional[str] = None


class DecisioneApprova(DecisioneBase):
    """Richiesta approvazione."""
    pass


class DecisioneRifiuta(DecisioneBase):
    """Richiesta rifiuto (note obbligatorie)."""
    note: str  # Override per renderlo obbligatorio


class DecisioneModifica(DecisioneBase):
    """Richiesta modifica manuale."""
    modifiche: dict


# =============================================================================
# MODELLI LISTINO
# =============================================================================

class CorrezioneListinoRequest(BaseModel):
    """Richiesta correzione prezzi listino - v8.1 con tutti i campi listini_vendor."""
    operatore: str
    descrizione: Optional[str] = None
    prezzo_netto: Optional[float] = None
    prezzo_pubblico: Optional[float] = None
    prezzo_scontare: Optional[float] = None
    sconto_1: Optional[float] = None
    sconto_2: Optional[float] = None
    sconto_3: Optional[float] = None
    sconto_4: Optional[float] = None
    aliquota_iva: Optional[float] = None
    scorporo_iva: Optional[str] = 'S'  # S=Netto, N=IVA inclusa
    data_decorrenza: Optional[str] = None  # YYYY-MM-DD
    applica_a_listino: bool = False  # Se True, aggiunge anche al listino vendor
    note: Optional[str] = None


class ArchiviazioneListinoRequest(BaseModel):
    """Richiesta archiviazione riga listino."""
    operatore: str
    motivo: str  # Motivo archiviazione obbligatorio
    note: Optional[str] = None


# =============================================================================
# MODELLI LOOKUP
# =============================================================================

class RisoluzioneLookupRequest(BaseModel):
    """Richiesta risoluzione supervisione lookup."""
    operatore: str
    min_id: Optional[str] = None
    id_farmacia: Optional[int] = None
    note: Optional[str] = None


# =============================================================================
# MODELLI ML/PATTERN
# =============================================================================

class RisoluzioneConflittoRequest(BaseModel):
    """Richiesta risoluzione conflitto ML."""
    operatore: str
    scelta: str  # 'PATTERN', 'ESTRAZIONE', 'MANUALE'
    modifiche_manuali: Optional[dict] = None
    note: Optional[str] = None


# =============================================================================
# MODELLI PREZZO (v8.1)
# =============================================================================

class PrezzoRigaUpdate(BaseModel):
    """Aggiornamento prezzo singola riga."""
    id_dettaglio: int
    prezzo_netto: Optional[float] = None
    prezzo_pubblico: Optional[float] = None


class PrezzoRigheRequest(BaseModel):
    """Richiesta aggiornamento prezzi righe."""
    operatore: str
    righe_modificate: List[PrezzoRigaUpdate]
    note: Optional[str] = None


class ApprovaPrezzoRequest(BaseModel):
    """Richiesta approvazione supervisione prezzo."""
    operatore: str
    azione_correttiva: str  # PREZZO_INSERITO, LISTINO_APPLICATO, ACCETTATO_SENZA_PREZZO, RIGHE_RIMOSSE
    note: Optional[str] = None


# =============================================================================
# MODELLI RESPONSE
# =============================================================================

class SupervisioneResponse(BaseModel):
    """Risposta singola supervisione."""
    id_supervisione: int
    id_testata: int
    codice_anomalia: str
    codice_espositore: Optional[str]
    descrizione_espositore: Optional[str]
    pezzi_attesi: int
    pezzi_trovati: int
    valore_calcolato: float
    pattern_signature: Optional[str]
    stato: str
    operatore: Optional[str]
    timestamp_creazione: str
    timestamp_decisione: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True
