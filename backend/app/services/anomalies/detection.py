# =============================================================================
# SERV.O v10.1 - ANOMALIES DETECTION
# =============================================================================
# Anomaly detection and creation logic
# =============================================================================

from typing import Dict, Any, List, Optional
from ...database_pg import get_db

# =============================================================================
# CONSTANTS
# =============================================================================

ANOMALY_CODES = {
    # Espositore anomalies
    'ESP-A01': 'Espositore incompleto - pezzi mancanti',
    'ESP-A02': 'Espositore con pezzi in eccesso',
    'ESP-A03': 'Espositore senza righe child',
    'ESP-A04': 'Espositore chiuso per nuovo parent',
    'ESP-A05': 'Espositore chiuso forzatamente',
    'ESP-A06': 'Conflitto pattern ML vs estrazione',

    # Lookup anomalies
    'LKP-A01': 'Lookup score basso - verifica obbligatoria',
    'LKP-A02': 'Farmacia non trovata in anagrafica',
    'LKP-A03': 'Lookup score medio - verifica consigliata',
    'LKP-A04': 'P.IVA mismatch tra PDF e anagrafica - verifica obbligatoria',
    'LKP-A05': 'Cliente non trovato in anagrafica clienti - deposito non determinabile',

    # Listino anomalies
    'LST-A01': 'Prodotto non trovato nel listino',
    'LST-A02': 'Prezzo estratto diverso da listino',
    'LST-A03': 'Prezzo pubblico mancante',

    # AIC anomalies
    'AIC-A01': 'Codice AIC non riconosciuto',
    'AIC-A02': 'Codice AIC formato non valido',

    # Extraction anomalies
    'EXT-A01': 'Vendor non riconosciuto',
    'EXT-A02': 'Formato PDF non standard',

    # DOC_GENERICI anomalies
    'DOCGEN-A01': 'Codice AIC non standard',
    'DOCGEN-A03': 'Assenza prezzi nel documento',
    'DOCGEN-A04': 'Totale pezzi non coerente',
    'DOCGEN-A08': 'Quantita anomala',
    'DOCGEN-A09': 'Riga prodotto malformata',
    'DOCGEN-A10': 'Footer mancante',

    # Validation anomalies
    'VAL-A01': 'Campo obbligatorio mancante',
    'VAL-A02': 'Formato dati non valido',
    'VAL-A03': 'Valore fuori range',
}

ANOMALY_LEVELS = {
    # Bloccanti (richiedono supervisione)
    # v11.4: Rimosso LKP-A05 (convertito in DEP-A01 - problema deposito, non lookup)
    'CRITICO': ['ESP-A01', 'ESP-A02', 'LKP-A01', 'LKP-A02', 'LKP-A04', 'EXT-A01'],
    # v11.4: Aggiunto DEP-A01 (deposito mancante - bloccante)
    'ERRORE': ['ESP-A03', 'ESP-A06', 'AIC-A01', 'LST-A01', 'LST-A02', 'DOCGEN-A04', 'DOCGEN-A09', 'DOCGEN-A10', 'DEP-A01'],
    # Non bloccanti
    'ATTENZIONE': ['LKP-A03', 'DOCGEN-A08'],
    'INFO': ['DOCGEN-A01', 'DOCGEN-A03'],
}


def get_anomaly_level(codice: str) -> str:
    """Ritorna il livello di gravità per un codice anomalia."""
    for livello, codici in ANOMALY_LEVELS.items():
        if codice in codici:
            return livello
    return 'ATTENZIONE'


def is_blocking_anomaly(codice: str) -> bool:
    """Verifica se l'anomalia è bloccante (richiede supervisione)."""
    return codice in ANOMALY_LEVELS.get('CRITICO', []) or codice in ANOMALY_LEVELS.get('ERRORE', [])


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def detect_anomalies_for_order(id_testata: int) -> List[Dict]:
    """
    Esegue detection anomalie complete per un ordine.

    Verifica:
    - Lookup farmacia
    - Prezzi listino
    - Espositori
    - Validazione campi

    Returns:
        Lista anomalie rilevate
    """
    anomalies = []

    # 1. Verifica lookup
    lookup_anomalies = _detect_lookup_anomalies(id_testata)
    anomalies.extend(lookup_anomalies)

    # 2. Verifica listino (per ogni riga)
    listino_anomalies = _detect_listino_anomalies(id_testata)
    anomalies.extend(listino_anomalies)

    # 3. Verifica validazione campi
    validation_anomalies = _detect_validation_anomalies(id_testata)
    anomalies.extend(validation_anomalies)

    return anomalies


