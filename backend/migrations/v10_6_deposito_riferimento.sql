-- =============================================================================
-- SERV.O v10.6 - Deposito Riferimento su Ordini
-- =============================================================================
-- Aggiunge colonna per assegnazione manuale deposito quando cliente non in anagrafica
-- Risolve anomalia LKP-A05
-- =============================================================================

-- Colonna deposito_riferimento su ordini_testata
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS deposito_riferimento VARCHAR(10);
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS id_cliente_manuale INTEGER;
ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS note_cliente_manuale TEXT;

-- Indice per join con anagrafica_clienti
CREATE INDEX IF NOT EXISTS idx_ordini_testata_deposito ON ordini_testata(deposito_riferimento) WHERE deposito_riferimento IS NOT NULL;

-- Commento
COMMENT ON COLUMN ordini_testata.deposito_riferimento IS 'Codice deposito assegnato manualmente per LKP-A05';
COMMENT ON COLUMN ordini_testata.id_cliente_manuale IS 'ID cliente selezionato manualmente';
COMMENT ON COLUMN ordini_testata.note_cliente_manuale IS 'Note operatore per assegnazione manuale cliente';
