-- =============================================================================
-- MIGRATION 003: ML Pattern Sequence per Espositori
-- =============================================================================
-- Aggiunge supporto per apprendimento sequenze child negli espositori
-- Data: 2026-01-08
-- =============================================================================

-- 1. Estendere CRITERI_ORDINARI_ESPOSITORE con nuove colonne
ALTER TABLE criteri_ordinari_espositore
    ADD COLUMN IF NOT EXISTS descrizione_normalizzata VARCHAR(255),
    ADD COLUMN IF NOT EXISTS child_sequence_json JSONB,
    ADD COLUMN IF NOT EXISTS num_child_attesi INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_applications INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS successful_applications INTEGER DEFAULT 0;

-- Indice per ricerca veloce su descrizione normalizzata
CREATE INDEX IF NOT EXISTS idx_criteri_descrizione
    ON criteri_ordinari_espositore(descrizione_normalizzata);

CREATE INDEX IF NOT EXISTS idx_criteri_ordinario
    ON criteri_ordinari_espositore(is_ordinario)
    WHERE is_ordinario = TRUE;

-- 2. Nuova tabella LOG_ML_DECISIONS per tracciamento decisioni ML
CREATE TABLE IF NOT EXISTS log_ml_decisions (
    id_log SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE SET NULL,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE SET NULL,
    pattern_signature VARCHAR(100),
    descrizione_espositore VARCHAR(255),

    -- Sequenze confrontate
    child_sequence_estratta JSONB,
    child_sequence_pattern JSONB,

    -- Risultato confronto
    similarity_score DECIMAL(5,2) NOT NULL,
    decision VARCHAR(20) NOT NULL,  -- 'APPLY_ML', 'APPLY_WARNING', 'SEND_SUPERVISION'
    decision_reason TEXT,

    -- Esito finale (aggiornato dopo supervisione)
    final_outcome VARCHAR(20),  -- 'CORRECT', 'INCORRECT', 'MODIFIED'
    operatore VARCHAR(50),

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici per query frequenti
CREATE INDEX IF NOT EXISTS idx_ml_decisions_testata ON log_ml_decisions(id_testata);
CREATE INDEX IF NOT EXISTS idx_ml_decisions_pattern ON log_ml_decisions(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_ml_decisions_decision ON log_ml_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_ml_decisions_timestamp ON log_ml_decisions(timestamp DESC);

-- 3. Commenti per documentazione
COMMENT ON COLUMN criteri_ordinari_espositore.descrizione_normalizzata IS
    'Descrizione espositore normalizzata per matching (uppercase, no special chars)';

COMMENT ON COLUMN criteri_ordinari_espositore.child_sequence_json IS
    'Sequenza child appresa [{"aic": "040002010", "codice": "415734", "descrizione": "...", "quantita": N}]';

COMMENT ON COLUMN criteri_ordinari_espositore.num_child_attesi IS
    'Numero di prodotti child attesi in questo espositore';

COMMENT ON TABLE log_ml_decisions IS
    'Log delle decisioni ML per pattern espositori (applicazione automatica, warning, supervisione)';

COMMENT ON COLUMN log_ml_decisions.decision IS
    'APPLY_ML: applicato automaticamente, APPLY_WARNING: applicato con warning, SEND_SUPERVISION: mandato in supervisione';

-- =============================================================================
-- FINE MIGRATION 003
-- =============================================================================