def _detect_lookup_anomalies(id_testata: int) -> List[Dict]:
    """Rileva anomalie lookup per un ordine."""
    db = get_db()
    anomalies = []

    order = db.execute("""
        SELECT lookup_score, lookup_status, partita_iva, ragione_sociale
        FROM ordini_testata
        WHERE id_testata = %s
    """, (id_testata,)).fetchone()

    if not order:
        return anomalies

    score = order.get('lookup_score', 0) or 0
    status = order.get('lookup_status', '')

    # Nessun match
    if status == 'NESSUNO' or score == 0:
        anomalies.append({
            'codice': 'LKP-A02',
            'tipo': 'LOOKUP',
            'livello': 'CRITICO',
            'descrizione': f"Farmacia non trovata: {order.get('ragione_sociale', 'N/D')} (P.IVA: {order.get('partita_iva', 'N/D')})",
            'id_testata': id_testata
        })
    # Score basso
    elif score < 80:
        anomalies.append({
            'codice': 'LKP-A01',
            'tipo': 'LOOKUP',
            'livello': 'CRITICO',
            'descrizione': f"Lookup score basso ({score}%) - verifica obbligatoria",
            'id_testata': id_testata
        })
    # Score medio
    elif score < 95:
        anomalies.append({
            'codice': 'LKP-A03',
            'tipo': 'LOOKUP',
            'livello': 'ATTENZIONE',
            'descrizione': f"Lookup score medio ({score}%) - verifica consigliata",
            'id_testata': id_testata
        })

    return anomalies


def _detect_listino_anomalies(id_testata: int) -> List[Dict]:
    """Rileva anomalie listino per un ordine."""
    db = get_db()
    anomalies = []

    # Trova righe senza prezzo o con prezzo diverso da listino
    # v11.2: Escludi prodotti omaggio/sconto merce (prezzo irrilevante per omaggi)
    rows = db.execute("""
        SELECT
            d.id_dettaglio,
            d.codice_aic,
            d.descrizione_prodotto,
            d.prezzo_netto,
            d.prezzo_pubblico,
            l.prezzo_netto as listino_netto,
            l.prezzo_pubblico as listino_pubblico
        FROM ordini_dettaglio d
        LEFT JOIN listini_vendor l ON d.codice_aic = l.codice_aic
        WHERE d.id_testata = %s
        AND d.tipo_espositore IS NULL  -- Escludi espositori
        AND d.stato NOT IN ('ARCHIVIATO')
        AND NOT (
            COALESCE(d.q_venduta, 0) = 0
            AND (COALESCE(d.q_omaggio, 0) > 0 OR COALESCE(d.q_sconto_merce, 0) > 0)
        )  -- v11.2: Escludi pure gift/sconto rows (q_venduta=0 ma q_omaggio/q_sconto_merce>0)
    """, (id_testata,)).fetchall()

    for row in rows:
        # Prodotto non in listino
        if row['listino_netto'] is None and row['codice_aic']:
            anomalies.append({
                'codice': 'LST-A01',
                'tipo': 'LISTINO',
                'livello': 'ATTENZIONE',
                'descrizione': f"Prodotto {row['codice_aic']} non trovato nel listino",
                'id_testata': id_testata,
                'id_dettaglio': row['id_dettaglio']
            })

        # Prezzo diverso da listino (tolleranza 1%)
        elif row['listino_netto'] and row['prezzo_netto']:
            diff = abs(float(row['prezzo_netto']) - float(row['listino_netto']))
            if diff > float(row['listino_netto']) * 0.01:
                anomalies.append({
                    'codice': 'LST-A02',
                    'tipo': 'LISTINO',
                    'livello': 'ATTENZIONE',
                    'descrizione': f"Prezzo {row['prezzo_netto']}€ diverso da listino {row['listino_netto']}€",
                    'id_testata': id_testata,
                    'id_dettaglio': row['id_dettaglio']
                })

    return anomalies


