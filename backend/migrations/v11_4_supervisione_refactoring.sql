-- =============================================================================
-- SERV.O v11.4 - REFACTORING SUPERVISIONE
-- =============================================================================
-- 1. Nuova tabella supervisione_anagrafica (unifica lookup + deposito + header)
-- 2. Aggiunge campi tracking correzione a tutte le tabelle supervisione
-- 3. Depreca supervisione_lookup (migra dati in supervisione_anagrafica)
-- =============================================================================

-- =============================================================================
-- 1. NUOVA TABELLA: supervisione_anagrafica
-- =============================================================================
-- Unifica tutti i problemi di header/anagrafica:
-- - LKP-A01: Score lookup < 80%
-- - LKP-A02: Farmacia non trovata
-- - LKP-A03: Score 80-95% (warning)
-- - LKP-A04: P.IVA mismatch (subentro)
-- - LKP-A05: Cliente non in anagrafica
-- - DEP-A01: Deposito mancante

CREATE TABLE IF NOT EXISTS supervisione_anagrafica (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata),
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia),
    codice_anomalia TEXT NOT NULL,
    vendor TEXT,

    -- Pattern per raggruppamento
    pattern_signature TEXT,
    pattern_descrizione TEXT,

    -- Valori estratti dal PDF (problematici)
    piva_estratta TEXT,
    min_id_estratto TEXT,
    ragione_sociale_estratta TEXT,
    indirizzo_estratto TEXT,
    cap_estratto TEXT,
    citta_estratta TEXT,
    provincia_estratta TEXT,
    deposito_estratto TEXT,

    -- Lookup automatico (risultato migliore trovato)
    lookup_score INTEGER,
    lookup_method TEXT,
    id_farmacia_suggerita INTEGER,

    -- Valori corretti (dall'operatore)
    piva_corretta TEXT,
    min_id_corretto TEXT,
    ragione_sociale_corretta TEXT,
    indirizzo_corretto TEXT,
    cap_corretto TEXT,
    citta_corretta TEXT,
    provincia_corretta TEXT,
    deposito_corretto TEXT,
    id_farmacia_assegnata INTEGER,

    -- Tracking correzione operatore
    operatore_correzione TEXT,
    data_correzione TIMESTAMP,
    note_correzione TEXT,

    -- Stato e approvazione supervisore
    stato TEXT DEFAULT 'PENDING' CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED')),
    operatore_approvazione TEXT,
    data_approvazione TIMESTAMP,
    note_approvazione TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_sup_anagrafica_testata ON supervisione_anagrafica(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_anagrafica_stato ON supervisione_anagrafica(stato);
CREATE INDEX IF NOT EXISTS idx_sup_anagrafica_pattern ON supervisione_anagrafica(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_sup_anagrafica_correzione ON supervisione_anagrafica(operatore_correzione) WHERE operatore_correzione IS NOT NULL;

-- =============================================================================
-- 2. AGGIUNGE CAMPI TRACKING CORREZIONE ALLE TABELLE ESISTENTI
-- =============================================================================

-- supervisione_aic: tracking correzione
ALTER TABLE supervisione_aic
ADD COLUMN IF NOT EXISTS operatore_correzione TEXT,
ADD COLUMN IF NOT EXISTS data_correzione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_correzione TEXT,
ADD COLUMN IF NOT EXISTS codice_aic_originale TEXT,
ADD COLUMN IF NOT EXISTS operatore_approvazione TEXT,
ADD COLUMN IF NOT EXISTS data_approvazione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_approvazione TEXT;

-- supervisione_espositore: tracking correzione
ALTER TABLE supervisione_espositore
ADD COLUMN IF NOT EXISTS operatore_correzione TEXT,
ADD COLUMN IF NOT EXISTS data_correzione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_correzione TEXT,
ADD COLUMN IF NOT EXISTS operatore_approvazione TEXT,
ADD COLUMN IF NOT EXISTS data_approvazione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_approvazione TEXT;

-- supervisione_prezzo: tracking correzione (unifica anche listino)
ALTER TABLE supervisione_prezzo
ADD COLUMN IF NOT EXISTS operatore_correzione TEXT,
ADD COLUMN IF NOT EXISTS data_correzione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_correzione TEXT,
ADD COLUMN IF NOT EXISTS prezzi_originali JSONB,
ADD COLUMN IF NOT EXISTS prezzi_corretti JSONB,
ADD COLUMN IF NOT EXISTS operatore_approvazione TEXT,
ADD COLUMN IF NOT EXISTS data_approvazione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_approvazione TEXT,
ADD COLUMN IF NOT EXISTS fonte TEXT DEFAULT 'PREZZO'; -- 'PREZZO' o 'LISTINO'

-- supervisione_listino: tracking correzione
ALTER TABLE supervisione_listino
ADD COLUMN IF NOT EXISTS operatore_correzione TEXT,
ADD COLUMN IF NOT EXISTS data_correzione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_correzione TEXT,
ADD COLUMN IF NOT EXISTS operatore_approvazione TEXT,
ADD COLUMN IF NOT EXISTS data_approvazione TIMESTAMP,
ADD COLUMN IF NOT EXISTS note_approvazione TEXT;

-- =============================================================================
-- 3. MIGRAZIONE DATI: supervisione_lookup → supervisione_anagrafica
-- =============================================================================

-- Migra dati esistenti da supervisione_lookup
-- Nota: i nomi colonna di supervisione_lookup sono diversi
INSERT INTO supervisione_anagrafica (
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    pattern_signature,
    piva_estratta,
    lookup_score,
    stato,
    operatore_correzione,
    data_correzione,
    operatore_approvazione,
    data_approvazione,
    created_at
)
SELECT
    sl.id_testata,
    sl.id_anomalia,
    COALESCE(sl.codice_anomalia, 'LKP-A01'),
    sl.vendor,
    sl.pattern_signature,
    sl.partita_iva_estratta,
    sl.lookup_score,
    sl.stato,
    sl.operatore,
    sl.timestamp_decisione,
    sl.operatore,
    sl.timestamp_decisione,
    sl.timestamp_creazione
FROM supervisione_lookup sl
WHERE NOT EXISTS (
    SELECT 1 FROM supervisione_anagrafica sa
    WHERE sa.id_testata = sl.id_testata
    AND sa.codice_anomalia = COALESCE(sl.codice_anomalia, 'LKP-A01')
)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- 4. VISTA UNIFICATA SUPERVISIONI PENDING
-- =============================================================================
-- Nota: usa solo colonne esistenti. Le colonne tracking saranno aggiunte dopo.

CREATE OR REPLACE VIEW v_supervisioni_pending AS
SELECT
    'anagrafica' as tipo_supervisione,
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    operatore_correzione,
    data_correzione,
    created_at,
    ragione_sociale_estratta as descrizione_pattern
FROM supervisione_anagrafica
WHERE stato = 'PENDING'

UNION ALL

SELECT
    'aic' as tipo_supervisione,
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    NULL as operatore_correzione,
    NULL as data_correzione,
    timestamp_creazione as created_at,
    descrizione_prodotto as descrizione_pattern
FROM supervisione_aic
WHERE stato = 'PENDING'

UNION ALL

SELECT
    'espositore' as tipo_supervisione,
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    NULL as vendor,
    pattern_signature,
    stato,
    NULL as operatore_correzione,
    NULL as data_correzione,
    timestamp_creazione as created_at,
    descrizione_espositore as descrizione_pattern
FROM supervisione_espositore
WHERE stato = 'PENDING'

UNION ALL

SELECT
    'prezzo' as tipo_supervisione,
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    NULL as operatore_correzione,
    NULL as data_correzione,
    timestamp_creazione as created_at,
    NULL as descrizione_pattern
FROM supervisione_prezzo
WHERE stato = 'PENDING'

UNION ALL

SELECT
    'listino' as tipo_supervisione,
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    NULL as operatore_correzione,
    NULL as data_correzione,
    timestamp_creazione as created_at,
    descrizione_prodotto as descrizione_pattern
FROM supervisione_listino
WHERE stato = 'PENDING';

-- =============================================================================
-- 5. COMMENTI
-- =============================================================================

COMMENT ON TABLE supervisione_anagrafica IS 'v11.4: Supervisione unificata per problemi anagrafica/header (P.IVA, MIN_ID, deposito, lookup)';
COMMENT ON COLUMN supervisione_anagrafica.operatore_correzione IS 'Operatore che ha effettuato la correzione (se presente, bottone Supervisione abilitato)';
COMMENT ON COLUMN supervisione_anagrafica.operatore_approvazione IS 'Supervisore che ha approvato/propagato la correzione';

COMMENT ON COLUMN supervisione_aic.operatore_correzione IS 'v11.4: Operatore che ha effettuato la correzione';
COMMENT ON COLUMN supervisione_espositore.operatore_correzione IS 'v11.4: Operatore che ha effettuato la correzione';
COMMENT ON COLUMN supervisione_prezzo.operatore_correzione IS 'v11.4: Operatore che ha effettuato la correzione';
COMMENT ON COLUMN supervisione_prezzo.fonte IS 'v11.4: Origine supervisione - PREZZO o LISTINO (unificati)';

-- =============================================================================
-- FINE MIGRATION v11.4
-- =============================================================================
