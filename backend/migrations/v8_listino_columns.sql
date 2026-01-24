-- =============================================================================
-- SERV.O v8.1 - MIGRAZIONE COLONNE LISTINO
-- =============================================================================
-- Aggiunge colonne mancanti per supervisione listino
-- =============================================================================

-- Aggiungi colonna 'azione' a supervisione_listino
ALTER TABLE supervisione_listino ADD COLUMN IF NOT EXISTS azione TEXT;

-- Aggiungi colonna 'id_dettaglio' a supervisione_listino (per collegamento riga)
ALTER TABLE supervisione_listino ADD COLUMN IF NOT EXISTS id_dettaglio INTEGER;

-- Aggiungi colonne pattern a criteri_ordinari_listino per apprendimento ML
ALTER TABLE criteri_ordinari_listino ADD COLUMN IF NOT EXISTS prezzo_netto_pattern NUMERIC(10,2);
ALTER TABLE criteri_ordinari_listino ADD COLUMN IF NOT EXISTS prezzo_pubblico_pattern NUMERIC(10,2);
ALTER TABLE criteri_ordinari_listino ADD COLUMN IF NOT EXISTS sconto_1_pattern NUMERIC(5,2);
ALTER TABLE criteri_ordinari_listino ADD COLUMN IF NOT EXISTS sconto_2_pattern NUMERIC(5,2);
ALTER TABLE criteri_ordinari_listino ADD COLUMN IF NOT EXISTS aliquota_iva_pattern NUMERIC(5,2);
ALTER TABLE criteri_ordinari_listino ADD COLUMN IF NOT EXISTS azione_pattern TEXT;

-- Verifica
SELECT 'Colonne aggiunte a supervisione_listino:' AS info;
SELECT column_name FROM information_schema.columns
WHERE table_name = 'supervisione_listino' AND column_name IN ('azione', 'id_dettaglio');

SELECT 'Colonne aggiunte a criteri_ordinari_listino:' AS info;
SELECT column_name FROM information_schema.columns
WHERE table_name = 'criteri_ordinari_listino' AND column_name LIKE '%_pattern';
