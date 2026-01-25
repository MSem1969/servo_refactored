-- =============================================================================
-- SERV.O v11.3 - MODIFICA MANUALE HEADER ORDINE
-- =============================================================================
-- Aggiunge colonne per:
-- 1. Audit trail modifiche manuali
-- 2. Priorità modifica manuale su lookup automatico
-- =============================================================================

-- Colonna per salvare valori originali prima della modifica
ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS valori_originali_header JSONB;

-- Data ultima modifica header
ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS data_modifica_header TIMESTAMP;

-- Operatore che ha modificato
ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS operatore_modifica_header VARCHAR(100);

-- Note sulla modifica
ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS note_modifica_header TEXT;

-- Indice per trovare ordini modificati manualmente
CREATE INDEX IF NOT EXISTS idx_ordini_modifica_header
ON ordini_testata(data_modifica_header)
WHERE data_modifica_header IS NOT NULL;

-- Indice per trovare ordini con lookup MANUALE
CREATE INDEX IF NOT EXISTS idx_ordini_lookup_manuale
ON ordini_testata(lookup_method)
WHERE lookup_method = 'MANUALE';

-- Commenti
COMMENT ON COLUMN ordini_testata.valori_originali_header IS
'JSON con valori originali prima della modifica manuale header';

COMMENT ON COLUMN ordini_testata.data_modifica_header IS
'Timestamp ultima modifica manuale header';

COMMENT ON COLUMN ordini_testata.operatore_modifica_header IS
'Username operatore che ha modificato header manualmente';

COMMENT ON COLUMN ordini_testata.note_modifica_header IS
'Note sulla modifica manuale header';

-- =============================================================================
-- VERIFICA
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migrazione v11.3 completata: colonne audit header aggiunte';
END $$;
