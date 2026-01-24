# =============================================================================
# SERV.O v10.1 - LISTINI ENRICHMENT
# =============================================================================
# Arricchimento righe ordine con dati listino
# =============================================================================

from typing import Dict, Any, List, Optional, Tuple
from .queries import get_prezzo_listino


def arricchisci_riga_con_listino(
    riga: Dict[str, Any],
    vendor: str = None
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Arricchisce una riga ordine con dati dal listino.
    Ritorna anche eventuale anomalia se AIC non trovato o prezzo mancante.

    LOGICA:
    - Se la riga ha già un prezzo_netto valido (>0) -> skip, mantiene prezzo PDF
    - Se prezzo_netto è None/0/vuoto -> cerca nel listino generale
    - Il vendor è opzionale e usato solo per messaggi anomalie
    """
    codice_aic = riga.get('codice_aic', '')
    anomalia = None

    if not codice_aic:
        return riga, None

    # Escludi righe SC.MERCE, P.O.P. e omaggi dalla verifica listino
    tipo_posizione = (riga.get('tipo_posizione') or '').upper()
    tipo_riga = (riga.get('tipo_riga') or '').upper()

    if tipo_posizione in ('SC.MERCE', 'SCMERCE', 'P.O.P.', 'P.O.P', 'POP'):
        riga['fonte_prezzi'] = 'OMAGGIO'
        return riga, None

    if tipo_riga in ('SCONTO_MERCE', 'MATERIALE_POP'):
        riga['fonte_prezzi'] = 'OMAGGIO'
        return riga, None

    # Escludi se q_venduta = 0 e (q_sconto_merce > 0 o q_omaggio > 0)
    q_venduta = riga.get('q_venduta', 0) or 0
    q_sconto_merce = riga.get('q_sconto_merce', 0) or 0
    q_omaggio = riga.get('q_omaggio', 0) or 0

    if q_venduta == 0 and (q_sconto_merce > 0 or q_omaggio > 0):
        riga['fonte_prezzi'] = 'OMAGGIO'
        return riga, None

    # Se la riga ha già un prezzo valido estratto dal PDF, non sovrascrivere
    prezzo_esistente = riga.get('prezzo_netto')
    if prezzo_esistente is not None and prezzo_esistente > 0:
        riga['fonte_prezzi'] = 'PDF'
        return riga, None

    # Cerca nel listino generale (senza filtro vendor)
    listino = get_prezzo_listino(codice_aic)

    if not listino:
        vendor_info = f' (vendor: {vendor})' if vendor else ''
        anomalia = {
            'tipo_anomalia': 'LISTINO',
            'livello': 'ERRORE',
            'codice_anomalia': 'LST-A01',
            'descrizione': f'Codice AIC {codice_aic} non trovato nel listino{vendor_info}',
            'valore_anomalo': codice_aic,
            'richiede_supervisione': True,
            'n_riga': riga.get('n_riga'),
            'vendor': vendor,
        }
        riga['fonte_prezzi'] = 'MANCANTE'
        return riga, anomalia

    # Arricchisci con campi listino
    mapping_campi = {
        'sconto_1': 'sconto1',
        'sconto_2': 'sconto2',
        'sconto_3': 'sconto3',
        'sconto_4': 'sconto4',
        'prezzo_netto': 'prezzo_netto',
        'prezzo_pubblico': 'prezzo_pubblico',
        'aliquota_iva': 'aliquota_iva',
    }

    for campo_listino, campo_riga in mapping_campi.items():
        if listino.get(campo_listino) is not None:
            riga[campo_riga] = listino[campo_listino]

    # Verifica che il prezzo netto sia presente
    if not listino.get('prezzo_netto'):
        anomalia = {
            'tipo_anomalia': 'LISTINO',
            'livello': 'ATTENZIONE',
            'codice_anomalia': 'LST-A02',
            'descrizione': f'Prezzo mancante nel listino per AIC {codice_aic}',
            'valore_anomalo': codice_aic,
            'richiede_supervisione': True,
            'n_riga': riga.get('n_riga'),
            'vendor': vendor,
        }

    riga['fonte_prezzi'] = 'LISTINO'
    riga['id_listino'] = listino.get('id_listino')

    return riga, anomalia


def arricchisci_ordine_con_listino(
    order_data: Dict[str, Any],
    vendor: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Arricchisce tutte le righe di un ordine con dati dal listino.
    """
    anomalie = []
    righe_arricchite = []

    for riga in order_data.get('righe', []):
        riga_arricchita, anomalia = arricchisci_riga_con_listino(riga, vendor)
        righe_arricchite.append(riga_arricchita)

        if anomalia:
            anomalie.append(anomalia)

    order_data['righe'] = righe_arricchite

    if anomalie:
        order_data['anomalie_listino'] = anomalie

    return order_data, anomalie
