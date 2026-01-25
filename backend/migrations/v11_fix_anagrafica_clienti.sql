-- =============================================================================
-- SERV.O v11.2 - FIX ANAGRAFICA CLIENTI
-- =============================================================================
-- Corregge i nomi delle colonne per allineamento con CSV ANAG_TOT_V.csv
-- =============================================================================

-- Rinomina colonne esistenti
ALTER TABLE anagrafica_clienti RENAME COLUMN categoria TO farmacia_categoria;
ALTER TABLE anagrafica_clienti RENAME COLUMN codice_stato TO farma_status;
ALTER TABLE anagrafica_clienti RENAME COLUMN id_tipo TO min_id;
ALTER TABLE anagrafica_clienti RENAME COLUMN riferimento TO deposito_riferimento;

-- Crea indice su min_id per ricerche veloci
CREATE INDEX IF NOT EXISTS idx_anagrafica_clienti_min_id ON anagrafica_clienti(min_id);

-- Verifica struttura finale
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'anagrafica_clienti';
