# =============================================================================
# SERV.O v10.1 - ESPOSITORI CONSTANTS
# =============================================================================
# Costanti per gestione espositori e anomalie
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
    'ESP-A07': 'Chiusura forzata per riga non correlata',
    # Anomalie Lookup Farmacia
    'LKP-A01': 'Lookup score inferiore a 80% - verifica obbligatoria',
    'LKP-A02': 'Farmacia non trovata in anagrafica',
    'LKP-A03': 'Lookup score 80-95% - verifica consigliata',
    'LKP-A04': 'P.IVA mismatch tra PDF e anagrafica - verifica obbligatoria',
    'LKP-A05': 'Cliente non trovato in anagrafica clienti - deposito non determinabile',
    # Anomalie Estrazione
    'EXT-A01': 'Vendor non riconosciuto - estrattore generico',
    # Anomalie Listino
    'LST-A01': 'Codice AIC non trovato nel listino - verifica obbligatoria',
    'LST-A02': 'Prezzo listino mancante - verifica obbligatoria',
    'LST-A03': 'Associazione listino confermata da pattern ML',
    # Anomalie Prezzo
    'PRICE-A01': 'Prodotto in vendita senza prezzo - verifica obbligatoria',
    # Anomalie AIC
    'AIC-A01': 'Codice AIC mancante o non valido - verifica obbligatoria',
}

FASCE_SUPERVISIONE_OBBLIGATORIA = {'ALTO', 'CRITICO'}

# Soglie lookup score
LOOKUP_SCORE_GRAVE = 80      # Sotto: anomalia GRAVE (bloccante)
LOOKUP_SCORE_ORDINARIA = 95  # Sotto: anomalia ORDINARIA (non bloccante)
