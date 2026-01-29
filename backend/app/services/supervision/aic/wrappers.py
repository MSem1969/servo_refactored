# =============================================================================
# SERV.O v11.4 - AIC WRAPPER FUNCTIONS
# =============================================================================
# Funzioni wrapper per retrocompatibilità
# =============================================================================

from typing import Dict

from .models import LivelloPropagazione
from .propagation import AICPropagator


def propaga_aic(
    id_dettaglio: int,
    codice_aic: str,
    livello: LivelloPropagazione,
    operatore: str,
    note: str = None
) -> Dict:
    """Wrapper retrocompatibile per AICPropagator.propaga()"""
    return AICPropagator().propaga(
        id_dettaglio, codice_aic, livello, operatore, note
    ).to_dict()


def risolvi_anomalia_aic(
    id_anomalia: int,
    codice_aic: str,
    livello: LivelloPropagazione,
    operatore: str,
    note: str = None
) -> Dict:
    """Wrapper retrocompatibile per AICPropagator.risolvi_da_anomalia()"""
    return AICPropagator().risolvi_da_anomalia(
        id_anomalia, codice_aic, livello, operatore, note
    ).to_dict()


def propaga_aic_da_anomalia(
    id_anomalia: int,
    codice_aic: str,
    livello_propagazione: str,
    operatore: str,
    note: str = None
) -> Dict:
    """
    Wrapper per risolvi_anomalia_aic con firma compatibile con resolver.py.
    """
    livello = LivelloPropagazione(livello_propagazione.upper())
    return risolvi_anomalia_aic(id_anomalia, codice_aic, livello, operatore, note)