def _detect_validation_anomalies(id_testata: int) -> List[Dict]:
    """Rileva anomalie di validazione campi."""
    db = get_db()
    anomalies = []

    order = db.execute("""
        SELECT partita_iva, min_id, ragione_sociale, data_ordine
        FROM ordini_testata
        WHERE id_testata = %s
    """, (id_testata,)).fetchone()

    if not order:
        return anomalies

    # P.IVA mancante o formato non valido
    piva = order.get('partita_iva', '')
    if not piva:
        anomalies.append({
            'codice': 'VAL-A01',
            'tipo': 'VALIDAZIONE',
            'livello': 'ERRORE',
            'descrizione': "Partita IVA mancante",
            'id_testata': id_testata
        })
    elif len(piva) != 11 or not piva.isdigit():
        anomalies.append({
            'codice': 'VAL-A02',
            'tipo': 'VALIDAZIONE',
            'livello': 'ATTENZIONE',
            'descrizione': f"Formato P.IVA non standard: {piva}",
            'id_testata': id_testata
        })

    return anomalies


# =============================================================================
# ANOMALY CREATION HELPERS
# =============================================================================

def create_lookup_anomaly(
    id_testata: int,
    codice: str,
    score: int = None,
    farmacia_estratta: str = None,
    piva: str = None
) -> int:
    """Crea anomalia lookup."""
    from .commands import create_anomalia

    descrizione = ANOMALY_CODES.get(codice, 'Anomalia lookup')
    if score is not None:
        descrizione += f" (score: {score}%)"
    if farmacia_estratta:
        descrizione += f" - Farmacia: {farmacia_estratta}"

    return create_anomalia(
        id_testata=id_testata,
        tipo='LOOKUP',
        codice=codice,
        livello=get_anomaly_level(codice),
        descrizione=descrizione,
        dati_originali={
            'score': score,
            'farmacia_estratta': farmacia_estratta,
            'piva': piva
        }
    )


def create_espositore_anomaly(
    id_testata: int,
    id_dettaglio: int,
    codice: str,
    codice_espositore: str = None,
    descrizione_espositore: str = None,
    pezzi_attesi: int = None,
    pezzi_trovati: int = None,
    percentuale_scostamento: float = None
) -> int:
    """Crea anomalia espositore."""
    from .commands import create_anomalia

    descrizione = ANOMALY_CODES.get(codice, 'Anomalia espositore')
    if descrizione_espositore:
        descrizione += f" - {descrizione_espositore}"
    if pezzi_attesi and pezzi_trovati:
        descrizione += f" ({pezzi_trovati}/{pezzi_attesi} pezzi)"

    return create_anomalia(
        id_testata=id_testata,
        id_dettaglio=id_dettaglio,
        tipo='ESPOSITORE',
        codice=codice,
        livello=get_anomaly_level(codice),
        descrizione=descrizione,
        dati_originali={
            'codice_espositore': codice_espositore,
            'descrizione_espositore': descrizione_espositore,
            'pezzi_attesi': pezzi_attesi,
            'pezzi_trovati': pezzi_trovati,
            'percentuale_scostamento': percentuale_scostamento
        }
    )


def create_listino_anomaly(
    id_testata: int,
    id_dettaglio: int,
    codice: str,
    codice_aic: str = None,
    prezzo_estratto: float = None,
    prezzo_listino: float = None
) -> int:
    """Crea anomalia listino."""
    from .commands import create_anomalia

    descrizione = ANOMALY_CODES.get(codice, 'Anomalia listino')
    if codice_aic:
        descrizione += f" - AIC: {codice_aic}"
    if prezzo_estratto and prezzo_listino:
        descrizione += f" (estratto: {prezzo_estratto}€, listino: {prezzo_listino}€)"

    return create_anomalia(
        id_testata=id_testata,
        id_dettaglio=id_dettaglio,
        tipo='LISTINO',
        codice=codice,
        livello=get_anomaly_level(codice),
        descrizione=descrizione,
        dati_originali={
            'codice_aic': codice_aic,
            'prezzo_estratto': prezzo_estratto,
            'prezzo_listino': prezzo_listino
        }
    )
